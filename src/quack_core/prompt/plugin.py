# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/plugin.py
# module: quack_core.prompt.plugin
# role: plugin
# neighbors: __init__.py, registry.py, booster.py, enhancer.py, strategy_base.py
# exports: PromptBoosterPlugin, create_plugin
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Plugin module for the PromptBooster.

This module provides a plugin interface for the PromptBooster to
integrate with the QuackCore plugin system.
"""

from collections.abc import Callable
from typing import Any

from .booster import PromptBooster
from .registry import (
    find_strategies_by_tags,
    get_all_strategies,
    get_strategy_by_id,
    register_prompt_strategy,
)
from .strategy_base import PromptStrategy


class PromptBoosterPlugin:
    """
    QuackCore plugin for the PromptBooster.

    This plugin provides access to PromptBooster functionality through
    the QuackCore plugin system.
    """

    def __init__(self):
        """Initialize the PromptBooster plugin."""
        self.name = "prompt_booster"
        self.version = "1.0.0"
        self.description = "A plugin for creating and enhancing prompts"

    def create_booster(
        self,
        raw_prompt: str,
        schema: str | None = None,
        examples: list[str] | str | None = None,
        tags: list[str] | None = None,
        strategy_id: str | None = None,
    ) -> PromptBooster:
        """
        Create a new PromptBooster instance.

        Args:
            raw_prompt: The original user-defined prompt
            schema: Optional schema for structured output
            examples: Optional examples for few-shot learning
            tags: Optional tags to help select an appropriate strategy
            strategy_id: Optional specific strategy ID to use

        Returns:
            A new PromptBooster instance
        """
        return PromptBooster(
            raw_prompt=raw_prompt,
            schema=schema,
            examples=examples,
            tags=tags,
            strategy_id=strategy_id,
        )

    def register_strategy(
        self,
        id: str,
        label: str,
        description: str,
        input_vars: list[str],
        render_fn: Callable[..., str],
        tags: list[str] | None = None,
        origin: str | None = None,
    ) -> PromptStrategy:
        """
        Register a new prompt strategy.

        Args:
            id: Unique identifier for the strategy
            label: Human-readable name for the strategy
            description: Detailed explanation of what the strategy does
            input_vars: List of input variables required by the strategy
            render_fn: Function that renders the prompt
            tags: Optional tags for categorizing strategies
            origin: Optional source of the strategy

        Returns:
            The registered PromptStrategy

        Raises:
            ValueError: If a strategy with the same ID already exists
        """
        strategy = PromptStrategy(
            id=id,
            label=label,
            description=description,
            input_vars=input_vars,
            render_fn=render_fn,
            tags=tags or [],
            origin=origin,
        )
        register_prompt_strategy(strategy)
        return strategy

    def get_strategy(self, strategy_id: str) -> PromptStrategy:
        """
        Get a prompt strategy by ID.

        Args:
            strategy_id: The ID of the strategy to retrieve

        Returns:
            The prompt strategy with the specified ID

        Raises:
            KeyError: If no strategy with the specified ID exists
        """
        return get_strategy_by_id(strategy_id)

    def find_strategies(self, tags: list[str]) -> list[PromptStrategy]:
        """
        Find prompt strategies that match the specified tags.

        Args:
            tags: The tags to search for

        Returns:
            A list of prompt strategies matching the tags
        """
        return find_strategies_by_tags(tags)

    def list_strategies(self) -> list[dict[str, Any]]:
        """
        List all registered prompt strategies.

        Returns:
            A list of dictionaries containing strategy information
        """
        strategies = get_all_strategies()
        return [
            {
                "id": s.id,
                "label": s.label,
                "description": s.description,
                "tags": s.tags,
                "origin": s.origin,
            }
            for s in strategies
        ]

    def enhance_prompt(
        self,
        booster: PromptBooster,
        model: str | None = None,
        provider: str | None = None,
    ) -> str:
        """
        Enhance a prompt using an LLM.

        Args:
            booster: The PromptBooster instance to enhance
            model: Optional specific model to use (e.g., "gpt-4o")
            provider: Optional specific provider to use (e.g., "openai")

        Returns:
            The enhanced prompt
        """
        return booster.render(use_llm=True, model=model, provider=provider)

    def estimate_token_count(self, booster: PromptBooster) -> int | None:
        """
        Estimate the token count for a prompt.

        Args:
            booster: The PromptBooster instance to analyze

        Returns:
            Estimated token count if successful, None otherwise
        """
        return booster.estimate_token_count()


def create_plugin() -> PromptBoosterPlugin:
    """
    Create a new PromptBooster plugin instance.

    Returns:
        A new PromptBoosterPlugin instance
    """
    return PromptBoosterPlugin()
