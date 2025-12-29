# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_prompt/conftest.py
# role: tests
# neighbors: __init__.py, test_booster.py, test_enhancer.py, test_integration.py, test_plugin.py, test_registry.py (+2 more)
# exports: mock_render_fn, basic_strategy, registered_strategy, prompt_output_dir, mock_llm_integration, complex_render_fn, complex_strategy
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""
Fixtures for prompt module tests.
"""

from typing import Any

import pytest

from quack_core.prompt.registry import clear_registry, register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


@pytest.fixture
def mock_render_fn():
    """Create a simple render function for testing."""

    def render_fn(
        task_description: str,
        schema: str | None = None,
        examples: list[str] | None = None,
    ) -> str:
        result = f"Task: {task_description}"
        if schema:
            result += f"\nSchema: {schema}"
        if examples:
            examples_str = "\n".join(f"- {ex}" for ex in examples)
            result += f"\nExamples:\n{examples_str}"
        return result

    return render_fn


@pytest.fixture
def basic_strategy(mock_render_fn):
    """Create a basic strategy for testing."""
    strategy = PromptStrategy(
        id="test-basic-strategy",
        label="Test Basic Strategy",
        description="A basic strategy for testing",
        input_vars=["task_description", "schema", "examples"],
        render_fn=mock_render_fn,
        tags=["test", "basic"],
    )

    return strategy


@pytest.fixture
def registered_strategy(basic_strategy):
    """Create and register a strategy for testing."""
    # Clear registry and register the strategy
    clear_registry()
    register_prompt_strategy(basic_strategy)

    yield basic_strategy

    # Clear registry after test
    clear_registry()


@pytest.fixture
def prompt_output_dir(tmp_path):
    """Create a directory for prompt export tests."""
    output_dir = tmp_path / "prompt_outputs"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_llm_integration():
    """Create a mock LLM integration for testing."""

    class MockResult:
        def __init__(
            self, success: bool, content: Any = None, error: str | None = None
        ):
            self.success = success
            self.content = content
            self.error = error

    class MockLLMIntegration:
        def initialize(self):
            return MockResult(success=True)

        def chat(self, messages, options=None):
            return MockResult(success=True, content="Enhanced by mock LLM")

        def count_tokens(self, messages):
            return MockResult(success=True, content=100)

    return MockLLMIntegration()


@pytest.fixture
def complex_render_fn():
    """Create a more complex render function for testing."""

    def render_fn(
        task_description: str,
        tools: list[dict] | None = None,
        final_instruction: str | None = None,
    ) -> str:
        result = f"Complex task: {task_description}"

        if tools:
            result += "\n\nAvailable tools:"
            for tool in tools:
                result += f"\n- {tool.get('name', 'Unnamed')}: {tool.get('description', 'No description')}"

        if final_instruction:
            result += f"\n\nFinal instruction: {final_instruction}"

        return result

    return render_fn


@pytest.fixture
def complex_strategy(complex_render_fn):
    """Create a more complex strategy for testing."""
    strategy = PromptStrategy(
        id="test-complex-strategy",
        label="Test Complex Strategy",
        description="A complex strategy for testing",
        input_vars=["task_description", "tools", "final_instruction"],
        render_fn=complex_render_fn,
        tags=["test", "complex", "tools"],
        origin="Test suite",
    )

    return strategy
