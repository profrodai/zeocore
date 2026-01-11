# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/notion/config.py
# module: quack_core.integrations.notion.config
# role: module
# neighbors: __init__.py
# exports: NotionConfig
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

from pydantic import BaseModel, Field


class NotionConfig(BaseModel):
    """Configuration for Notion integration."""

    api_key: str | None = Field(default=None, description="Notion API key")
    database_ids: dict[str, str] = Field(
        default_factory=dict, description="Mapping of database names to IDs"
    )
