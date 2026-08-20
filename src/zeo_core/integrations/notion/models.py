"""Notion integration data models for zeo_core.

These models cover the scoped surface this integration supports: pages,
databases (queried through their default data source per the Notion API's
2025-09-03 data-source model -- see client.py's module docstring), and
blocks. They are deliberately NOT a full mirror of Notion's rich-text /
property-value schema (that surface is large and callers routinely need
only a handful of properties) -- `properties`/`raw` stay as loosely-typed
dict passthroughs so a caller can reach anything the trimmed model does not
name, mirroring how GitHubRepo/GitHubUser (github/models.py) model the
common fields and leave the rest reachable via the raw API response.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotionUser(BaseModel):
    """Model representing a Notion user (person or bot)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Notion user ID")
    name: str | None = Field(default=None, description="User's display name")
    object_type: str = Field(default="user", description="Notion object type")

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
    archived: bool = Field(default=False, description="Whether the page is archived")
    parent: dict[str, Any] = Field(
        default_factory=dict, description="Parent reference (page/database/workspace)"
    )
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Raw property-value map for this page"
    )

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


class NotionDatabase(BaseModel):
    """Model representing a Notion database."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Notion database ID")
    title: str = Field(default="", description="Database title (plain text)")
    url: str | None = Field(default=None, description="Database URL")
    data_sources: list[NotionDataSource] = Field(
        default_factory=list, description="Data sources contained in this database"
    )
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Raw property schema for this database"
    )

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
    content: dict[str, Any] = Field(
        default_factory=dict, description="Type-specific block payload"
    )

    def __str__(self) -> str:
        """String representation of the block."""
        return f"{self.type}:{self.id}"
