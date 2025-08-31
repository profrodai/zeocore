# quack-core/tests/test_prompt/test_registry.py
"""
Tests for the prompt strategy registry functionality.
"""

import pytest

from quack_core.prompt.registry import (
    _STRATEGY_REGISTRY,
    clear_registry,
    find_strategies_by_tags,
    get_all_strategies,
    get_strategy_by_id,
    register_prompt_strategy,
)
from quack_core.prompt.strategy_base import PromptStrategy


@pytest.fixture
def sample_strategies():
    """Fixture to create sample strategies for testing."""

    # Define simple render functions
    def render_fn1(prompt: str) -> str:
        return f"Strategy 1: {prompt}"

    def render_fn2(prompt: str) -> str:
        return f"Strategy 2: {prompt}"

    def render_fn3(prompt: str) -> str:
        return f"Strategy 3: {prompt}"

    # Create strategies
    strategy1 = PromptStrategy(
        id="strategy-1",
        label="Strategy One",
        description="First test strategy",
        input_vars=["prompt"],
        render_fn=render_fn1,
        tags=["basic", "test"],
    )

    strategy2 = PromptStrategy(
        id="strategy-2",
        label="Strategy Two",
        description="Second test strategy",
        input_vars=["prompt"],
        render_fn=render_fn2,
        tags=["advanced", "test"],
    )

    strategy3 = PromptStrategy(
        id="strategy-3",
        label="Strategy Three",
        description="Third test strategy",
        input_vars=["prompt"],
        render_fn=render_fn3,
        tags=["basic", "advanced", "special"],
    )

    return [strategy1, strategy2, strategy3]


@pytest.fixture(autouse=True)
def clear_registry_before_after():
    """Ensure registry is cleared before and after each test."""
    clear_registry()
    yield
    clear_registry()


def test_register_prompt_strategy(sample_strategies):
    """Test registering a strategy in the registry."""
    # Register the first strategy
    register_prompt_strategy(sample_strategies[0])

    # Check if it's in the registry
    assert "strategy-1" in _STRATEGY_REGISTRY
    assert _STRATEGY_REGISTRY["strategy-1"] == sample_strategies[0]


def test_register_duplicate_strategy(sample_strategies):
    """Test that registering a duplicate strategy raises an error."""
    # Register the first strategy
    register_prompt_strategy(sample_strategies[0])

    # Try to register it again, should raise ValueError
    with pytest.raises(
        ValueError, match="Strategy with ID 'strategy-1' already exists in registry"
    ):
        register_prompt_strategy(sample_strategies[0])


def test_get_strategy_by_id(sample_strategies):
    """Test retrieving a strategy by its ID."""
    # Register all sample strategies
    for strategy in sample_strategies:
        register_prompt_strategy(strategy)

    # Get a strategy by ID
    retrieved = get_strategy_by_id("strategy-2")
    assert retrieved == sample_strategies[1]

    # Try to get a non-existent strategy
    with pytest.raises(KeyError, match="No strategy found with ID 'non-existent'"):
        get_strategy_by_id("non-existent")


def test_find_strategies_by_tags(sample_strategies):
    """Test finding strategies by tags."""
    # Register all sample strategies
    for strategy in sample_strategies:
        register_prompt_strategy(strategy)

    # Find strategies with the "basic" tag
    basic_strategies = find_strategies_by_tags(["basic"])
    assert len(basic_strategies) == 2
    assert sample_strategies[0] in basic_strategies
    assert sample_strategies[2] in basic_strategies

    # Find strategies with the "advanced" tag
    advanced_strategies = find_strategies_by_tags(["advanced"])
    assert len(advanced_strategies) == 2
    assert sample_strategies[1] in advanced_strategies
    assert sample_strategies[2] in advanced_strategies

    # Find strategies with the "special" tag
    special_strategies = find_strategies_by_tags(["special"])
    assert len(special_strategies) == 1
    assert sample_strategies[2] in special_strategies

    # Find strategies with multiple tags (should match any tag)
    multi_tag_strategies = find_strategies_by_tags(["basic", "special"])
    assert len(multi_tag_strategies) == 2
    assert sample_strategies[0] in multi_tag_strategies
    assert sample_strategies[2] in multi_tag_strategies

    # Find strategies with a non-existent tag
    non_existent_strategies = find_strategies_by_tags(["non-existent"])
    assert len(non_existent_strategies) == 0


def test_get_all_strategies(sample_strategies):
    """Test retrieving all registered strategies."""
    # Initially, there should be no strategies
    assert len(get_all_strategies()) == 0

    # Register all sample strategies
    for strategy in sample_strategies:
        register_prompt_strategy(strategy)

    # Get all strategies
    all_strategies = get_all_strategies()
    assert len(all_strategies) == 3

    # Check all strategies are in the list
    for strategy in sample_strategies:
        assert strategy in all_strategies


def test_clear_registry(sample_strategies):
    """Test clearing the registry."""
    # Register all sample strategies
    for strategy in sample_strategies:
        register_prompt_strategy(strategy)

    # Verify they're in the registry
    assert len(get_all_strategies()) == 3

    # Clear the registry
    clear_registry()

    # Verify the registry is empty
    assert len(get_all_strategies()) == 0
    assert len(_STRATEGY_REGISTRY) == 0
