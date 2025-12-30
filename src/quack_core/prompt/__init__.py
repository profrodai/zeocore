# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/__init__.py
# module: quack_core.prompt.__init__
# role: module
# neighbors: service.py, models.py, plugin.py
# exports: PromptService, PromptStrategy, StrategyInfo, create_default_prompt_service, PromptRenderResult, StrategyListResult, GetStrategyResult, RegisterStrategyResult (+1 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
QuackCore Prompt module.

Provides a service for creating, managing, and rendering high-quality prompts
using codified strategies.
"""

from quack_core.prompt.api.public.results import (
    GetStrategyResult,
    LoadPackResult,
    PromptRenderResult,
    RegisterStrategyResult,
    StrategyListResult,
)
from quack_core.prompt.models import PromptStrategy, StrategyInfo
from quack_core.prompt.service import PromptService


def create_default_prompt_service() -> PromptService:
    """Factory to create a service with internal strategies pre-loaded."""
    return PromptService(load_defaults=True)

__all__ = [
    "PromptService",
    "PromptStrategy",
    "StrategyInfo",
    "create_default_prompt_service",
    "PromptRenderResult",
    "StrategyListResult",
    "GetStrategyResult",
    "RegisterStrategyResult",
    "LoadPackResult"
]
