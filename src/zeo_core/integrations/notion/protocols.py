"""Protocols for Notion integration."""

from typing import Any, Protocol, runtime_checkable

from zeo_core.integrations.core import IntegrationProtocol, IntegrationResult

from .models import NotionBlock, NotionDatabase, NotionPage


@runtime_checkable
class NotionIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for Notion integration."""

    # -- Read --

    def get_page(self, page_id: str) -> IntegrationResult[NotionPage]:
        """Retrieve a page by ID."""
        ...

    def list_page_blocks(
        self, page_id: str, page_size: int = 100, start_cursor: str | None = None
    ) -> IntegrationResult[list[NotionBlock]]:
        """List the content blocks of a page."""
        ...

    def search(
        self,
        query: str | None = None,
        filter_object_type: str | None = None,
        page_size: int = 100,
    ) -> IntegrationResult[list[dict[str, Any]]]:
        """Search pages and databases shared with the integration."""
        ...

    def get_database(self, database_id: str) -> IntegrationResult[NotionDatabase]:
        """Retrieve a database's metadata."""
        ...

    def query_database(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,  # noqa: A002 -- matches Notion API's own field name, see client.py's identical noqa
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
    ) -> IntegrationResult[list[NotionPage]]:
        """Query a database's default data source with an optional filter."""
        ...

    # -- Write --

    def create_page(
        self,
        parent: dict[str, Any],
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> IntegrationResult[NotionPage]:
        """Create a new page."""
        ...

    def create_database_entry(
        self,
        database_id: str,
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> IntegrationResult[NotionPage]:
        """Create a new entry (page) in a database."""
        ...

    def update_page(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
    ) -> IntegrationResult[NotionPage]:
        """Update a page's properties or archived state."""
        ...

    def append_blocks(
        self, block_id: str, children: list[dict[str, Any]]
    ) -> IntegrationResult[list[NotionBlock]]:
        """Append content blocks to a page or block."""
        ...
