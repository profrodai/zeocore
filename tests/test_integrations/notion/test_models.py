"""Tests for Notion integration data models."""

from datetime import datetime

from zeo_core.integrations.notion.models import (
    NotionBlock,
    NotionDatabase,
    NotionDataSource,
    NotionPage,
    NotionUser,
)


class TestNotionUser:
    def test_str_uses_name(self) -> None:
        user = NotionUser(id="u1", name="Rod")
        assert str(user) == "Rod"

    def test_str_falls_back_to_id(self) -> None:
        user = NotionUser(id="u1")
        assert str(user) == "u1"


class TestNotionPage:
    def test_defaults(self) -> None:
        page = NotionPage(id="p1")
        assert page.url is None
        assert page.archived is False
        assert page.properties == {}
        assert page.parent == {}

    def test_str(self) -> None:
        page = NotionPage(id="p1")
        assert str(page) == "p1"

    def test_equality_by_id(self) -> None:
        assert NotionPage(id="p1") == NotionPage(id="p1")
        assert NotionPage(id="p1") == "p1"
        assert NotionPage(id="p1") != NotionPage(id="p2")
        assert NotionPage(id="p1") != 42

    def test_with_timestamps(self) -> None:
        page = NotionPage(
            id="p1",
            created_time=datetime(2026, 1, 1),
            last_edited_time=datetime(2026, 1, 2),
        )
        assert page.created_time == datetime(2026, 1, 1)
        assert page.last_edited_time == datetime(2026, 1, 2)


class TestNotionDatabase:
    def test_defaults(self) -> None:
        db = NotionDatabase(id="db1")
        assert db.title == ""
        assert db.data_sources == []

    def test_str_uses_title_or_id(self) -> None:
        assert str(NotionDatabase(id="db1", title="Tasks")) == "Tasks"
        assert str(NotionDatabase(id="db1")) == "db1"

    def test_equality_by_id(self) -> None:
        assert NotionDatabase(id="db1") == NotionDatabase(id="db1")
        assert NotionDatabase(id="db1") == "db1"
        assert NotionDatabase(id="db1") != NotionDatabase(id="db2")
        assert NotionDatabase(id="db1") != 42

    def test_data_sources(self) -> None:
        db = NotionDatabase(
            id="db1", data_sources=[NotionDataSource(id="ds1", name="Tasks")]
        )
        assert len(db.data_sources) == 1
        assert db.data_sources[0].id == "ds1"


class TestNotionBlock:
    def test_str(self) -> None:
        block = NotionBlock(id="b1", type="paragraph")
        assert str(block) == "paragraph:b1"

    def test_content_default(self) -> None:
        block = NotionBlock(id="b1", type="paragraph")
        assert block.content == {}

    def test_has_children(self) -> None:
        block = NotionBlock(id="b1", type="toggle", has_children=True)
        assert block.has_children is True
