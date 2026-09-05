"""Notion integration data models for zeo_core.

Common objects are typed while every raw payload remains reachable. This is
intentional: Notion's property, block, view, and file unions evolve more
quickly than ZeoCore releases, so a closed mirror would make the supposedly
complete client discard valid current fields.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class NotionPageResult(BaseModel, Generic[T]):
    """One cursor page, preserving pagination evidence the old API discarded."""

    items: list[T] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "NotionPageResult[dict[str, Any]]":
        return NotionPageResult[dict[str, Any]](
            items=data.get("results", []),
            next_cursor=data.get("next_cursor"),
            has_more=bool(data.get("has_more", False)),
            raw=data,
        )


class NotionUser(BaseModel):
    """Model representing a Notion user (person or bot)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Notion user ID")
    name: str | None = Field(default=None, description="User's display name")
    object_type: str = Field(default="user", description="Notion object type")
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)

    def __str__(self) -> str:
        """String representation of the user."""
        return self.name or self.id


class NotionPage(BaseModel):
    """Model representing a Notion page.

    `properties` is the raw Notion property-value map (e.g. a database
    entry's column values) -- kept as a dict rather than a fully-typed
    schema because Notion property shapes are database-specific and
    unbounded; a caller reads the specific properties it needs from it.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Notion page ID")
    url: str | None = Field(default=None, description="Page URL")
    created_time: datetime | None = Field(
        default=None, description="Page creation timestamp"
    )
    last_edited_time: datetime | None = Field(
        default=None, description="Last edit timestamp"
    )
    in_trash: bool = Field(default=False, description="Whether the page is in trash")
    parent: dict[str, Any] = Field(
        default_factory=dict, description="Parent reference (page/database/workspace)"
    )
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Raw property-value map for this page"
    )
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)

    @property
    def archived(self) -> bool:
        """Compatibility alias for Notion API versions before 2026-03-11."""
        return self.in_trash

    def __str__(self) -> str:
        """String representation of the page."""
        return self.id

    def __eq__(self, other: object) -> bool:
        """Equality by page ID."""
        if isinstance(other, NotionPage):
            return self.id == other.id
        if isinstance(other, str):
            return self.id == other
        return NotImplemented


class NotionDataSource(BaseModel):
    """Model representing a Notion data source (a queryable table under a database).

    Since the 2025-09-03 Notion API version, a database is a container for
    one or more data sources, and querying happens against a data source ID,
    not the database ID directly (see client.py's docstring). Most databases
    have exactly one data source; NotionClient.query_database resolves it
    automatically so most callers never need this model directly.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Notion data source ID")
    name: str | None = Field(default=None, description="Data source name")
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)


class NotionDatabase(BaseModel):
    """Model representing a Notion database."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Notion database ID")
    title: str = Field(default="", description="Database title (plain text)")
    url: str | None = Field(default=None, description="Database URL")
    in_trash: bool = Field(
        default=False, description="Whether the database is in trash"
    )
    data_sources: list[NotionDataSource] = Field(
        default_factory=list, description="Data sources contained in this database"
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Legacy database schema view; current schemas live on data sources",
    )
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)

    @property
    def archived(self) -> bool:
        """Compatibility alias for Notion API versions before 2026-03-11."""
        return self.in_trash

    def __str__(self) -> str:
        """String representation of the database."""
        return self.title or self.id

    def __eq__(self, other: object) -> bool:
        """Equality by database ID."""
        if isinstance(other, NotionDatabase):
            return self.id == other.id
        if isinstance(other, str):
            return self.id == other
        return NotImplemented


class NotionBlock(BaseModel):
    """Model representing a Notion block.

    `content` carries the block-type-specific payload (e.g. a paragraph
    block's `paragraph.rich_text`) as a raw dict -- Notion's block type
    surface is large (20+ types) and callers reading blocks generally know
    which type(s) they expect and read `content` directly, mirroring
    `properties` on NotionPage above.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Notion block ID")
    type: str = Field(description="Block type (paragraph, heading_1, to_do, ...)")
    has_children: bool = Field(
        default=False, description="Whether this block has child blocks"
    )
    in_trash: bool = Field(default=False, description="Whether the block is in trash")
    content: dict[str, Any] = Field(
        default_factory=dict, description="Type-specific block payload"
    )
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)

    @property
    def archived(self) -> bool:
        """Compatibility alias for Notion API versions before 2026-03-11."""
        return self.in_trash

    def __str__(self) -> str:
        """String representation of the block."""
        return f"{self.type}:{self.id}"
