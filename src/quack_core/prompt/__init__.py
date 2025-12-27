# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/__init__.py
# module: quack_core.prompt.__init__
# role: module
# neighbors: plugin.py, registry.py, booster.py, enhancer.py, strategy_base.py
# exports: PromptBooster, PromptStrategy, register_prompt_strategy, get_strategy_by_id, find_strategies_by_tags, get_all_strategies
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
QuackCore Prompt module.

This module provides tools and strategies for creating high-quality LLM prompts.
"""

# Import strategies package to register all strategies
from . import strategies
from .booster import PromptBooster
from .registry import (
    find_strategies_by_tags,
    get_all_strategies,
    get_strategy_by_id,
    register_prompt_strategy,
)
from .strategy_base import PromptStrategy

__all__ = [
    "PromptBooster",
    "PromptStrategy",
    "register_prompt_strategy",
    "get_strategy_by_id",
    "find_strategies_by_tags",
    "get_all_strategies",
]
