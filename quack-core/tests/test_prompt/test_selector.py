# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_prompt/test_selector.py
# === QV-LLM:END ===

"""
Tests for quack_core.prompt._internal.selector.select_best_strategy and its
helper _match_by_schema_and_examples. Uses a real StrategyRegistry loaded with
the real internal strategy pack -- no mocking, per RULING-235.
"""

from quack_core.prompt._internal.registry import StrategyRegistry
from quack_core.prompt._internal.selector import (
    _match_by_schema_and_examples,
    select_best_strategy,
)
from quack_core.prompt.packs.internal import load as load_internal


def _loaded_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    load_internal(registry)
    return registry


# --- select_best_strategy: tag matching ---


def test_select_best_strategy_by_tags() -> None:
    registry = _loaded_registry()
    result = select_best_strategy(registry, tags=["code", "debugging"])
    assert result is not None
    assert result.id == "debugging-code-prompting"


def test_select_best_strategy_tags_no_match_falls_through() -> None:
    registry = _loaded_registry()
    result = select_best_strategy(registry, tags=["no-such-tag"])
    # No tag match -> no schema -> falls back to zero-shot.
    assert result is not None
    assert result.id == "zero-shot-prompting"


# --- select_best_strategy: schema + examples heuristics ---


def test_select_best_strategy_schema_multi_shot() -> None:
    registry = _loaded_registry()
    result = select_best_strategy(
        registry, schema="{type: object}", examples=["a", "b"]
    )
    assert result is not None
    assert result.id == "multi-shot-structured"


def test_select_best_strategy_schema_single_example() -> None:
    registry = _loaded_registry()
    result = select_best_strategy(registry, schema="{type: object}", examples=["a"])
    assert result is not None
    assert result.id == "single-shot-structured"


def test_select_best_strategy_schema_string_example() -> None:
    registry = _loaded_registry()
    result = select_best_strategy(
        registry, schema="{type: object}", examples="a single example"
    )
    assert result is not None
    assert result.id == "single-shot-structured"


def test_select_best_strategy_schema_with_data_fallback() -> None:
    registry = _loaded_registry()
    result = select_best_strategy(
        registry, schema="{type: object}", extra_inputs={"data": '{"a": 1}'}
    )
    assert result is not None
    assert result.id == "working-with-schemas-prompting"


def test_select_best_strategy_schema_no_examples_no_data_falls_to_zero_shot() -> None:
    registry = _loaded_registry()
    result = select_best_strategy(registry, schema="{type: object}")
    assert result is not None
    assert result.id == "zero-shot-prompting"


# --- select_best_strategy: default fallback ---


def test_select_best_strategy_no_criteria_defaults_to_zero_shot() -> None:
    registry = _loaded_registry()
    result = select_best_strategy(registry)
    assert result is not None
    assert result.id == "zero-shot-prompting"


def test_select_best_strategy_empty_registry_returns_none() -> None:
    registry = StrategyRegistry()
    result = select_best_strategy(registry)
    assert result is None


# --- select_best_strategy: deterministic sort ---


def test_select_best_strategy_sorts_by_priority_then_id() -> None:
    registry = StrategyRegistry()

    def render_fn(task_description: str) -> str:
        return task_description

    from quack_core.prompt.models import PromptStrategy

    strat_low_priority_b = PromptStrategy(
        id="b-strategy",
        label="B",
        description="B",
        input_vars=["task_description"],
        render_fn=render_fn,
        tags=["shared-tag"],
        priority=100,
    )
    strat_low_priority_a = PromptStrategy(
        id="a-strategy",
        label="A",
        description="A",
        input_vars=["task_description"],
        render_fn=render_fn,
        tags=["shared-tag"],
        priority=100,
    )
    strat_high_priority = PromptStrategy(
        id="z-strategy",
        label="Z",
        description="Z",
        input_vars=["task_description"],
        render_fn=render_fn,
        tags=["shared-tag"],
        priority=10,
    )
    registry.register(strat_low_priority_b)
    registry.register(strat_low_priority_a)
    registry.register(strat_high_priority)

    result = select_best_strategy(registry, tags=["shared-tag"])
    # Lower priority value wins first.
    assert result is not None
    assert result.id == "z-strategy"


def test_select_best_strategy_ties_break_alphabetically_by_id() -> None:
    registry = StrategyRegistry()

    def render_fn(task_description: str) -> str:
        return task_description

    from quack_core.prompt.models import PromptStrategy

    for sid in ("z-tag-strategy", "a-tag-strategy"):
        registry.register(
            PromptStrategy(
                id=sid,
                label=sid,
                description=sid,
                input_vars=["task_description"],
                render_fn=render_fn,
                tags=["tie-tag"],
                priority=42,
            )
        )

    result = select_best_strategy(registry, tags=["tie-tag"])
    assert result is not None
    assert result.id == "a-tag-strategy"


# --- _match_by_schema_and_examples directly ---


def test_match_by_schema_and_examples_no_schema_returns_empty() -> None:
    registry = _loaded_registry()
    matches = _match_by_schema_and_examples(registry, None, ["a", "b"], {})
    assert matches == []


def test_match_by_schema_and_examples_missing_strategy_in_registry() -> None:
    """
    If the registry simply doesn't have the target strategy IDs registered,
    the helper should return no matches rather than raising.
    """
    empty_registry = StrategyRegistry()
    matches = _match_by_schema_and_examples(
        empty_registry, "{type: object}", ["a", "b"], {}
    )
    assert matches == []
