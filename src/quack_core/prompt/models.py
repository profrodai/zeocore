# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/models.py
# module: quack_core.prompt.models
# role: models
# neighbors: __init__.py, service.py, plugin.py
# exports: PromptStrategy, StrategyInfo
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field


class PromptStrategy(BaseModel):
    """
    A reusable prompt strategy definition.
    """
    id: str = Field(..., description="Unique identifier for the strategy")
    label: str = Field(..., description="Human-readable name for the strategy")
    description: str = Field(...,
                             description="Detailed explanation of what the strategy does")
    input_vars: list[str] = Field(..., description="List of input variables required")

    # exclude=True ensures this callable isn't serialized, preventing crashes during logging/dumping
    render_fn: Callable[..., str] = Field(...,
                                          description="Function that renders the prompt",
                                          exclude=True)

    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    origin: str | None = Field(None, description="Source of the strategy")
    example: str | None = Field(None, description="Illustrative example")
    priority: int = Field(default=100,
                          description="Selection priority. Lower value = higher preference.")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class StrategyInfo(BaseModel):
    """
    Public DTO for listing strategies safely without internal implementation details.
    """
    id: str
    label: str
    description: str
    input_vars: list[str]
    tags: list[str]
    origin: str | None = None
    priority: int
    example: str | None = None

    @classmethod
    def from_strategy(cls, strategy: PromptStrategy) -> "StrategyInfo":
        return cls(
            id=strategy.id,
            label=strategy.label,
            description=strategy.description,
            input_vars=strategy.input_vars,
            tags=strategy.tags,
            origin=strategy.origin,
            priority=strategy.priority,
            example=strategy.example
        )
