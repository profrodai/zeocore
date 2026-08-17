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
    "LoadPackResult",
]
