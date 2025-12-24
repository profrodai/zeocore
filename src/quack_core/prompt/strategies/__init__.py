# quack-core/src/quack_core/prompt/strategies/__init__.py
"""
Prompt strategies package for the PromptBooster.

This package contains various prompt enhancement strategies.
"""

# Import all strategies to register them
from . import (
    multi_shot_structured,
    react_agentic,
    single_shot_structured,
    task_decomposition,
    zero_shot_cot,
)

__all__ = [
    "multi_shot_structured",
    "single_shot_structured",
    "react_agentic",
    "zero_shot_cot",
    "task_decomposition",
]
