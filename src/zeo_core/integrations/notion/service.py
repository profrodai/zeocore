"""Notion core integration service for zeo_core."""

import os
from collections.abc import Callable
from typing import Any

from zeo_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from zeo_core.integrations.core import (
    AuthProviderProtocol,
    BaseIntegrationService,
    ConfigProviderProtocol,
    IntegrationResult,
)

from .auth import NotionAuthProvider
from .client import NotionAPIError, NotionClient, NotionOperation
from .config import NotionConfigProvider
from .models import NotionBlock, NotionDatabase, NotionPage
from .protocols import NotionIntegrationProtocol

logger = get_logger(__name__)


class NotionIntegration(BaseIntegrationService, NotionIntegrationProtocol):
    """Notion integration for zeo_core.

    Structural mirror of GitHubIntegration (integrations/github/service.py):
    same provider-injection constructor, same _ensure_initialized /
    self.client-is-None mypy-narrowing guard pattern per method, same
    IntegrationResult.success_result/error_result envelope discipline. The
    difference is the API surface (Notion pages/databases/blocks instead of
    GitHub repos/issues/PRs) and the underlying transport (the notion-client
    SDK instead of raw requests + a hand-rolled retry loop, since
    notion-client already owns that -- see client.py's module docstring).
    """

    def __init__(
        self,
        config_provider: ConfigProviderProtocol | None = None,
        auth_provider: AuthProviderProtocol | None = None,
        config_path: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        client_factory: Callable[..., NotionClient] | None = None,
    ) -> None:
        """Initialize the Notion integration.

        Args:
            config_provider: Configuration provider
            auth_provider: Authentication provider
            config_path: Path to configuration file
            log_level: Logging level
            client_factory: Injectable Notion client constructor. The default
                uses ZeoCore's explicit direct-transport policy.
        """
        if config_provider is None:
            config_provider = NotionConfigProvider(log_level=log_level)

        if auth_provider is None:
            auth_provider = NotionAuthProvider(log_level=log_level)

        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        self.client: NotionClient | None = None
        self._client_factory = client_factory or NotionClient

    @property
    def name(self) -> str:
        """Name of the integration."""
        return "Notion"

    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"

    def _ensure_initialized(self) -> IntegrationResult | None:
        """Ensure the integration is initialized.

        Returns:
            IntegrationResult error if not initialized, None if initialized
        """
        if not self._initialized:
            logger.error("Notion integration is not initialized")
            not_initialized_msg = (
                "Notion integration is not initialized. Call initialize() first."
            )
            return IntegrationResult.error_result(
                error=not_initialized_msg,
                message=not_initialized_msg,
            )
        return None

    def _check_config_available(self) -> IntegrationResult | None:
        """Check that configuration was loaded successfully."""
        try:
            if self.config is None:
                return IntegrationResult.error_result(
                    error="Notion configuration is not available",
                    message="Notion configuration is not available",
                )
        except Exception as e:
            logger.exception("Exception while accessing configuration")
            return IntegrationResult.error_result(
                error=f"Failed to initialize Notion integration: {str(e)}",
                message=f"Failed to initialize Notion integration: {str(e)}",
            )
        return None

    def _authenticate_with_config_token(self, token: str) -> IntegrationResult | None:
        """Authenticate the auth provider using a token found in config."""
        logger.debug("Using Notion token from configuration")
        if not self.auth_provider:
            return None

        try:
            auth_result = self.auth_provider.authenticate()
            if not auth_result.success:
                logger.warning(
                    "Failed to authenticate auth provider with token from "
                    f"config: {auth_result.error}"
                )
                error_msg = getattr(auth_result, "error", "Authentication failed")
                return IntegrationResult.error_result(
                    error=f"Failed to authenticate with Notion: {error_msg}",
                    message=f"Failed to authenticate with Notion: {error_msg}",
                )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to initialize Notion integration: {error_msg}",
                message=f"Failed to initialize Notion integration: {error_msg}",
            )
        return None

    def _get_token_from_auth_provider(
        self,
    ) -> tuple[str | None, IntegrationResult | None]:
        """Obtain a Notion token from the auth provider directly."""
        if not self.auth_provider:
            return None, None

        try:
            logger.debug("Getting credentials from auth provider")
            auth_result = self.auth_provider.get_credentials()

            if isinstance(auth_result, dict):
                token = auth_result.get("token")
            else:
                token = getattr(auth_result, "token", None)

            if not token:
                logger.debug("No token from get_credentials, trying authenticate()")
                auth_result = self.auth_provider.authenticate()
                if auth_result.success:
                    credentials = self.auth_provider.get_credentials()
                    if isinstance(credentials, dict):
                        token = credentials.get("token")
                    else:
                        token = getattr(credentials, "token", None)
                if not token:
                    error_msg = getattr(auth_result, "error", "Authentication failed")
                    logger.error(f"Authentication failed: {error_msg}")
                    return None, IntegrationResult.error_result(
                        error=f"Failed to authenticate with Notion: {error_msg}",
                        message=f"Failed to authenticate with Notion: {error_msg}",
                    )
        except Exception as e:
            error_msg = str(e)
            return None, IntegrationResult.error_result(
                error=f"Failed to initialize Notion integration: {error_msg}",
                message=f"Failed to initialize Notion integration: {error_msg}",
            )
        return token, None

    def _resolve_auth_token(self) -> tuple[str | None, IntegrationResult | None]:
        """Resolve the Notion token to use, from config or auth provider."""
        # self.config is always non-None here in practice: initialize()
        # calls _check_config_available() (which validates this exact
        # invariant) and returns early on failure before ever reaching
        # this method -- mypy cannot see that across the call boundary,
        # matching GitHubIntegration's own identical comment/guard.
        if self.config is None:
            return None, IntegrationResult.error_result(
                error="Notion configuration is not available",
                message="Notion configuration is not available",
            )

        token = os.environ.get("NOTION_TOKEN")
        if token:
            return token, None
        return None, IntegrationResult.error_result(
            error="NOTION_TOKEN is not configured",
            message="Set NOTION_TOKEN in the process environment",
        )

    def _create_notion_client(self, token: str) -> IntegrationResult:
        """Create the Notion client and mark the integration initialized."""
        try:
            if self.config is None:
                return IntegrationResult.error_result(
                    error="Notion configuration is not available",
                    message="Notion configuration is not available",
                )
            self.client = self._client_factory(
                token=token,
                timeout_ms=self.config.get("timeout_ms", 60_000),
                max_retries=self.config.get("max_retries", 3),
            )

            self._initialized = True
            return IntegrationResult.success_result(
                message="Notion integration initialized successfully"
            )
        except Exception as e:
            error_msg = str(e)
            self._initialized = False
            return IntegrationResult.error_result(
                error=f"Failed to initialize Notion client: {error_msg}",
                message=f"Failed to initialize Notion client: {error_msg}",
            )

    def initialize(self) -> IntegrationResult:
        """Initialize the Notion integration.

        Returns:
            Result of the initialization
        """
        try:
            init_result = super().initialize()
            if not init_result.success:
                return init_result

            config_error = self._check_config_available()
            if config_error:
                return config_error

            token, auth_error = self._resolve_auth_token()
            if auth_error:
                return auth_error

            if not token:
                error_msg = (
                    "Notion token is not configured and no auth provider is available"
                )
                return IntegrationResult.error_result(
                    error=error_msg, message=error_msg
                )

            return self._create_notion_client(token)
        except Exception as e:
            logger.exception("Unexpected error in Notion integration initialization")
            error_msg = str(e)
            self._initialized = False
            return IntegrationResult.error_result(
                error=f"Failed to initialize Notion integration: {error_msg}",
                message=f"Failed to initialize Notion integration: {error_msg}",
            )

    def is_available(self) -> bool:
        """Check if the Notion integration is available."""
        return self._initialized and self.client is not None

    def execute(
        self,
        operation: NotionOperation | str,
        **kwargs: Any,  # noqa: ANN401
    ) -> IntegrationResult[dict[str, Any]]:
        """Execute any current public Notion operation by stable name.

        This is the endpoint-complete surface. The named convenience methods
        below remain for common workflows and backward compatibility.
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )
        try:
            content = self.client.execute(operation, **kwargs)
            return IntegrationResult.success_result(
                content=content,
                message=f"Notion operation {operation} completed",
            )
        except NotionAPIError as error:
            return IntegrationResult.error_result(
                error=f"{error.code}: {error}", message=str(error)
            )
        except (TypeError, ValueError) as error:
            return IntegrationResult.error_result(
                error=f"Invalid Notion request: {error}",
                message=f"Invalid Notion request: {error}",
            )

    # ------------------------------------------------------------------
    # Read: pages
    # ------------------------------------------------------------------

    def get_page(self, page_id: str) -> IntegrationResult[NotionPage]:
        """Retrieve a page by ID."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # self.client is always set together with _initialized=True in
        # _create_notion_client -- mypy cannot narrow that across the
        # _ensure_initialized call boundary, matching GitHubIntegration's
        # own identical comment/guard on every method below.
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            page = self.client.get_page(page_id)
            return IntegrationResult.success_result(
                content=page, message=f"Successfully retrieved page {page.id}"
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to get page: {error_msg}",
                message=f"Failed to get page: {error_msg}",
            )

    def list_page_blocks(
        self, page_id: str, page_size: int = 100, start_cursor: str | None = None
    ) -> IntegrationResult[list[NotionBlock]]:
        """List the content blocks of a page."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            blocks, next_cursor = self.client.list_page_blocks(
                page_id, page_size=page_size, start_cursor=start_cursor
            )
            message = f"Successfully retrieved {len(blocks)} blocks for page {page_id}"
            if next_cursor:
                message += " (more results available)"
            return IntegrationResult.success_result(content=blocks, message=message)
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to list page blocks: {error_msg}",
                message=f"Failed to list page blocks: {error_msg}",
            )

    def search(
        self,
        query: str | None = None,
        filter_object_type: str | None = None,
        page_size: int = 100,
    ) -> IntegrationResult[list[dict[str, Any]]]:
        """Search pages and databases shared with the integration."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            results = self.client.search(
                query=query,
                filter_object_type=filter_object_type,
                page_size=page_size,
            )
            return IntegrationResult.success_result(
                content=results,
                message=f"Successfully retrieved {len(results)} search results",
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to search: {error_msg}",
                message=f"Failed to search: {error_msg}",
            )

    # ------------------------------------------------------------------
    # Read: databases
    # ------------------------------------------------------------------

    def get_database(self, database_id: str) -> IntegrationResult[NotionDatabase]:
        """Retrieve a database's metadata."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            database = self.client.get_database(database_id)
            return IntegrationResult.success_result(
                content=database,
                message=f"Successfully retrieved database {database.id}",
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to get database: {error_msg}",
                message=f"Failed to get database: {error_msg}",
            )

    def query_database(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,  # noqa: A002 -- matches Notion API's own field name, see client.py's identical noqa
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
    ) -> IntegrationResult[list[NotionPage]]:
        """Query a database's default data source with an optional filter."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            pages, next_cursor = self.client.query_database(
                database_id, filter=filter, sorts=sorts, page_size=page_size
            )
            message = (
                f"Successfully retrieved {len(pages)} pages from database {database_id}"
            )
            if next_cursor:
                message += " (more results available)"
            return IntegrationResult.success_result(content=pages, message=message)
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to query database: {error_msg}",
                message=f"Failed to query database: {error_msg}",
            )

    # ------------------------------------------------------------------
    # Write: pages
    # ------------------------------------------------------------------

    def create_page(
        self,
        parent: dict[str, Any],
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> IntegrationResult[NotionPage]:
        """Create a new page."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            page = self.client.create_page(
                parent=parent, properties=properties, children=children
            )
            return IntegrationResult.success_result(
                content=page, message=f"Successfully created page {page.id}"
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to create page: {error_msg}",
                message=f"Failed to create page: {error_msg}",
            )

    def create_database_entry(
        self,
        database_id: str,
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> IntegrationResult[NotionPage]:
        """Create a new entry (page) in a database."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            page = self.client.create_database_entry(
                database_id=database_id, properties=properties, children=children
            )
            return IntegrationResult.success_result(
                content=page,
                message=f"Successfully created entry {page.id} in database "
                f"{database_id}",
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to create database entry: {error_msg}",
                message=f"Failed to create database entry: {error_msg}",
            )

    def update_page(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
    ) -> IntegrationResult[NotionPage]:
        """Update a page's properties or trash state."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            page = self.client.update_page(
                page_id=page_id, properties=properties, archived=archived
            )
            return IntegrationResult.success_result(
                content=page, message=f"Successfully updated page {page.id}"
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to update page: {error_msg}",
                message=f"Failed to update page: {error_msg}",
            )

    # ------------------------------------------------------------------
    # Write: blocks
    # ------------------------------------------------------------------

    def append_blocks(
        self, block_id: str, children: list[dict[str, Any]]
    ) -> IntegrationResult[list[NotionBlock]]:
        """Append content blocks to a page or block."""
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        if self.client is None:
            return IntegrationResult.error_result(
                error="Notion client is not initialized",
                message="Notion client is not initialized",
            )

        try:
            blocks = self.client.append_blocks(block_id=block_id, children=children)
            return IntegrationResult.success_result(
                content=blocks,
                message=f"Successfully appended {len(blocks)} blocks to {block_id}",
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to append blocks: {error_msg}",
                message=f"Failed to append blocks: {error_msg}",
            )
