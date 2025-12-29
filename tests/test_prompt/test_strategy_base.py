# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_prompt/test_strategy_base.py
# role: tests
# neighbors: __init__.py, conftest.py, test_booster.py, test_enhancer.py, test_integration.py, test_plugin.py (+2 more)
# exports: test_prompt_strategy_creation, test_prompt_strategy_rendering, test_prompt_strategy_arbitrary_types, test_prompt_strategy_without_optional_fields
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
Tests for the PromptStrategy base class in strategy_base.py.
"""

from quack_core.prompt.strategy_base import PromptStrategy


def test_prompt_strategy_creation():
    """Test creating a PromptStrategy with valid parameters."""

    # Define a simple render function
    def render_fn(var1: str, var2: str | None = None) -> str:
        if var2:
            return f"{var1} - {var2}"
        return var1

    # Create a strategy
    strategy = PromptStrategy(
        id="test-strategy",
        label="Test Strategy",
        description="A strategy for testing",
        input_vars=["var1", "var2"],
        render_fn=render_fn,
        tags=["test", "simple"],
        origin="Unit tests",
    )

    # Check properties
    assert strategy.id == "test-strategy"
    assert strategy.label == "Test Strategy"
    assert strategy.description == "A strategy for testing"
    assert strategy.input_vars == ["var1", "var2"]
    assert strategy.render_fn is render_fn
    assert strategy.tags == ["test", "simple"]
    assert strategy.origin == "Unit tests"


def test_prompt_strategy_rendering():
    """Test that a PromptStrategy correctly renders a prompt."""

    # Define a simple render function
    def render_fn(prompt: str, examples: list[str] | None = None) -> str:
        result = f"PROMPT: {prompt}"
        if examples:
            examples_str = "\n".join(examples)
            result += f"\n\nEXAMPLES:\n{examples_str}"
        return result

    # Create a strategy
    strategy = PromptStrategy(
        id="render-test",
        label="Render Test",
        description="Tests rendering functionality",
        input_vars=["prompt", "examples"],
        render_fn=render_fn,
    )

    # Test rendering with just a prompt
    result1 = strategy.render_fn(prompt="Hello world")
    assert result1 == "PROMPT: Hello world"

    # Test rendering with examples
    result2 = strategy.render_fn(prompt="List items", examples=["Item 1", "Item 2"])
    assert result2 == "PROMPT: List items\n\nEXAMPLES:\nItem 1\nItem 2"


def test_prompt_strategy_arbitrary_types():
    """Test that PromptStrategy allows arbitrary types like callables."""

    # Define a simple render function
    def render_fn(x: int) -> str:
        return str(x)

    # A more complex function to store
    def complex_fn(a: int, b: int) -> int:
        return a + b

    # Create a strategy with a callable as one of its attributes
    strategy = PromptStrategy(
        id="complex-strategy",
        label="Complex Strategy",
        description="Stores a complex function",
        input_vars=["x"],
        render_fn=render_fn,
        tags=["complex"],
        origin=None,
    )

    # Check that we can access the render_fn
    assert callable(strategy.render_fn)
    assert strategy.render_fn(5) == "5"


def test_prompt_strategy_without_optional_fields():
    """Test creating a PromptStrategy without optional fields."""

    def render_fn(prompt: str) -> str:
        return f"Simple: {prompt}"

    # Create a strategy with only required fields
    strategy = PromptStrategy(
        id="minimal",
        label="Minimal Strategy",
        description="A minimal strategy",
        input_vars=["prompt"],
        render_fn=render_fn,
    )

    assert strategy.tags == []
    assert strategy.origin is None

    # Test rendering works
    assert strategy.render_fn("test") == "Simple: test"
