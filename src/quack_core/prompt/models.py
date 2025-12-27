# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/models.py
# module: quack_core.prompt.models
# role: models
# neighbors: __init__.py, service.py, plugin.py
# exports: PromptStrategy
# git_branch: refactor/newHeaders
# git_commit: bd13631
# === QV-LLM:END ===

from typing import Callable
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