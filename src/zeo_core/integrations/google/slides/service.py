"""
Google Slides integration service for zeo_core.

This module provides the main service class for Google Slides integration:
`presentations.get`, `presentations.create`, and `presentations.batchUpdate`
(per RULING-408 DESIGN-04, exactly these 3 of Slides' 5 methods -- omitting
both thumbnail-generation methods -- no escape-hatch method).

CONFIG TIMING (RULING-408 DESIGN-04 / item 4): this class follows
`google/mail/service.py`'s and `google/docs/service.py`'s DEFERRED CONFIG
pattern, not `drive/service.py`'s or `calendar/service.py`'s eager
pattern. Config resolution (calling the config provider, constructing
`GoogleAuthProvider`, calling `get_credentials()`, calling
`googleapiclient.discovery.build(...)`) all happens INSIDE `initialize()`,
never in `__init__` -- constructing this service from a fresh directory
with no config file must never raise; `initialize()` is where a genuine
missing-config failure surfaces, and only there.

ERROR-HANDLING SHAPE (per docs/service.py, copied for its shape only, not
its ordering policy): every public method wraps its SDK call in an inner
try/except that logs and returns an `IntegrationResult.error_result(...)`,
inside an outer try/except catching `ZeoApiError` / `ZeoBaseAuthError` /
`Exception` around the whole method body.

THE ONE THING NOT COPIED FROM DOCS: `batch_update` here routes requests
through `SlidesRequestBuilder`, which PRESERVES caller order -- it does
NOT reverse-sort by index the way `docs/service.py`'s `batch_update` does.
See `request_builder.py`'s module docstring for the full rationale: Slides
addresses objects by a stable, caller-assignable `objectId`, not by a
position that shifts under mutation, and a batch commonly has request N+1
reference an `objectId` request N just created -- reordering would break
that reference chain.

Structural precedent for "no separate operations/ package": `google/
docs/service.py` -- everything inline in this file, matching the identical
dead/unwired-package concern documented there for drive's own operations/
package (not repeated here).
"""

import logging
from typing import Any, cast

from zeo_core.core.errors import (
    ZeoApiError,
    ZeoBaseAuthError,
    ZeoIntegrationError,
)
from zeo_core.integrations.core.base import BaseIntegrationService
from zeo_core.integrations.core.protocols import ConfigProviderProtocol
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.google.auth import GoogleAuthProvider
from zeo_core.integrations.google.config import GoogleConfigProvider
from zeo_core.integrations.google.slides.protocols import (
    GoogleCredentials,
    SlidesIntegrationProtocol,
    SlidesService,
)
from zeo_core.integrations.google.slides.request_builder import SlidesRequestBuilder

# mypy's nonetype-type check rejects `types.NoneType` used as a type
# expression directly; google/drive/service.py, google/mail/service.py,
# and google/docs/service.py already established this same module-level
# alias (`NoneType = type(None)`) as the fix for the identical pattern --
# matched here rather than inventing a new idiom.
NoneType = type(None)


