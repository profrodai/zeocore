# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/packs/internal/__init__.py
# module: quack_core.prompt.packs.internal.__init__
# role: module
# exports: load
# git_branch: refactor/toolkitWorkflow
# git_commit: 9e6703a
# === QV-LLM:END ===

"""
Internal strategy loader for the PromptService.

This module loads all core strategies into the registry.
"""

from quack_core.prompt._internal.registry import StrategyRegistry
from quack_core.prompt.strategies.core import get_internal_strategies


def load(registry: StrategyRegistry) -> int:
    """
    Load the internal core strategies into the provided registry.
    Returns the number of strategies loaded.
    """
    strategies = get_internal_strategies()

    count = 0
    for strat in strategies:
        try:
            registry.register(strat)
            count += 1
        except ValueError:
            # Strategy already exists, ignore
            pass

    return count
