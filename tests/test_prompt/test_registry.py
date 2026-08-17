"""
Tests for zeo_core.prompt._internal.registry.StrategyRegistry.
"""

import pytest
from zeo_core.prompt._internal.registry import StrategyRegistry
from zeo_core.prompt.models import PromptStrategy


def _make_strategy(strategy_id: str, tags: list[str] | None = None) -> PromptStrategy:
    def render_fn(task_description: str) -> str:
        return task_description

    return PromptStrategy(
        id=strategy_id,
        label=strategy_id,
        description=strategy_id,
        input_vars=["task_description"],
        render_fn=render_fn,
        tags=tags or [],
    )


def test_register_and_get() -> None:
    registry = StrategyRegistry()
    strat = _make_strategy("s1")
    registry.register(strat)
    assert registry.get("s1") is strat


def test_register_duplicate_raises_value_error() -> None:
    registry = StrategyRegistry()
    registry.register(_make_strategy("dup"))
    with pytest.raises(ValueError, match="already exists"):
        registry.register(_make_strategy("dup"))


def test_get_missing_returns_none() -> None:
    registry = StrategyRegistry()
    assert registry.get("missing") is None


def test_find_by_tags_match_all_default() -> None:
    registry = StrategyRegistry()
    registry.register(_make_strategy("both", tags=["a", "b"]))
    registry.register(_make_strategy("only-a", tags=["a"]))

    matches = registry.find_by_tags(["a", "b"])
    assert [s.id for s in matches] == ["both"]


def test_find_by_tags_match_any() -> None:
    registry = StrategyRegistry()
    registry.register(_make_strategy("has-a", tags=["a"]))
    registry.register(_make_strategy("has-b", tags=["b"]))
    registry.register(_make_strategy("has-neither", tags=["c"]))

    matches = registry.find_by_tags(["a", "b"], match_any=True)
    ids = {s.id for s in matches}
    assert ids == {"has-a", "has-b"}


def test_find_by_tags_no_matches_returns_empty_list() -> None:
    registry = StrategyRegistry()
    registry.register(_make_strategy("s1", tags=["x"]))
    assert registry.find_by_tags(["y"]) == []


def test_list_all_returns_all_registered_strategies() -> None:
    registry = StrategyRegistry()
    registry.register(_make_strategy("s1"))
    registry.register(_make_strategy("s2"))
    ids = {s.id for s in registry.list_all()}
    assert ids == {"s1", "s2"}


def test_list_all_empty_registry() -> None:
    registry = StrategyRegistry()
    assert registry.list_all() == []


def test_clear_removes_all_strategies() -> None:
    registry = StrategyRegistry()
    registry.register(_make_strategy("s1"))
    registry.clear()
    assert registry.list_all() == []
    assert registry.get("s1") is None
