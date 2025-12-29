# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/core/config.py
# module: quack_core.integrations.core.config
# role: module
# neighbors: __init__.py, protocols.py, registry.py, results.py, base.py
# exports: IntegrationsConfig
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===

from pydantic import BaseModel, Field

from quack_core.integrations.google.config import GoogleConfig
from quack_core.integrations.notion.config import NotionConfig


class IntegrationsConfig(BaseModel):
    """Configuration for third-party integrations."""

    google: GoogleConfig = Field(
        default_factory=GoogleConfig, description="Google integration settings"
    )
    notion: NotionConfig = Field(
        default_factory=NotionConfig, description="Notion integration settings"
    )
