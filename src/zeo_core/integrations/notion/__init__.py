"""Notion integration for zeo_core.

Complete Notion API 2026-03-11 access via the official `notion-client` SDK.
Follows the same shape as `integrations.github` and
`integrations.google` -- a config provider, an auth provider, a thin SDK
client wrapper, and a service class implementing `NotionIntegrationProtocol`
-- and registers under the `zeo_core.integrations` entry-point group the
same way (see this repo's `pyproject.toml`,
`[project.entry-points."zeo_core.integrations"]`, key `notion`).

Quickstart::

    from zeo_core.integrations.notion import NotionIntegration

    notion = NotionIntegration()  # reads NOTION_TOKEN from the environment
    result = notion.initialize()
    assert result.success

    # Read: query a database with a filter
    pages = notion.query_database(
        database_id="...",
        filter={"property": "Status", "select": {"equals": "Done"}},
    )

    # Write: create an entry in that database
    created = notion.create_database_entry(
        database_id="...",
        properties={"Name": {"title": [{"text": {"content": "New task"}}]}},
    )

    # Write: append a paragraph block to the new page
    notion.append_blocks(
        block_id=created.content.id,
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": "Hello"}}]
                },
            }
        ],
    )

Every call returns an `IntegrationResult[T]` (`.success`, `.content`,
`.error`) -- see `zeo_core.integrations.core.results`.
"""

from __future__ import annotations

from .auth import NotionAuthProvider
from .client import (
    NOTION_API_VERSION,
    NotionAPIError,
    NotionClient,
    NotionNoDataSourceError,
    NotionOperation,
)
from .config import NotionConfig, NotionConfigProvider
from .models import (
    NotionBlock,
    NotionDatabase,
    NotionDataSource,
    NotionPage,
    NotionPageResult,
    NotionUser,
)
from .oauth import NotionOAuthBroker, NotionOAuthGrant
from .protocols import NotionIntegrationProtocol
from .service import NotionIntegration

__all__ = [
    # Main classes
    "NotionIntegration",
    "NotionClient",
    "NotionAuthProvider",
    "NotionConfigProvider",
    # Protocols
    "NotionIntegrationProtocol",
    # Models
    "NotionBlock",
    "NotionDatabase",
    "NotionDataSource",
    "NotionPage",
    "NotionUser",
    "NotionConfig",
    "NotionOAuthBroker",
    "NotionOAuthGrant",
    "NotionPageResult",
    "NotionOperation",
    "NOTION_API_VERSION",
    # Errors
    "NotionNoDataSourceError",
    "NotionAPIError",
    # Factory function
    "create_integration",
]


def create_integration() -> NotionIntegration:
    """
    Create and return a Notion integration instance.

    This function is the entry point for integration loading.

    Returns:
        NotionIntegration instance
    """
    return NotionIntegration()
