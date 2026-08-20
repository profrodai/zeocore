"""Notion API client wrapper for zeo_core.

Wraps the official `notion-client` SDK (https://pypi.org/project/notion-client/,
package `notion_client`, upstream `ramnes/notion-sdk-py`) rather than
hand-rolling HTTP the way `github/client.py` does over raw `requests` --
`notion-client` already owns retry/backoff, rate-limit handling, and error
typing (`notion_client.errors.APIResponseError`), so this wrapper's job is
narrowing that general SDK surface to zeocore's Result/model conventions,
not reimplementing HTTP plumbing.

**The 2025-09-03 API version's data-source model, and why `query_database`
exists.** As of the Notion API version this SDK targets (`notion_client`
>=1.0.0, confirmed against the installed 3.1.0 and the 2.7.0 floor alike),
a Notion "database" is a container for one or more "data sources," and
querying happens against a *data source ID*, not the database ID directly
(`notion_client.api_endpoints.DataSourcesEndpoint.query`; there is no
`databases.query` method in this SDK generation -- confirmed by reading
`api_endpoints.py` directly, not assumed from older docs). The overwhelming
common case is one implicit data source per database (that's the shape
every pre-2025 "Notion database" already had). `query_database` below
hides that indirection: it retrieves the database, resolves its first data
source, and queries that -- so a caller asking to "query a database with
filters" (the plain-English, common-case ask) does not need to learn the
data-source split unless their database genuinely has more than one source,
in which case `list_data_sources`/`query_data_source` are available directly.
"""

from typing import Any

from zeo_core.core.logging import get_logger

from .models import NotionBlock, NotionDatabase, NotionDataSource, NotionPage

logger = get_logger(__name__)


class NotionNoDataSourceError(Exception):
    """Raised when a database has no data source to query."""


