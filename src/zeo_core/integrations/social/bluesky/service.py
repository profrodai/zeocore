"""Bluesky integration service for zeo_core.

**Fresh-directory construction is an acceptance criterion, not a hope**
(RULING-409 s6c): this class resolves NO configuration and touches NO disk
in `__init__` -- exactly `mail/service.py`'s pattern (the in-repo reference
RULING-409 s3/SOW-01 names as already correct), and deliberately NOT
`drive/service.py`'s (`__init__` calls `self._initialize_config(...)`
directly, which raises `ZeoConfigurationError` from a directory with no
config file -- RULING-409 s3's blocker 1, reproduced against zeocore
`8f609c3b`). All config/credential resolution happens inside `initialize()`,
so `BlueskyIntegration()` alone -- zero arguments, zero config, any
directory -- always succeeds; only calling `initialize()` can fail, and only
for a reason connected to actually authenticating.
"""

from typing import Any

from zeo_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from zeo_core.integrations.core import (
    AuthProviderProtocol,
    BaseIntegrationService,
    ConfigProviderProtocol,
    IntegrationResult,
)
from zeo_core.integrations.social.bluesky.auth import BlueskyAuthProvider
from zeo_core.integrations.social.bluesky.config import BlueskyConfigProvider
from zeo_core.integrations.social.bluesky.facets import (
    LinkSpan,
    MentionSpan,
    compute_facets,
)
from zeo_core.integrations.social.bluesky.protocols import BlueskyIntegrationProtocol

logger = get_logger(__name__)


