# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/_internal/registry.py
# module: quack_core.prompt._internal.registry
# role: module
# neighbors: __init__.py, enhancer.py, selector.py
# exports: StrategyRegistry
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

from collections.abc import Sequence

from quack_core.prompt.models import PromptStrategy


class StrategyRegistry:
    # ... [Same as before, just updated import] ...
    # (re-pasted for completeness)
    """
    Internal registry for managing prompt strategies.
    Instance-based, no global state.
    """

    def __init__(self) -> None:
        self._strategies: dict[str, PromptStrategy] = {}

    def register(self, strategy: PromptStrategy) -> None:
        """Register a strategy. Raises ValueError if ID exists."""
        if strategy.id in self._strategies:
            raise ValueError(f"Strategy with ID '{strategy.id}' already exists")
        self._strategies[strategy.id] = strategy

    def get(self, strategy_id: str) -> PromptStrategy | None:
        """Get a strategy by ID. Returns None if not found."""
        return self._strategies.get(strategy_id)

    def find_by_tags(self, tags: Sequence[str], *, match_any: bool = False) -> list[
        PromptStrategy]:
        """
        Find strategies matching the provided tags.

        Args:
            tags: List of tags to search for.
            match_any: If True, matches if ANY tag is present.
                       If False (default), matches only if ALL tags are present.
        """
        matches = []
        for strategy in self._strategies.values():
            if match_any:
                if any(tag in strategy.tags for tag in tags):
                    matches.append(strategy)
            else:
                if all(tag in strategy.tags for tag in tags):
                    matches.append(strategy)
        return matches

    def list_all(self) -> list[PromptStrategy]:
        """List all registered strategies."""
        return list(self._strategies.values())

    def clear(self) -> None:
        """Clear the registry."""
        self._strategies.clear()
