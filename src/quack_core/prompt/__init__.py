# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/__init__.py
# module: quack_core.prompt.__init__
# role: module
# neighbors: service.py, models.py, plugin.py
# exports: PromptService, PromptStrategy, create_default_prompt_service, PromptRenderResult, StrategyListResult, GetStrategyResult, RegisterStrategyResult, LoadPackResult
# git_branch: refactor/newHeaders
# git_commit: bd13631
# === QV-LLM:END ===

"""
QuackCore Prompt module.

Provides a service for creating, managing, and rendering high-quality prompts
using codified strategies.
"""

from quack_core.prompt.service import PromptService
from quack_core.prompt.models import PromptStrategy
from quack_core.prompt.api.public.results import (
    PromptRenderResult,
    StrategyListResult,
    GetStrategyResult,
    RegisterStrategyResult,
    LoadPackResult
)

def create_default_prompt_service() -> PromptService:
    """Factory to create a service with internal strategies pre-loaded."""
    return PromptService(load_defaults=True)

__all__ = [
    "PromptService",
    "PromptStrategy",
    "create_default_prompt_service",
    "PromptRenderResult",
    "StrategyListResult",
    "GetStrategyResult",
    "RegisterStrategyResult",
    "LoadPackResult"
]