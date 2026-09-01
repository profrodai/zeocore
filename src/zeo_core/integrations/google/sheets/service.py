"""
Google Sheets integration service for zeo_core.

This module provides the main service class for Google Sheets integration,
implementing the curated 7-of-17-method surface RULING-408 DESIGN-04
approach B ruled: `spreadsheets.get`, `spreadsheets.create`,
`spreadsheets.values.get`, `spreadsheets.values.update`,
`spreadsheets.values.append`, `spreadsheets.values.clear`, and
`spreadsheets.batchUpdate` -- no more, no less, no escape-hatch method (a
separate, not-yet-built ruling item, same boundary as Docs).

THE SHEETS ASYMMETRY (why this file has two clearly separated halves):
`spreadsheets.values.*` reads/writes a `ValueRange` body of exactly THREE
fields (`range`, `majorDimension`, `values`) -- verified live against
discovery revision 20260828 -- and NEVER touches the 69-kind `Request`
union `batchUpdate` uses. Full read/write/create-from-scratch therefore
ships entirely through `get_spreadsheet`/`create_spreadsheet`/
`get_values`/`update_values`/`append_values`/`clear_values`, none of which
need `SheetsRequestBuilder` at all. `batch_update` is the one method that
does, and it is the only place the 69-kind union's typing seam
(`dict[str, Any]` at this boundary, per RULING-408 DESIGN-02) actually
matters.

CONFIG TIMING (RULING-408 DESIGN-04 / item 4, same as Docs): this class
follows `google/mail/service.py`'s DEFERRED CONFIG pattern, not `drive/
service.py`'s or `calendar/service.py`'s eager pattern. Config resolution
(calling the config provider, constructing `GoogleAuthProvider`, calling
`get_credentials()`, calling `googleapiclient.discovery.build(...)`) all
happens INSIDE `initialize()`, never in `__init__` -- constructing this
service from a fresh directory with no config file must never raise;
`initialize()` is where a genuine missing-config failure surfaces, and only
there.

ERROR-HANDLING SHAPE (per drive/service.py and docs/service.py, copied for
shape only, not config timing): every public method wraps its SDK call in
an inner try/except that logs and returns an `IntegrationResult.
error_result(...)`, inside an outer try/except catching `ZeoApiError` /
`ZeoBaseAuthError` / `Exception` around the whole method body.

Structural precedent for "no separate operations/ package": `google/
calendar/service.py` and `google/docs/service.py` -- everything inline in
this file.
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
from zeo_core.integrations.google.sheets.protocols import (
    GoogleCredentials,
    SheetsIntegrationProtocol,
    SheetsService,
)
from zeo_core.integrations.google.sheets.request_builder import SheetsRequestBuilder

# mypy's nonetype-type check rejects `types.NoneType` used as a type
# expression directly; google/drive/service.py, google/mail/service.py, and
# google/docs/service.py already established this same module-level alias
# (`NoneType = type(None)`) as the fix for the identical pattern -- matched
# here rather than inventing a new idiom.
NoneType = type(None)


class GoogleSheetsService(BaseIntegrationService, SheetsIntegrationProtocol):
    """Integration service for Google Sheets."""

    # Per RULING-405/406's narrower-than-Drive clause (matching Docs'
    # RULING-408 item 5 precedent): read-write spreadsheets scope only,
    # since `create`/`values.update`/`values.append`/`values.clear`/
    # `batchUpdate` all need write access but nothing here needs Drive-wide
    # file access. Sheets also offers `auth/spreadsheets.readonly`, verified
    # live, but this service's curated surface is read+write by design (per
    # DESIGN-04's own "read/write/manipulate/create-from-scratch" framing),
    # so the broader-of-the-two-Sheets-scopes is the correct default, same
    # reasoning as Docs choosing `auth/documents` over `auth/documents.
    # readonly`.
    SCOPES: list[str] = [
        "https://www.googleapis.com/auth/spreadsheets",
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
        Initialize the Google Sheets integration service.

        Per the deferred-config pattern (mirroring `google/mail/service.py`
        and `google/docs/service.py` exactly): NO config resolution, auth
        provider construction, or API client construction happens here.
        Those all happen inside `initialize()`. Constructing this service,
        even from a fresh directory with no config file anywhere, must
        never raise.

        Args:
            client_secrets_file: Path to the client secrets file.
            credentials_file: Path to the credentials file.
            config_path: Path to the configuration file.
            scopes: OAuth scopes for the Sheets API.
            log_level: Logging level.
        """
        config_provider = GoogleConfigProvider("sheets", log_level)
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
        # Typed Any, matching drive/service.py's `self.drive_service: Any`,
        # calendar/service.py's `self.calendar_service: Any`, and docs/
        # service.py's `self.docs_service: Any` convention -- keeps tests
        # mocking at the real SDK boundary (a bare `unittest.mock.
        # MagicMock()`) rather than needing a hand-built Protocol-conforming
        # mock class. See docs/service.py's own docstring for the full
        # reasoning (3 of the now-4 sibling services use `Any` here; mail is
        # the sole outlier with a real Protocol type).
        self.sheets_service: Any = None
        self.config: dict[str, object] = {}

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "GoogleSheets"

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
                "GoogleSheetsService has no config_provider configured"
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
        Initialize the Google Sheets service.

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
                    f"Failed to authenticate with Google Sheets: {auth_error}"
                )

            try:
                from googleapiclient.discovery import build

                self.sheets_service = cast(
                    SheetsService,
                    build(
                        "sheets",
                        "v4",
                        credentials=cast(GoogleCredentials, credentials),
                    ),
                )
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to initialize Google Sheets API: {api_error}",
                    service="Google Sheets",
                    api_method="build",
                    original_error=api_error,
                ) from api_error

            self._initialized = True
            return IntegrationResult.success_result(
                message="Google Sheets service initialized successfully"
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
            self.logger.error(f"Failed to initialize Google Sheets service: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize Google Sheets service: {e}"
            )

    # ------------------------------------------------------------------
    # spreadsheets.get / spreadsheets.create
    # ------------------------------------------------------------------

    def get_spreadsheet(self, spreadsheet_id: str) -> IntegrationResult[dict[str, Any]]:
        """
        Retrieve a spreadsheet's metadata (wraps `spreadsheets.get`).

        Args:
            spreadsheet_id: ID of the spreadsheet to retrieve.

        Returns:
            IntegrationResult containing the full spreadsheet resource
            dict (properties, sheets metadata -- not cell values; use
            `get_values` for cell data).
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.sheets_service is None:
                return IntegrationResult.error_result(
                    "Google Sheets service is not initialized"
                )

            try:
                spreadsheet = (
                    self.sheets_service.spreadsheets()
                    .get(spreadsheetId=spreadsheet_id)
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to get spreadsheet: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to get spreadsheet from Google Sheets: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], spreadsheet),
                message=f"Retrieved spreadsheet {spreadsheet_id}",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during getting spreadsheet: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during getting spreadsheet: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get spreadsheet: {e}")
            return IntegrationResult.error_result(
                f"Failed to get spreadsheet from Google Sheets: {e}"
            )

    def create_spreadsheet(self, title: str) -> IntegrationResult[dict[str, Any]]:
        """
        Create a new, empty spreadsheet with the given title (wraps
        `spreadsheets.create`).

        Args:
            title: Title of the new spreadsheet.

        Returns:
            IntegrationResult containing the created spreadsheet resource
            dict (includes `spreadsheetId`).
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.sheets_service is None:
                return IntegrationResult.error_result(
                    "Google Sheets service is not initialized"
                )

            body: dict[str, object] = {"properties": {"title": title}}
            try:
                spreadsheet = (
                    self.sheets_service.spreadsheets().create(body=body).execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to create spreadsheet: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to create spreadsheet in Google Sheets: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], spreadsheet),
                message=f"Created spreadsheet '{title}'",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during creating spreadsheet: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during creating spreadsheet: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create spreadsheet: {e}")
            return IntegrationResult.error_result(
                f"Failed to create spreadsheet in Google Sheets: {e}"
            )

    # ------------------------------------------------------------------
    # spreadsheets.values.* -- the plainly-typed, non-batchUpdate half
    # (ValueRange: exactly `range`/`majorDimension`/`values`, verified live
    # against discovery revision 20260828; never touches the Request union)
    # ------------------------------------------------------------------

    def get_values(
        self, spreadsheet_id: str, range_a1: str
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Read values from a range (wraps `spreadsheets.values.get`).

        Args:
            spreadsheet_id: ID of the spreadsheet to read from.
            range_a1: A1 notation range to read (e.g. "Sheet1!A1:B10").

        Returns:
            IntegrationResult containing the `ValueRange` response dict
            (`range`, `majorDimension`, `values`).
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.sheets_service is None:
                return IntegrationResult.error_result(
                    "Google Sheets service is not initialized"
                )

            try:
                value_range = (
                    self.sheets_service.spreadsheets()
                    .values()
                    .get(spreadsheetId=spreadsheet_id, range=range_a1)
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to get values: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to get values from Google Sheets: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], value_range),
                message=f"Retrieved values from {spreadsheet_id}!{range_a1}",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during getting values: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during getting values: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get values: {e}")
            return IntegrationResult.error_result(
                f"Failed to get values from Google Sheets: {e}"
            )

    def update_values(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Overwrite values in a range (wraps `spreadsheets.values.update`).

        Args:
            spreadsheet_id: ID of the spreadsheet to update.
            range_a1: A1 notation range to write.
            values: Row-major list of rows, each a list of cell values.
            value_input_option: "RAW" (store exactly as given) or
                "USER_ENTERED" (parsed as if typed into the UI, e.g.
                formulas evaluate and dates parse). Defaults to
                "USER_ENTERED" to match spreadsheet-UI paste behavior.

        Returns:
            IntegrationResult containing the `UpdateValuesResponse` dict.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.sheets_service is None:
                return IntegrationResult.error_result(
                    "Google Sheets service is not initialized"
                )

            body: dict[str, object] = {"range": range_a1, "values": values}
            try:
                response = (
                    self.sheets_service.spreadsheets()
                    .values()
                    .update(
                        spreadsheetId=spreadsheet_id,
                        range=range_a1,
                        body=body,
                        valueInputOption=value_input_option,
                    )
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to update values: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to update values in Google Sheets: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], response),
                message=f"Updated values at {spreadsheet_id}!{range_a1}",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during updating values: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during updating values: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to update values: {e}")
            return IntegrationResult.error_result(
                f"Failed to update values in Google Sheets: {e}"
            )

    def append_values(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Append values after the last row of a range (wraps
        `spreadsheets.values.append`). Never overwrites existing data --
        the API finds the first empty row after the given range's table and
        writes there, which is why this is index-free from the caller's
        perspective: no row number needs to be computed or passed.

        Args:
            spreadsheet_id: ID of the spreadsheet to append to.
            range_a1: A1 notation range identifying the table to append
                after (e.g. "Sheet1!A1" is enough -- the API finds the
                table's actual extent).
            values: Row-major list of rows, each a list of cell values.
            value_input_option: "RAW" or "USER_ENTERED". Defaults to
                "USER_ENTERED".

        Returns:
            IntegrationResult containing the `AppendValuesResponse` dict.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.sheets_service is None:
                return IntegrationResult.error_result(
                    "Google Sheets service is not initialized"
                )

            body: dict[str, object] = {"range": range_a1, "values": values}
            try:
                response = (
                    self.sheets_service.spreadsheets()
                    .values()
                    .append(
                        spreadsheetId=spreadsheet_id,
                        range=range_a1,
                        body=body,
                        valueInputOption=value_input_option,
                    )
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to append values: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to append values in Google Sheets: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], response),
                message=f"Appended values after {spreadsheet_id}!{range_a1}",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during appending values: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during appending values: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to append values: {e}")
            return IntegrationResult.error_result(
                f"Failed to append values in Google Sheets: {e}"
            )

    def clear_values(
        self, spreadsheet_id: str, range_a1: str
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Clear values from a range, leaving formatting untouched (wraps
        `spreadsheets.values.clear`).

        Args:
            spreadsheet_id: ID of the spreadsheet to clear.
            range_a1: A1 notation range to clear.

        Returns:
            IntegrationResult containing the `ClearValuesResponse` dict.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.sheets_service is None:
                return IntegrationResult.error_result(
                    "Google Sheets service is not initialized"
                )

            try:
                response = (
                    self.sheets_service.spreadsheets()
                    .values()
                    .clear(spreadsheetId=spreadsheet_id, range=range_a1)
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to clear values: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to clear values in Google Sheets: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], response),
                message=f"Cleared values at {spreadsheet_id}!{range_a1}",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during clearing values: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during clearing values: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to clear values: {e}")
            return IntegrationResult.error_result(
                f"Failed to clear values in Google Sheets: {e}"
            )

    # ------------------------------------------------------------------
    # spreadsheets.batchUpdate -- the one method that touches the 69-kind
    # Request union, and the only reason SheetsRequestBuilder exists
    # ------------------------------------------------------------------

    def batch_update(
        self, spreadsheet_id: str, requests: list[dict[str, Any]]
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Apply a batch of update requests to a spreadsheet (wraps
        `spreadsheets.batchUpdate`).

        Per RULING-408 DESIGN-03: `requests` is routed through
        `SheetsRequestBuilder`, which PRESERVES caller order (not a sort --
        see `request_builder.py`'s module docstring for why Sheets does not
        get Docs' descending-index policy: index-shifting requests are
        partitioned per-(sheetId, dimension) rather than global, and
        same-batch sheet references rely on a caller-supplied explicit
        `sheetId`, not response-chaining -- both of which defeat a single
        global sort key).

        Args:
            spreadsheet_id: ID of the spreadsheet to update.
            requests: Sheets API `Request` dicts (each shaped exactly like
                the real API, e.g. `{"addSheet": {...}}`), in the caller's
                intended execution order.

        Returns:
            IntegrationResult containing the `batchUpdate` response dict.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.sheets_service is None:
                return IntegrationResult.error_result(
                    "Google Sheets service is not initialized"
                )

            ordered_requests = SheetsRequestBuilder.from_requests(requests).build()
            body: dict[str, object] = {"requests": ordered_requests}

            try:
                response = (
                    self.sheets_service.spreadsheets()
                    .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to apply batch update: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to apply batch update in Google Sheets: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], response),
                message=(
                    f"Applied {len(ordered_requests)} update(s) to {spreadsheet_id}"
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
                f"Failed to apply batch update in Google Sheets: {e}"
            )

    def validate_config(self, config: dict[str, object]) -> tuple[bool, list[str]]:
        """
        Validate the service configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        from zeo_core.integrations.google.config import GoogleSheetsConfig

        errors: list[str] = []
        try:
            GoogleSheetsConfig(**config)
            return True, []
        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")
            return False, errors
