# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/registry.py
# module: quack_core.prompt.registry
# role: module
# neighbors: __init__.py, plugin.py, booster.py, enhancer.py, strategy_base.py
# exports: register_prompt_strategy, get_strategy_by_id, find_strategies_by_tags, get_all_strategies, clear_registry
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Registry module for the PromptBooster.

This module provides functions to register, retrieve, and search for
prompt strategies in the QuackCore ecosystem.
"""

from collections.abc import Sequence

from .strategy_base import PromptStrategy

# Global registry to store all prompt strategies
_STRATEGY_REGISTRY: dict[str, PromptStrategy] = {}


def register_prompt_strategy(strategy: PromptStrategy) -> None:
    """
    Register a prompt strategy in the global registry.

    Args:
        strategy: The prompt strategy to register

    Raises:
        ValueError: If a strategy with the same ID already exists
    """
    if strategy.id in _STRATEGY_REGISTRY:
        raise ValueError(f"Strategy with ID '{strategy.id}' already exists in registry")
    _STRATEGY_REGISTRY[strategy.id] = strategy


def get_strategy_by_id(strategy_id: str) -> PromptStrategy:
    """
    Get a prompt strategy from the registry by its ID.

    Args:
        strategy_id: The ID of the strategy to retrieve

    Returns:
        The prompt strategy with the specified ID

    Raises:
        KeyError: If no strategy with the specified ID exists
    """
    if strategy_id not in _STRATEGY_REGISTRY:
        raise KeyError(f"No strategy found with ID '{strategy_id}'")
    return _STRATEGY_REGISTRY[strategy_id]


def find_strategies_by_tags(tags: Sequence[str]) -> list[PromptStrategy]:
    """
    Find all prompt strategies that match the specified tags.

    A strategy matches if it contains ANY of the specified tags.

    Args:
        tags: The tags to search for

    Returns:
        A list of prompt strategies matching the tags
    """
    matching_strategies = []
    for strategy in _STRATEGY_REGISTRY.values():
        if any(tag in strategy.tags for tag in tags):
            matching_strategies.append(strategy)
    return matching_strategies


def get_all_strategies() -> list[PromptStrategy]:
    """
    Get all registered prompt strategies.

    Returns:
        A list of all registered prompt strategies
    """
    return list(_STRATEGY_REGISTRY.values())


def clear_registry() -> None:
    """
    Clear the strategy registry.

    This is primarily useful for testing.
    """
    _STRATEGY_REGISTRY.clear()