class NotionClient:
    """Client for interacting with the Notion API, wrapping notion_client.Client."""

    def __init__(
        self,
        token: str,
        timeout_ms: int = 60_000,
        max_retries: int = 3,
        sdk_client: Any = None,  # noqa: ANN401 -- injectable for testing; real default is notion_client.Client
    ) -> None:
        """Initialize the Notion client.

        Args:
            token: Notion integration token
            timeout_ms: Request timeout in milliseconds
            max_retries: Maximum number of retries for requests
            sdk_client: Optional pre-built notion_client.Client (or a test
                double satisfying the same surface), for testing.
        """
        self.token = token
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries

        if sdk_client is not None:
            self._sdk = sdk_client
        else:
            from notion_client import Client as NotionSDKClient
            from notion_client import RetryOptions

            self._sdk = NotionSDKClient(
                auth=token,
                timeout_ms=timeout_ms,
                retry=RetryOptions(max_retries=max_retries),
            )

    # ------------------------------------------------------------------
    # Read: pages
    # ------------------------------------------------------------------

    def get_page(self, page_id: str) -> NotionPage:
        """Retrieve a page by ID.

        Args:
            page_id: Notion page ID

        Returns:
            NotionPage object

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        data = self._sdk.pages.retrieve(page_id=page_id)
        return _page_from_response(data)

    def list_page_blocks(
        self, page_id: str, page_size: int = 100, start_cursor: str | None = None
    ) -> tuple[list[NotionBlock], str | None]:
        """List the top-level content blocks of a page (or any block's children).

        Args:
            page_id: Notion page or block ID
            page_size: Max number of blocks to return in this page of results
            start_cursor: Pagination cursor from a previous call

        Returns:
            Tuple of (blocks, next_cursor). next_cursor is None when there
            are no more results.

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        kwargs: dict[str, Any] = {"block_id": page_id, "page_size": page_size}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        data = self._sdk.blocks.children.list(**kwargs)
        blocks = [_block_from_response(b) for b in data.get("results", [])]
        next_cursor = data.get("next_cursor") if data.get("has_more") else None
        return blocks, next_cursor

    def search(
        self,
        query: str | None = None,
        filter_object_type: str | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Search pages and databases shared with the integration.

        Args:
            query: Text to search for (empty/None returns all shared objects)
            filter_object_type: Restrict results to "page" or "database"
            page_size: Max number of results to return

        Returns:
            List of raw Notion object dicts (pages and/or databases) -- kept
            raw rather than coerced to NotionPage/NotionDatabase because
            search results mix both object types in one list.

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        kwargs: dict[str, Any] = {"page_size": page_size}
        if query:
            kwargs["query"] = query
        if filter_object_type:
            kwargs["filter"] = {"property": "object", "value": filter_object_type}

        data = self._sdk.search(**kwargs)
        results: list[dict[str, Any]] = data.get("results", [])
        return results

    # ------------------------------------------------------------------
    # Read: databases / data sources
    # ------------------------------------------------------------------

    def get_database(self, database_id: str) -> NotionDatabase:
        """Retrieve a database's metadata (title, properties, data sources).

        Args:
            database_id: Notion database ID

        Returns:
            NotionDatabase object

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        data = self._sdk.databases.retrieve(database_id=database_id)
        return _database_from_response(data)

    def list_data_sources(self, database_id: str) -> list[NotionDataSource]:
        """List the data sources contained in a database.

        Args:
            database_id: Notion database ID

        Returns:
            List of NotionDataSource objects
        """
        return self.get_database(database_id).data_sources

    def query_data_source(
        self,
        data_source_id: str,
        filter: dict[str, Any] | None = None,  # noqa: A002 -- matches the Notion API's own "filter" field name; shadowing the builtin is the clearest name here (see GitHub client.py, no `filter` precedent, but same convention as notion_client's own DataSourcesEndpoint.query kwarg)
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
        start_cursor: str | None = None,
    ) -> tuple[list[NotionPage], str | None]:
        """Query a specific data source directly (bypasses database resolution).

        Args:
            data_source_id: Notion data source ID
            filter: Notion filter object (see Notion API docs for shape)
            sorts: List of Notion sort objects
            page_size: Max number of results to return in this page
            start_cursor: Pagination cursor from a previous call

        Returns:
            Tuple of (pages, next_cursor). next_cursor is None when there
            are no more results.

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        kwargs: dict[str, Any] = {
            "data_source_id": data_source_id,
            "page_size": page_size,
        }
        if filter:
            kwargs["filter"] = filter
        if sorts:
            kwargs["sorts"] = sorts
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        data = self._sdk.data_sources.query(**kwargs)
        pages = [_page_from_response(p) for p in data.get("results", [])]
        next_cursor = data.get("next_cursor") if data.get("has_more") else None
        return pages, next_cursor

    def query_database(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,  # noqa: A002 -- see query_data_source's identical noqa
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
        start_cursor: str | None = None,
    ) -> tuple[list[NotionPage], str | None]:
        """Query a database's (first / default) data source with an optional filter.

        Convenience entry point for the common case (see this module's
        docstring): resolves the database's first data source, then queries
        it. A database with more than one data source should call
        `list_data_sources` + `query_data_source` directly instead.

        Args:
            database_id: Notion database ID
            filter: Notion filter object (see Notion API docs for shape)
            sorts: List of Notion sort objects
            page_size: Max number of results to return in this page
            start_cursor: Pagination cursor from a previous call

        Returns:
            Tuple of (pages, next_cursor).

        Raises:
            NotionNoDataSourceError: If the database has no data source
            notion_client.errors.APIResponseError: If the API request fails
        """
        database = self.get_database(database_id)
        if not database.data_sources:
            raise NotionNoDataSourceError(
                f"Database {database_id} has no queryable data source"
            )

        data_source_id = database.data_sources[0].id
        return self.query_data_source(
            data_source_id=data_source_id,
            filter=filter,
            sorts=sorts,
            page_size=page_size,
            start_cursor=start_cursor,
        )

    # ------------------------------------------------------------------
    # Write: pages
    # ------------------------------------------------------------------

    def create_page(
        self,
        parent: dict[str, Any],
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> NotionPage:
        """Create a new page (in a database's data source, or under a page).

        Args:
            parent: Notion parent reference, e.g.
                {"type": "data_source_id", "data_source_id": "..."} to create
                a database entry, or {"type": "page_id", "page_id": "..."} to
                create a sub-page.
            properties: Property values for the new page (its database-entry
                column values, or just {"title": [...]} for a plain sub-page)
            children: Optional initial content blocks

        Returns:
            NotionPage object for the created page

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        kwargs: dict[str, Any] = {"parent": parent, "properties": properties}
        if children:
            kwargs["children"] = children

        data = self._sdk.pages.create(**kwargs)
        return _page_from_response(data)

    def create_database_entry(
        self,
        database_id: str,
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> NotionPage:
        """Create a new entry (page) in a database's default data source.

        Convenience wrapper over create_page that resolves the database's
        first data source the same way query_database does, so a caller
        adding a row to a database does not need to learn the data-source
        split for the common single-data-source case.

        Args:
            database_id: Notion database ID
            properties: Property values for the new entry
            children: Optional initial content blocks

        Returns:
            NotionPage object for the created entry

        Raises:
            NotionNoDataSourceError: If the database has no data source
            notion_client.errors.APIResponseError: If the API request fails
        """
        database = self.get_database(database_id)
        if not database.data_sources:
            raise NotionNoDataSourceError(
                f"Database {database_id} has no data source to add an entry to"
            )

        parent = {
            "type": "data_source_id",
            "data_source_id": database.data_sources[0].id,
        }
        return self.create_page(parent=parent, properties=properties, children=children)

    def update_page(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
    ) -> NotionPage:
        """Update a page's properties (a database entry's column values) or
        archived state.

        Args:
            page_id: Notion page ID
            properties: Property values to update
            archived: Set True to archive (soft-delete), False to restore

        Returns:
            Updated NotionPage object

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        kwargs: dict[str, Any] = {"page_id": page_id}
        if properties is not None:
            kwargs["properties"] = properties
        if archived is not None:
            kwargs["archived"] = archived

        data = self._sdk.pages.update(**kwargs)
        return _page_from_response(data)

    # ------------------------------------------------------------------
    # Write: blocks
    # ------------------------------------------------------------------

    def append_blocks(
        self, block_id: str, children: list[dict[str, Any]]
    ) -> list[NotionBlock]:
        """Append content blocks to a page or block.

        Args:
            block_id: Notion page or block ID to append under
            children: List of Notion block objects to append (see Notion API
                docs for block object shape, e.g.
                {"object": "block", "type": "paragraph",
                 "paragraph": {"rich_text": [...]}})

        Returns:
            List of NotionBlock objects that were appended

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        data = self._sdk.blocks.children.append(block_id=block_id, children=children)
        return [_block_from_response(b) for b in data.get("results", [])]

    def update_block(self, block_id: str, **fields: Any) -> NotionBlock:  # noqa: ANN401 -- passthrough to notion_client's own type-specific block update payload (e.g. paragraph=..., to_do=...), genuinely heterogeneous per block type
        """Update a single block's content (e.g. mark a to_do complete).

        Args:
            block_id: Notion block ID
            **fields: Block-type-specific update payload, e.g.
                `to_do={"checked": True}`

        Returns:
            Updated NotionBlock object

        Raises:
            notion_client.errors.APIResponseError: If the API request fails
        """
        data = self._sdk.blocks.update(block_id=block_id, **fields)
        return _block_from_response(data)


# ----------------------------------------------------------------------
# Response -> model coercion helpers
# ----------------------------------------------------------------------


def _page_from_response(data: dict[str, Any]) -> NotionPage:
    """Build a NotionPage from a raw Notion API page object."""
    return NotionPage(
        id=data.get("id", ""),
        url=data.get("url"),
        created_time=data.get("created_time"),
        last_edited_time=data.get("last_edited_time"),
        archived=data.get("archived", False),
        parent=data.get("parent", {}),
        properties=data.get("properties", {}),
    )


def _database_from_response(data: dict[str, Any]) -> NotionDatabase:
    """Build a NotionDatabase from a raw Notion API database object."""
    title_parts = data.get("title", [])
    title = "".join(part.get("plain_text", "") for part in title_parts)

    data_sources = [
        NotionDataSource(id=ds.get("id", ""), name=ds.get("name"))
        for ds in data.get("data_sources", [])
    ]

    return NotionDatabase(
        id=data.get("id", ""),
        title=title,
        url=data.get("url"),
        data_sources=data_sources,
        properties=data.get("properties", {}),
    )


def _block_from_response(data: dict[str, Any]) -> NotionBlock:
    """Build a NotionBlock from a raw Notion API block object."""
    block_type = data.get("type", "")
    return NotionBlock(
        id=data.get("id", ""),
        type=block_type,
        has_children=data.get("has_children", False),
        content=data.get(block_type, {}) if block_type else {},
    )
