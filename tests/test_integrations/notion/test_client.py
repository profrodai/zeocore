"""Tests for the Notion client wrapper (client.py).

Mocks the notion_client SDK surface directly (a MagicMock shaped like
notion_client.Client: .pages, .databases, .data_sources, .blocks.children,
.search) -- no real Notion API token or network access required, mirroring
GitHub's TestGitHubMockedIntegration pattern one directory over.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from zeo_core.integrations.notion.client import NotionClient, NotionNoDataSourceError
from zeo_core.integrations.notion.models import NotionBlock, NotionDatabase, NotionPage

RAW_PAGE: dict[str, Any] = {
    "id": "page-1",
    "url": "https://notion.so/page-1",
    "created_time": "2026-01-01T00:00:00.000Z",
    "last_edited_time": "2026-01-02T00:00:00.000Z",
    "archived": False,
    "parent": {"type": "data_source_id", "data_source_id": "ds-1"},
    "properties": {"Name": {"title": [{"plain_text": "Task One"}]}},
}

RAW_DATABASE: dict[str, Any] = {
    "id": "db-1",
    "title": [{"plain_text": "Tasks"}],
    "url": "https://notion.so/db-1",
    "data_sources": [{"id": "ds-1", "name": "Tasks"}],
    "properties": {"Name": {"type": "title"}},
}

RAW_BLOCK: dict[str, Any] = {
    "id": "block-1",
    "type": "paragraph",
    "has_children": False,
    "paragraph": {"rich_text": [{"plain_text": "hello"}]},
}


@pytest.fixture
def fake_sdk() -> MagicMock:
    """A MagicMock shaped like notion_client.Client."""
    sdk = MagicMock()
    sdk.pages.retrieve.return_value = RAW_PAGE
    sdk.pages.create.return_value = RAW_PAGE
    sdk.pages.update.return_value = RAW_PAGE
    sdk.databases.retrieve.return_value = RAW_DATABASE
    sdk.data_sources.query.return_value = {
        "results": [RAW_PAGE],
        "has_more": False,
        "next_cursor": None,
    }
    sdk.blocks.children.list.return_value = {
        "results": [RAW_BLOCK],
        "has_more": False,
        "next_cursor": None,
    }
    sdk.blocks.children.append.return_value = {"results": [RAW_BLOCK]}
    sdk.blocks.update.return_value = RAW_BLOCK
    sdk.search.return_value = {"results": [RAW_PAGE, RAW_DATABASE]}
    return sdk


@pytest.fixture
def client(fake_sdk: MagicMock) -> NotionClient:
    return NotionClient(token="test_token", sdk_client=fake_sdk)  # noqa: S106 -- test fixture


class TestNotionClientRead:
    """Read-path tests."""

    def test_get_page(self, client: NotionClient, fake_sdk: MagicMock) -> None:
        page = client.get_page("page-1")

        assert isinstance(page, NotionPage)
        assert page.id == "page-1"
        assert page.url == "https://notion.so/page-1"
        assert page.archived is False
        assert page.properties == RAW_PAGE["properties"]
        fake_sdk.pages.retrieve.assert_called_once_with(page_id="page-1")

    def test_list_page_blocks(self, client: NotionClient, fake_sdk: MagicMock) -> None:
        blocks, next_cursor = client.list_page_blocks("page-1")

        assert len(blocks) == 1
        assert isinstance(blocks[0], NotionBlock)
        assert blocks[0].type == "paragraph"
        assert blocks[0].content == {"rich_text": [{"plain_text": "hello"}]}
        assert next_cursor is None
        fake_sdk.blocks.children.list.assert_called_once_with(
            block_id="page-1", page_size=100
        )

    def test_list_page_blocks_pagination(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        fake_sdk.blocks.children.list.return_value = {
            "results": [RAW_BLOCK],
            "has_more": True,
            "next_cursor": "cursor-2",
        }

        blocks, next_cursor = client.list_page_blocks("page-1", start_cursor="cursor-1")

        assert len(blocks) == 1
        assert next_cursor == "cursor-2"
        fake_sdk.blocks.children.list.assert_called_once_with(
            block_id="page-1", page_size=100, start_cursor="cursor-1"
        )

    def test_search(self, client: NotionClient, fake_sdk: MagicMock) -> None:
        results = client.search(query="Tasks", filter_object_type="page")

        assert len(results) == 2
        fake_sdk.search.assert_called_once_with(
            page_size=100,
            query="Tasks",
            filter={"property": "object", "value": "page"},
        )

    def test_get_database(self, client: NotionClient, fake_sdk: MagicMock) -> None:
        database = client.get_database("db-1")

        assert isinstance(database, NotionDatabase)
        assert database.id == "db-1"
        assert database.title == "Tasks"
        assert len(database.data_sources) == 1
        assert database.data_sources[0].id == "ds-1"
        fake_sdk.databases.retrieve.assert_called_once_with(database_id="db-1")

    def test_list_data_sources(self, client: NotionClient) -> None:
        sources = client.list_data_sources("db-1")
        assert len(sources) == 1
        assert sources[0].id == "ds-1"

    def test_query_data_source_direct(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        pages, next_cursor = client.query_data_source(
            "ds-1",
            filter={"property": "Status", "select": {"equals": "Done"}},
            sorts=[{"property": "Name", "direction": "ascending"}],
        )

        assert len(pages) == 1
        assert isinstance(pages[0], NotionPage)
        assert next_cursor is None
        fake_sdk.data_sources.query.assert_called_once_with(
            data_source_id="ds-1",
            page_size=100,
            filter={"property": "Status", "select": {"equals": "Done"}},
            sorts=[{"property": "Name", "direction": "ascending"}],
        )

    def test_query_database_resolves_default_data_source(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        """The high-leverage convenience path: query_database hides the
        2025-09-03 API's data-source indirection -- a caller passes only a
        database_id and gets pages back, exactly like the pre-2025 API's
        databases.query(database_id, filter=...) shape."""
        pages, next_cursor = client.query_database(
            "db-1", filter={"property": "Status", "select": {"equals": "Done"}}
        )

        assert len(pages) == 1
        assert next_cursor is None
        fake_sdk.databases.retrieve.assert_called_once_with(database_id="db-1")
        fake_sdk.data_sources.query.assert_called_once_with(
            data_source_id="ds-1",
            page_size=100,
            filter={"property": "Status", "select": {"equals": "Done"}},
        )

    def test_query_database_no_data_source_raises(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        fake_sdk.databases.retrieve.return_value = {**RAW_DATABASE, "data_sources": []}

        with pytest.raises(NotionNoDataSourceError):
            client.query_database("db-1")

    def test_query_data_source_with_start_cursor(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        client.query_data_source("ds-1", start_cursor="cursor-1")

        fake_sdk.data_sources.query.assert_called_once_with(
            data_source_id="ds-1", page_size=100, start_cursor="cursor-1"
        )


class TestNotionClientWrite:
    """Write-path tests -- the operator's explicit ask."""

    def test_create_page(self, client: NotionClient, fake_sdk: MagicMock) -> None:
        parent = {"type": "page_id", "page_id": "parent-1"}
        properties = {"title": [{"text": {"content": "New sub-page"}}]}

        page = client.create_page(parent=parent, properties=properties)

        assert isinstance(page, NotionPage)
        assert page.id == "page-1"
        fake_sdk.pages.create.assert_called_once_with(
            parent=parent, properties=properties
        )

    def test_create_page_with_children(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        parent = {"type": "page_id", "page_id": "parent-1"}
        properties = {"title": [{"text": {"content": "New sub-page"}}]}
        children = [{"object": "block", "type": "paragraph"}]

        client.create_page(parent=parent, properties=properties, children=children)

        fake_sdk.pages.create.assert_called_once_with(
            parent=parent, properties=properties, children=children
        )

    def test_create_database_entry_resolves_data_source(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        properties = {"Name": {"title": [{"text": {"content": "New task"}}]}}

        page = client.create_database_entry("db-1", properties=properties)

        assert isinstance(page, NotionPage)
        fake_sdk.databases.retrieve.assert_called_once_with(database_id="db-1")
        fake_sdk.pages.create.assert_called_once_with(
            parent={"type": "data_source_id", "data_source_id": "ds-1"},
            properties=properties,
        )

    def test_create_database_entry_no_data_source_raises(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        fake_sdk.databases.retrieve.return_value = {**RAW_DATABASE, "data_sources": []}

        with pytest.raises(NotionNoDataSourceError):
            client.create_database_entry("db-1", properties={})

    def test_update_page_properties(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        properties = {"Status": {"select": {"name": "Done"}}}

        page = client.update_page("page-1", properties=properties)

        assert isinstance(page, NotionPage)
        fake_sdk.pages.update.assert_called_once_with(
            page_id="page-1", properties=properties
        )

    def test_update_page_archive(
        self, client: NotionClient, fake_sdk: MagicMock
    ) -> None:
        client.update_page("page-1", archived=True)

        # ``archived`` remains a caller compatibility alias, but API
        # 2026-03-11 removed that wire key in favour of ``in_trash``.
        fake_sdk.pages.update.assert_called_once_with(page_id="page-1", in_trash=True)

    def test_append_blocks(self, client: NotionClient, fake_sdk: MagicMock) -> None:
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": "hi"}}]},
            }
        ]

        blocks = client.append_blocks("page-1", children=children)

        assert len(blocks) == 1
        assert isinstance(blocks[0], NotionBlock)
        fake_sdk.blocks.children.append.assert_called_once_with(
            block_id="page-1", children=children
        )

    def test_update_block(self, client: NotionClient, fake_sdk: MagicMock) -> None:
        block = client.update_block("block-1", to_do={"checked": True})

        assert isinstance(block, NotionBlock)
        fake_sdk.blocks.update.assert_called_once_with(
            block_id="block-1", to_do={"checked": True}
        )


class TestNotionClientInit:
    """Constructor / default-SDK-wiring behavior."""

    def test_real_sdk_client_constructed_when_none_injected(self) -> None:
        """Without an injected sdk_client, NotionClient builds a real
        notion_client.Client -- confirms the wiring is real, not just that
        the injection seam exists."""
        import notion_client

        client = NotionClient(token="real_token_shape")  # noqa: S106 -- test fixture
        assert isinstance(client._sdk, notion_client.Client)