class GoogleSlidesService(BaseIntegrationService, SlidesIntegrationProtocol):
    """Integration service for Google Slides."""

    # Per RULING-405/406's narrower-than-Drive clause (verified live
    # against the Slides discovery document): `auth/presentations` is the
    # read-write presentations scope, narrower than Drive's
    # `.../auth/drive`, and is chosen over `auth/presentations.readonly`
    # since `create` and `batchUpdate` both require write access.
    SCOPES: list[str] = [
        "https://www.googleapis.com/auth/presentations",
    ]

    def __init__(
        self,
        client_secrets_file: str | None = None,
        credentials_file: str | None = None,
        config_path: str | None = None,
        scopes: list[str] | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Initialize the Google Slides integration service.

        Per the deferred-config pattern (mirroring `google/docs/
        service.py`/`google/mail/service.py` exactly): NO config
        resolution, auth provider construction, or API client
        construction happens here. Those all happen inside `initialize()`.
        Constructing this service, even from a fresh directory with no
        config file anywhere, must never raise.

        Args:
            client_secrets_file: Path to the client secrets file.
            credentials_file: Path to the credentials file.
            config_path: Path to the configuration file.
            scopes: OAuth scopes for the Slides API.
            log_level: Logging level.
        """
        config_provider = GoogleConfigProvider("slides", log_level)
        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        # If explicit parameters are provided, override configuration from
        # file -- same "custom_config short-circuits file loading" shape as
        # google/mail/service.py's and google/docs/service.py's own
        # __init__.
        self.custom_config: dict[str, object] = {}
        if client_secrets_file and credentials_file:
            self.custom_config = {
                "client_secrets_file": client_secrets_file,
                "credentials_file": credentials_file,
            }

        self.scopes: list[str] = list(scopes) if scopes is not None else self.SCOPES

        self.auth_provider: GoogleAuthProvider | None = None
        # Typed Any, matching drive/service.py's `self.drive_service: Any`
        # and docs/service.py's `self.docs_service: Any` convention. A
        # real `SlidesService | None` annotation forces mypy strict to
        # check every `self.slides_service.presentations()...` call site
        # against `SlidesPresentationsResource`'s exact signature, which a
        # bare `unittest.mock.MagicMock()` (this package's test
        # convention, matching docs/test_service.py's SDK-boundary
        # mocking style) does not structurally satisfy. `Any` here
        # matches the sibling precedent and keeps tests mocking at the
        # real SDK boundary rather than needing a hand-built Protocol-
        # conforming mock class.
        self.slides_service: Any = None
        self.config: dict[str, object] = {}

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "GoogleSlides"

    @property
    def version(self) -> str:
        """Get the version of the integration."""
        return "1.0.0"

    def _require_config_provider(self) -> ConfigProviderProtocol:
        """Return `self.config_provider`, narrowed to non-None.

        `self.config_provider` is typed `ConfigProviderProtocol | None` on
        the base class, but `__init__` always constructs and passes a real
        `GoogleConfigProvider` before `super().__init__` -- never `None`
        for this concrete class (same reasoning as
        `GoogleDocsService._require_config_provider`). Raises if that
        invariant is ever violated (defensive, not expected).
        """
        if self.config_provider is None:
            raise ZeoIntegrationError(
                "GoogleSlidesService has no config_provider configured"
            )
        return self.config_provider

    def _initialize_config(self) -> dict[str, object] | None:
        """
        Initialize configuration from parameters or config file.

        Returns:
            The initialized configuration or None if failed.

        Raises:
            ZeoIntegrationError: If configuration initialization fails in
                expected ways.
        """
        try:
            if self.custom_config:
                self.config = self.custom_config
            else:
                config_provider = self._require_config_provider()
                config_result = config_provider.load_config(self.config_path)
                if not config_result.success or not config_result.content:
                    raise ZeoIntegrationError(
                        "Failed to load configuration from file", {}
                    )
                self.config = config_result.content

            return self.config
        except ZeoIntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration: {e}")
            return None

    def initialize(self) -> IntegrationResult[NoneType]:
        """
        Initialize the Google Slides service.

        Returns:
            IntegrationResult indicating success or failure.
        """
        init_result: IntegrationResult[NoneType] = super().initialize()
        if not init_result.success:
            return init_result

        try:
            config: dict[str, object] | None = self._initialize_config()
            if config is None:
                self._initialized = False
                return IntegrationResult.error_result(
                    "Failed to initialize configuration"
                )

            client_secrets_file: str = str(config["client_secrets_file"])
            credentials_file_value: object = config.get("credentials_file")
            credentials_file: str | None = (
                str(credentials_file_value)
                if credentials_file_value is not None
                else None
            )

            self.auth_provider = GoogleAuthProvider(
                client_secrets_file=client_secrets_file,
                credentials_file=credentials_file,
                scopes=self.scopes,
                log_level=self.log_level,
            )

            try:
                credentials = self.auth_provider.get_credentials()
            except ZeoBaseAuthError as auth_error:
                self.logger.error(f"Authentication failed: {auth_error}")
                return IntegrationResult.error_result(
                    f"Failed to authenticate with Google Slides: {auth_error}"
                )

            try:
                from googleapiclient.discovery import build

                self.slides_service = cast(
                    SlidesService,
                    build(
                        "slides",
                        "v1",
                        credentials=cast(GoogleCredentials, credentials),
                    ),
                )
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to initialize Google Slides API: {api_error}",
                    service="Google Slides",
                    api_method="build",
                    original_error=api_error,
                ) from api_error

            self._initialized = True
            return IntegrationResult.success_result(
                message="Google Slides service initialized successfully"
            )
        except ZeoApiError as e:
            self._initialized = False
            self.logger.error(f"API error during initialization: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self._initialized = False
            self.logger.error(f"Authentication error during initialization: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self._initialized = False
            self.logger.error(f"Failed to initialize Google Slides service: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize Google Slides service: {e}"
            )

    # ------------------------------------------------------------------
    # presentations.get
    # ------------------------------------------------------------------

    def get_presentation(
        self, presentation_id: str
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Retrieve a presentation by ID (wraps `presentations.get`).

        Args:
            presentation_id: ID of the presentation to retrieve.

        Returns:
            IntegrationResult containing the full presentation resource
            dict.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.slides_service is None:
                return IntegrationResult.error_result(
                    "Google Slides service is not initialized"
                )

            try:
                presentation = (
                    self.slides_service.presentations()
                    .get(presentationId=presentation_id)
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to get presentation: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to get presentation from Google Slides: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], presentation),
                message=f"Retrieved presentation {presentation_id}",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during getting presentation: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during getting presentation: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get presentation: {e}")
            return IntegrationResult.error_result(
                f"Failed to get presentation from Google Slides: {e}"
            )

    # ------------------------------------------------------------------
    # presentations.create
    # ------------------------------------------------------------------

    def create_presentation(self, title: str) -> IntegrationResult[dict[str, Any]]:
        """
        Create a new, empty presentation with the given title (wraps
        `presentations.create`).

        Args:
            title: Title of the new presentation.

        Returns:
            IntegrationResult containing the created presentation resource
            dict (includes `presentationId`).
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.slides_service is None:
                return IntegrationResult.error_result(
                    "Google Slides service is not initialized"
                )

            body: dict[str, object] = {"title": title}
            try:
                presentation = (
                    self.slides_service.presentations().create(body=body).execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to create presentation: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to create presentation in Google Slides: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], presentation),
                message=f"Created presentation '{title}'",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during creating presentation: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during creating presentation: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create presentation: {e}")
            return IntegrationResult.error_result(
                f"Failed to create presentation in Google Slides: {e}"
            )

    # ------------------------------------------------------------------
    # presentations.batchUpdate
    # ------------------------------------------------------------------

    def batch_update(
        self, presentation_id: str, requests: list[dict[str, Any]]
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Apply a batch of update requests to a presentation (wraps
        `presentations.batchUpdate`).

        Per RULING-408 DESIGN-03: `requests` is routed through
        `SlidesRequestBuilder`, which PRESERVES caller order exactly --
        the opposite of `GoogleDocsService.batch_update`'s reverse-sort.
        See `request_builder.py`'s module docstring for the full
        rationale: Slides objects are addressed by a stable,
        caller-assignable `objectId`, and a later request in the batch
        routinely references an `objectId` an earlier request in the same
        batch just created, so reordering would break that dependency.

        Args:
            presentation_id: ID of the presentation to update.
            requests: Slides API `Request` dicts (each shaped exactly like
                the real API, e.g. `{"createSlide": {...}}`), in the exact
                order they must be applied.

        Returns:
            IntegrationResult containing the `batchUpdate` response dict.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.slides_service is None:
                return IntegrationResult.error_result(
                    "Google Slides service is not initialized"
                )

            ordered_requests = SlidesRequestBuilder.from_requests(requests).build()
            body: dict[str, object] = {"requests": ordered_requests}

            try:
                response = (
                    self.slides_service.presentations()
                    .batchUpdate(presentationId=presentation_id, body=body)
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to apply batch update: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to apply batch update in Google Slides: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], response),
                message=(
                    f"Applied {len(ordered_requests)} update(s) to {presentation_id}"
                ),
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during batch update: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during batch update: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to apply batch update: {e}")
            return IntegrationResult.error_result(
                f"Failed to apply batch update in Google Slides: {e}"
            )

    def validate_config(self, config: dict[str, object]) -> tuple[bool, list[str]]:
        """
        Validate the service configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        from zeo_core.integrations.google.config import GoogleSlidesConfig

        errors: list[str] = []
        try:
            GoogleSlidesConfig(**config)
            return True, []
        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")
            return False, errors
