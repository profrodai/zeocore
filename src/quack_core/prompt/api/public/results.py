# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/api/public/results.py
# module: quack_core.prompt.api.public.results
# role: api
# neighbors: __init__.py
# exports: PromptRenderResult, RegisterStrategyResult, GetStrategyResult, StrategyListResult, LoadPackResult
# git_branch: refactor/toolkitWorkflow
# git_commit: 7e3e554
# === QV-LLM:END ===

from typing import Any

from pydantic import BaseModel, Field
from quack_core.prompt.models import PromptStrategy, StrategyInfo


class PromptRenderResult(BaseModel):
    """Result of a prompt rendering operation."""
    success: bool
    prompt: str | None = None
    strategy_id: str | None = None
    strategy_label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    estimated_words: int | None = None
    error: str | None = None

class RegisterStrategyResult(BaseModel):
    """Result of registering a strategy."""
    success: bool
    strategy_id: str | None = None
    error: str | None = None

class GetStrategyResult(BaseModel):
    """Result of retrieving a strategy."""
    success: bool
    strategy: PromptStrategy | None = None
    error: str | None = None

class StrategyListResult(BaseModel):
    """Result of listing strategies."""
    success: bool
    strategies: list[StrategyInfo] = Field(default_factory=list)
    error: str | None = None

class LoadPackResult(BaseModel):
    """Result of loading a strategy pack."""
    success: bool
    loaded_count: int = 0
    error: str | None = None
