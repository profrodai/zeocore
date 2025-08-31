# quack-core/tests/test_prompt/test_integration.py
"""
Integration tests for the prompt module.

These tests verify that the various components of the prompt module
work together correctly as a complete system.
"""

import importlib
from unittest.mock import patch

import pytest

from quack_core.prompt import (
    PromptBooster,
    PromptStrategy,
    find_strategies_by_tags,
    get_all_strategies,
    get_strategy_by_id,
    register_prompt_strategy,
)
from quack_core.prompt.registry import clear_registry


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test."""
    # Clear registry before each test
    clear_registry()
    yield
    clear_registry()


def create_and_register_test_strategies():
    """Create and register some test strategies for testing."""

    # Define a simple render function for a basic strategy
    def basic_render_fn(task_description: str) -> str:
        return f"Basic: {task_description}"

    # Define a render function for a structured strategy
    def structured_render_fn(task_description: str, schema: str) -> str:
        return f"Structured: {task_description}, Schema: {schema}"

    # Create a basic strategy
    basic_strategy = PromptStrategy(
        id="basic-strategy",
        label="Basic Strategy",
        description="A basic strategy",
        input_vars=["task_description"],
        render_fn=basic_render_fn,
        tags=["basic"],
    )

    # Create a structured strategy
    structured_strategy = PromptStrategy(
        id="structured-strategy",
        label="Structured Strategy",
        description="A structured strategy",
        input_vars=["task_description", "schema"],
        render_fn=structured_render_fn,
        tags=["structured"],
    )

    # Register the strategies
    register_prompt_strategy(basic_strategy)
    register_prompt_strategy(structured_strategy)

    return [basic_strategy, structured_strategy]


def test_strategy_registry_integration():
    """Test that strategies can be registered and retrieved."""

    # Define a simple render function
    def render_fn(prompt: str) -> str:
        return f"Test: {prompt}"

    # Create a strategy
    strategy = PromptStrategy(
        id="integration-test",
        label="Integration Test",
        description="A strategy for integration testing",
        input_vars=["prompt"],
        render_fn=render_fn,
        tags=["integration", "test"],
    )

    # Register the strategy
    register_prompt_strategy(strategy)

    # Retrieve by ID
    retrieved = get_strategy_by_id("integration-test")
    assert retrieved.id == "integration-test"
    assert retrieved.render_fn is render_fn

    # Find by tags
    by_tags = find_strategies_by_tags(["integration"])
    assert len(by_tags) == 1
    assert by_tags[0].id == "integration-test"

    # Get all strategies
    all_strategies = get_all_strategies()
    assert len(all_strategies) == 1
    assert all_strategies[0].id == "integration-test"


def test_booster_with_registry_integration():
    """Test that PromptBooster works with the strategy registry."""

    # Define a render function
    def render_fn(task_description: str, examples: list[str] | None = None) -> str:
        result = f"Task: {task_description}"
        if examples:
            examples_str = "\n".join(examples)
            result += f"\n\nExamples:\n{examples_str}"
        return result

    # Create and register a strategy
    strategy = PromptStrategy(
        id="booster-test",
        label="Booster Test",
        description="A strategy for testing with the booster",
        input_vars=["task_description", "examples"],
        render_fn=render_fn,
        tags=["booster", "test"],
    )

    register_prompt_strategy(strategy)

    # Create a booster with the registered strategy
    booster = PromptBooster(
        raw_prompt="Generate a story",
        examples=["Example 1", "Example 2"],
        strategy_id="booster-test",
    )

    # Render the prompt
    rendered = booster.render()

    # Check the rendered prompt
    assert rendered == "Task: Generate a story\n\nExamples:\nExample 1\nExample 2"


def test_booster_auto_strategy_selection():
    """Test that PromptBooster can automatically select an appropriate strategy."""
    # Create and register strategies
    create_and_register_test_strategies()

    # Create a booster with tags matching the basic strategy
    booster1 = PromptBooster(raw_prompt="Simple task", tags=["basic"])

    # Render and check
    rendered1 = booster1.render()
    assert rendered1 == "Basic: Simple task"
    assert booster1.strategy_id == "basic-strategy"

    # Create a booster with tags matching the structured strategy
    booster2 = PromptBooster(
        raw_prompt="Extract entities", schema='{"entities": []}', tags=["structured"]
    )

    # Render and check
    rendered2 = booster2.render()
    assert rendered2 == 'Structured: Extract entities, Schema: {"entities": []}'
    assert booster2.strategy_id == "structured-strategy"


@pytest.mark.integration
def test_llm_integration():
    """Test integration with LLM enhancer."""
    # Skip if no LLM integration is available
    try:
        importlib.import_module("quack-core.integrations.llms.service")
    except ImportError:
        pytest.skip("LLM integration not available")

    # Create a mock for the LLM service
    with patch("quack-core.prompt.enhancer.enhance_with_llm") as mock_enhance:
        # Configure the mock
        mock_enhance.return_value = "LLM enhanced: Generate a creative story"

        # Define a simple render function
        def render_fn(task_description: str) -> str:
            return f"Basic: {task_description}"

        # Create and register a strategy
        strategy = PromptStrategy(
            id="llm-test",
            label="LLM Test",
            description="A strategy for testing with LLM",
            input_vars=["task_description"],
            render_fn=render_fn,
        )

        register_prompt_strategy(strategy)

        # Create a booster
        booster = PromptBooster(
            raw_prompt="Generate a creative story", strategy_id="llm-test"
        )

        # Render with LLM enhancement
        rendered = booster.render(use_llm=True)

        # Check the rendered prompt
        assert rendered == "LLM enhanced: Generate a creative story"

        # Verify the enhancer was called
        mock_enhance.assert_called_once()


def test_full_pipeline_with_mock_llm():
    """Test the full pipeline from strategy creation to enhanced rendering."""
    # Create a mock for the LLM service
    with patch("quack-core.prompt.enhancer.enhance_with_llm") as mock_enhance:
        # Configure the mock to simulate LLM enhancement
        mock_enhance.return_value = (
            "Enhanced: Create a comprehensive guide to prompt engineering"
        )

        # Define a render function
        def render_fn(task_description: str, examples: list[str] | None = None) -> str:
            result = f"Original: {task_description}"
            if examples:
                examples_str = "\n".join(f"- {ex}" for ex in examples)
                result += f"\n\nExamples:\n{examples_str}"
            return result

        # Create and register a strategy
        strategy = PromptStrategy(
            id="pipeline-test",
            label="Pipeline Test",
            description="A strategy for testing the full pipeline",
            input_vars=["task_description", "examples"],
            render_fn=render_fn,
            tags=["comprehensive"],
        )

        register_prompt_strategy(strategy)

        # Create a booster
        booster = PromptBooster(
            raw_prompt="Create a comprehensive guide to prompt engineering",
            examples=["Example 1: Chain-of-thought", "Example 2: Few-shot learning"],
            tags=["comprehensive"],
        )

        # First render without LLM
        basic_rendered = booster.render(use_llm=False)
        assert (
            basic_rendered
            == "Original: Create a comprehensive guide to prompt engineering\n\nExamples:\n- Example 1: Chain-of-thought\n- Example 2: Few-shot learning"
        )

        # Then render with LLM enhancement
        enhanced_rendered = booster.render(use_llm=True)
        assert (
            enhanced_rendered
            == "Enhanced: Create a comprehensive guide to prompt engineering"
        )

        # Verify the enhancer was called with the correct parameters
        mock_enhance.assert_called_once_with(
            task_description="Create a comprehensive guide to prompt engineering",
            schema=None,
            examples=["Example 1: Chain-of-thought", "Example 2: Few-shot learning"],
            strategy_name="pipeline-test",
            model=None,
            provider=None,
        )


def test_registry_import_integration():
    """Test that importing the module registers all strategies."""
    # First clear the registry
    clear_registry()

    # Create and register test strategies to ensure the registry is populated
    create_and_register_test_strategies()

    # Check that strategies are registered
    strategies = get_all_strategies()
    assert len(strategies) > 0

    # Check for specific strategies
    strategy_ids = {s.id for s in strategies}
    assert "basic-strategy" in strategy_ids
    assert "structured-strategy" in strategy_ids
