# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_prompt/test_plugin.py
# role: tests
# neighbors: __init__.py, conftest.py, test_booster.py, test_enhancer.py, test_integration.py, test_registry.py (+2 more)
# exports: clear_registry_before_after, test_plugin_initialization, test_create_plugin, test_plugin_create_booster, test_plugin_register_strategy, test_plugin_get_strategy, test_plugin_find_strategies, test_plugin_list_strategies (+2 more)
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

"""
Tests for the prompt plugin functionality.
"""

from unittest.mock import MagicMock, patch

import pytest
from quack_core.prompt.plugin import PromptBoosterPlugin, create_plugin
from quack_core.prompt.registry import clear_registry, get_all_strategies
from quack_core.prompt.strategy_base import PromptStrategy


@pytest.fixture(autouse=True)
def clear_registry_before_after():
    """Ensure registry is cleared before and after each test."""
    clear_registry()
    yield
    clear_registry()


def test_plugin_initialization():
    """Test creating a PromptBoosterPlugin."""
    plugin = PromptBoosterPlugin()

    assert plugin.name == "prompt_booster"
    assert plugin.version == "1.0.0"
    assert "prompt" in plugin.description.lower()


def test_create_plugin():
    """Test the create_plugin factory function."""
    plugin = create_plugin()

    assert isinstance(plugin, PromptBoosterPlugin)
    assert plugin.name == "prompt_booster"


def test_plugin_create_booster():
    """Test creating a PromptBooster through the plugin."""
    plugin = PromptBoosterPlugin()

    # Create a booster with the plugin
    booster = plugin.create_booster(
        raw_prompt="Generate a story",
        schema='{"title": "string", "content": "string"}',
        examples=["Example 1", "Example 2"],
        tags=["creative", "structured"],
        strategy_id="test-strategy",
    )

    # Check booster properties
    assert booster.raw_prompt == "Generate a story"
    assert booster.schema == '{"title": "string", "content": "string"}'
    assert booster.examples == ["Example 1", "Example 2"]
    assert booster.tags == ["creative", "structured"]
    assert booster.strategy_id == "test-strategy"


def test_plugin_register_strategy():
    """Test registering a strategy through the plugin."""
    plugin = PromptBoosterPlugin()

    # Define a render function
    def render_fn(task: str) -> str:
        return f"Plugin test: {task}"

    # Register a strategy through the plugin
    strategy = plugin.register_strategy(
        id="plugin-test",
        label="Plugin Test",
        description="Testing plugin registration",
        input_vars=["task"],
        render_fn=render_fn,
        tags=["plugin", "test"],
        origin="Plugin tests",
    )

    # Check strategy properties
    assert strategy.id == "plugin-test"
    assert strategy.label == "Plugin Test"
    assert strategy.input_vars == ["task"]
    assert strategy.render_fn is render_fn
    assert strategy.tags == ["plugin", "test"]
    assert strategy.origin == "Plugin tests"

    # Check it was added to the registry
    all_strategies = get_all_strategies()
    assert len(all_strategies) == 1
    assert all_strategies[0] == strategy


def test_plugin_get_strategy():
    """Test getting a strategy by ID through the plugin."""
    plugin = PromptBoosterPlugin()

    # Register a strategy
    def render_fn(task: str) -> str:
        return f"Task: {task}"

    strategy = PromptStrategy(
        id="test-id",
        label="Test Strategy",
        description="Strategy for testing",
        input_vars=["task"],
        render_fn=render_fn,
    )

    plugin.register_strategy(
        id=strategy.id,
        label=strategy.label,
        description=strategy.description,
        input_vars=strategy.input_vars,
        render_fn=strategy.render_fn,
    )

    # Get the strategy
    retrieved = plugin.get_strategy("test-id")

    # Check properties
    assert retrieved.id == "test-id"
    assert retrieved.label == "Test Strategy"
    assert retrieved.render_fn is render_fn

    # Try to get a non-existent strategy
    with pytest.raises(KeyError):
        plugin.get_strategy("non-existent")