class BlueskyIntegration(BaseIntegrationService, BlueskyIntegrationProtocol):
    """Integration service for Bluesky, via the AT Protocol.

    Structural mirror of `NotionIntegration` (integrations/notion/service.py):
    same provider-injection constructor, same `_ensure_initialized` /
    client-is-None mypy-narrowing guard pattern per method, same
    `IntegrationResult.success_result`/`error_result` envelope discipline.
    Config/credential resolution is deferred into `initialize()`, matching
    `mail/service.py` rather than `NotionIntegration.__init__` (which
    constructs its providers eagerly but still defers `load_config`/
    `authenticate` to `initialize()` via the base class -- the same
    deferred-resolution property, arrived at the same way).
    """

    def __init__(
        self,
        config_provider: ConfigProviderProtocol | None = None,
        auth_provider: AuthProviderProtocol | None = None,
        config_path: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """Initialize the Bluesky integration.

        Constructs a `BlueskyConfigProvider` if none is given, but --
        critically -- does NOT construct a `BlueskyAuthProvider` or resolve
        any config here. The auth provider needs a resolved
        `credentials_file` path, and resolving one (even to a default) is
        deferred to `initialize()` so this constructor can never raise from
        a fresh directory. `auth_provider=None` is passed to `super()`
        unconditionally, exactly like `NotionIntegration.__init__` does,
        even when a caller supplies one -- it is stored separately below and
        wired to a resolved config in `initialize()`.

        Args:
            config_provider: Configuration provider.
            auth_provider: Optional pre-built auth provider (e.g. for
                testing). If omitted, one is built in `initialize()` from
                resolved config.
            config_path: Path to configuration file.
            log_level: Logging level.
        """
        if config_provider is None:
            config_provider = BlueskyConfigProvider(log_level=log_level)

        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        self._injected_auth_provider: AuthProviderProtocol | None = auth_provider
        self.auth_provider: BlueskyAuthProvider | None = None

    @property
    def name(self) -> str:
        """Name of the integration."""
        return "Bluesky"

    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"

    def _ensure_initialized(self) -> IntegrationResult | None:
        """Ensure the integration is initialized."""
        if not self._initialized:
            logger.error("Bluesky integration is not initialized")
            not_initialized_msg = (
                "Bluesky integration is not initialized. Call initialize() first."
            )
            return IntegrationResult.error_result(
                error=not_initialized_msg,
                message=not_initialized_msg,
            )
        return None

    def initialize(self) -> IntegrationResult:
        """Initialize the Bluesky integration: resolve config, build (or
        accept an injected) auth provider, and authenticate.

        This is where every fresh-directory-sensitive step lives, matching
        `GoogleMailService.initialize()`'s shape: load config, build the
        provider from it, authenticate, mark initialized. Nothing here is
        done in `__init__`.
        """
        try:
            if not self.config and self.config_provider:
                config_result = self.config_provider.load_config(self.config_path)
                if not config_result.success:
                    return IntegrationResult.error_result(
                        f"Failed to load Bluesky configuration: {config_result.error}"
                    )
                self.config = config_result.content

            if self.config is None:
                return IntegrationResult.error_result(
                    "Bluesky configuration is not available"
                )

            if self._injected_auth_provider is not None:
                self.auth_provider = self._injected_auth_provider  # type: ignore[assignment]
            else:
                credentials_file = self.config.get("credentials_file")
                self.auth_provider = BlueskyAuthProvider(
                    credentials_file=credentials_file,
                    log_level=self.log_level,
                )

            # self.auth_provider was just assigned on every path above (the
            # injected provider or a freshly-built one) -- mypy cannot
            # narrow `BlueskyAuthProvider | None` across those two branches
            # back to non-None, so this guard is a real (if structurally
            # unreachable) narrowing step, matching the same class of guard
            # NotionIntegration._create_notion_client uses one file over.
            if self.auth_provider is None:
                return IntegrationResult.error_result(
                    "Bluesky auth provider is not available"
                )

            identifier = self.config.get("identifier") or None
            app_password = self.config.get("app_password") or None
            service_url = self.config.get("service_url") or None

            auth_result = self.auth_provider.authenticate(
                identifier=identifier,
                app_password=app_password,
                service_url=service_url,
            )
            if not auth_result.success:
                return IntegrationResult.error_result(
                    f"Failed to authenticate Bluesky: {auth_result.error}"
                )

            self._initialized = True
            return IntegrationResult.success_result(
                message="Bluesky integration initialized successfully"
            )
        except Exception as e:
            self._initialized = False
            logger.error(f"Failed to initialize Bluesky integration: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize Bluesky integration: {e}"
            )

    def is_available(self) -> bool:
        """Check if the integration is available."""
        return self._initialized and self.auth_provider is not None

    def post(
        self,
        text: str,
        links: list[LinkSpan] | None = None,
        mentions: list[MentionSpan] | None = None,
    ) -> IntegrationResult[dict[str, object]]:
        """Create a post on Bluesky.

        Args:
            text: Post text (<=300 graphemes / 3000 bytes per the
                `app.bsky.feed.post` lexicon; not independently
                re-validated here, the server is authoritative).
            links: Optional link spans to annotate as rich-text facets
                (RULING-409 s6c: client-side byte-offset computation, see
                `facets.py`).
            mentions: Optional mention spans to annotate as rich-text
                facets.

        Returns:
            `IntegrationResult` whose `content` is the `createRecord`
            response (`uri`, `cid`), on success.

        Note on acceptance (RULING-409 s5/SOW-02): a success result here
        means the AT Protocol accepted the write -- it is NOT the acceptance
        test. Bluesky has no silent-failure mode (unlike YouTube/TikTok),
        but RULING-409's own discipline is set on this easy case precisely
        so it stays habitual: `done_when` requires an OPERATOR confirming
        the post is actually VISIBLE, not merely that this call returned
        2xx.
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # self.auth_provider is always set together with _initialized=True
        # in initialize() -- mypy cannot narrow that across the
        # _ensure_initialized call boundary, matching NotionIntegration's
        # own identical comment/guard on every method.
        if self.auth_provider is None:
            return IntegrationResult.error_result(
                error="Bluesky auth provider is not initialized",
                message="Bluesky auth provider is not initialized",
            )

        credentials = self.auth_provider.get_credentials()
        session: dict[str, Any] = credentials if isinstance(credentials, dict) else {}
        token = session.get("access_jwt")
        repo = session.get("did") or session.get("identifier")
        if not token or not repo:
            return IntegrationResult.error_result(
                error="No active Bluesky session to post with",
                message="No active Bluesky session to post with",
            )

        facets = compute_facets(text, links=links, mentions=mentions)

        try:
            session_client = self.auth_provider.build_client()
            result: dict[str, Any] = session_client.create_post_record(
                repo=repo,
                text=text,
                access_jwt=token,
                facets=facets or None,
            )
            return IntegrationResult.success_result(
                content=result,
                message="Post accepted by the AT Protocol (2xx) -- this is NOT "
                "visibility confirmation; see RULING-409 s5.",
            )
        except Exception as e:
            return IntegrationResult.error_result(
                error=f"Failed to create Bluesky post: {e}",
                message=f"Failed to create Bluesky post: {e}",
            )