def test_plugin_find_strategies():
    """Test finding strategies by tags through the plugin."""
    plugin = PromptBoosterPlugin()

    # Register some strategies
    def render_fn(task: str) -> str:
        return f"Task: {task}"

    plugin.register_strategy(
        id="strategy1",
        label="Strategy One",
        description="First strategy",
        input_vars=["task"],
        render_fn=render_fn,
        tags=["tag1", "common"],
    )

    plugin.register_strategy(
        id="strategy2",
        label="Strategy Two",
        description="Second strategy",
        input_vars=["task"],
        render_fn=render_fn,
        tags=["tag2", "common"],
    )

    # Find strategies by tag
    tag1_strategies = plugin.find_strategies(["tag1"])
    assert len(tag1_strategies) == 1
    assert tag1_strategies[0].id == "strategy1"

    common_strategies = plugin.find_strategies(["common"])
    assert len(common_strategies) == 2
    assert {s.id for s in common_strategies} == {"strategy1", "strategy2"}

    # Find with non-existent tag
    non_existent = plugin.find_strategies(["non-existent"])
    assert len(non_existent) == 0


def test_plugin_list_strategies():
    """Test listing all strategies through the plugin."""
    plugin = PromptBoosterPlugin()

    # Register some strategies
    def render_fn(task: str) -> str:
        return f"Task: {task}"

    plugin.register_strategy(
        id="strategy1",
        label="Strategy One",
        description="First strategy",
        input_vars=["task"],
        render_fn=render_fn,
        tags=["tag1"],
        origin="Test origin",
    )

    plugin.register_strategy(
        id="strategy2",
        label="Strategy Two",
        description="Second strategy",
        input_vars=["task"],
        render_fn=render_fn,
        tags=["tag2"],
    )

    # List strategies
    strategies = plugin.list_strategies()

    # Check result
    assert len(strategies) == 2

    # Check first strategy
    assert strategies[0]["id"] == "strategy1"
    assert strategies[0]["label"] == "Strategy One"
    assert strategies[0]["description"] == "First strategy"
    assert strategies[0]["tags"] == ["tag1"]
    assert strategies[0]["origin"] == "Test origin"

    # Check second strategy
    assert strategies[1]["id"] == "strategy2"
    assert strategies[1]["label"] == "Strategy Two"
    assert strategies[1]["description"] == "Second strategy"
    assert strategies[1]["tags"] == ["tag2"]
    assert strategies[1]["origin"] is None

    # render_fn should not be included
    assert "render_fn" not in strategies[0]
    assert "render_fn" not in strategies[1]


def test_plugin_enhance_prompt():
    """Test enhancing a prompt through the plugin."""
    with patch("quack_core.prompt.booster.PromptBooster") as MockBooster:
        # Configure the mock
        mock_booster = MagicMock()
        mock_booster.render.return_value = "Enhanced prompt"
        MockBooster.return_value = mock_booster

        # Create plugin
        plugin = PromptBoosterPlugin()

        # Call enhance_prompt
        enhanced = plugin.enhance_prompt(
            booster=mock_booster, model="gpt-4", provider="openai"
        )

        # Check result
        assert enhanced == "Enhanced prompt"

        # Verify the booster's render method was called correctly
        mock_booster.render.assert_called_once_with(
            use_llm=True, model="gpt-4", provider="openai"
        )


def test_plugin_estimate_token_count():
    """Test estimating token count through the plugin."""
    # Configure a mock booster
    mock_booster = MagicMock()
    mock_booster.estimate_token_count.return_value = 125

    # Create plugin
    plugin = PromptBoosterPlugin()

    # Call estimate_token_count
    count = plugin.estimate_token_count(booster=mock_booster)

    # Check result
    assert count == 125

    # Verify the booster's method was called
    mock_booster.estimate_token_count.assert_called_once()
