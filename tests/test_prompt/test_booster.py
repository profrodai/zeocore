# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_prompt/test_booster.py
# role: tests
# neighbors: __init__.py, conftest.py, test_enhancer.py, test_integration.py, test_plugin.py, test_registry.py (+2 more)
# exports: sample_strategy, setup_teardown, test_booster_initialization, test_booster_select_strategy, test_booster_select_strategy_by_tags, test_booster_select_strategy_with_schema_examples, test_booster_render, test_booster_render_with_llm (+9 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
Tests for the PromptBooster class.
"""

# Fixed test_enhancer.py imports
from unittest.mock import MagicMock, patch

import pytest
from quack_core.prompt.booster import PromptBooster
from quack_core.prompt.registry import clear_registry, register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


@pytest.fixture
def sample_strategy():
    """Create a sample strategy for testing."""

    def render_fn(task_description: str, schema: str | None = None) -> str:
        result = f"Task: {task_description}"
        if schema:
            result += f"\nSchema: {schema}"
        return result

    strategy = PromptStrategy(
        id="test-strategy",
        label="Test Strategy",
        description="A strategy for testing",
        input_vars=["task_description", "schema"],
        render_fn=render_fn,
        tags=["test"],
    )

    return strategy


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test."""
    # Clear registry at the start and register our test strategy
    clear_registry()
    yield
    clear_registry()


def test_booster_initialization():
    """Test initializing a PromptBooster."""
    # Create a booster with minimal arguments
    booster = PromptBooster(raw_prompt="Create a list of fruits")

    assert booster.raw_prompt == "Create a list of fruits"
    assert booster.schema is None
    assert booster.examples is None
    assert booster.tags == []
    assert booster.strategy_id is None
    assert booster.strategy is None
    assert booster.optimized_prompt is None

    # Create a booster with all arguments
    booster_full = PromptBooster(
        raw_prompt="Extract company information",
        schema='{"name": "string", "founded": "string"}',
        examples=["Example 1", "Example 2"],
        tags=["structured", "extraction"],
        strategy_id="multi-shot-structured",
    )

    assert booster_full.raw_prompt == "Extract company information"
    assert booster_full.schema == '{"name": "string", "founded": "string"}'
    assert booster_full.examples == ["Example 1", "Example 2"]
    assert booster_full.tags == ["structured", "extraction"]
    assert booster_full.strategy_id == "multi-shot-structured"


def test_booster_select_strategy(sample_strategy):
    """Test strategy selection in PromptBooster."""
    # Register our sample strategy
    register_prompt_strategy(sample_strategy)

    # Create a booster without specifying a strategy
    booster = PromptBooster(raw_prompt="Test prompt")

    # Select the strategy
    selected = booster.select_strategy("test-strategy")

    # Check the selected strategy
    assert selected == sample_strategy
    assert booster.strategy == sample_strategy
    assert booster.strategy_id == "test-strategy"


def test_booster_select_strategy_by_tags(sample_strategy):
    """Test selecting a strategy by tags."""
    # Register our sample strategy
    register_prompt_strategy(sample_strategy)

    # Create a booster with matching tags
    booster = PromptBooster(raw_prompt="Test prompt", tags=["test"])

    # Select strategy without specifying ID
    selected = booster.select_strategy()

    # Check the selected strategy
    assert selected == sample_strategy
    assert booster.strategy == sample_strategy
    assert booster.strategy_id == "test-strategy"


def test_booster_select_strategy_with_schema_examples():
    """Test strategy selection based on schema and examples."""

    # Register some strategies
    def render_fn(
        task_description: str,
        schema: str | None = None,
        examples: list[str] | None = None,
    ) -> str:
        return "Test strategy"

    multi_shot = PromptStrategy(
        id="multi-shot-structured",
        label="Multi-shot Structured",
        description="Multi-shot strategy",
        input_vars=["task_description", "schema", "examples"],
        render_fn=render_fn,
    )

    single_shot = PromptStrategy(
        id="single-shot-structured",
        label="Single-shot Structured",
        description="Single-shot strategy",
        input_vars=["task_description", "schema", "example"],
        render_fn=render_fn,
    )

    register_prompt_strategy(multi_shot)
    register_prompt_strategy(single_shot)

    # Test multi-shot selection (schema + multiple examples)
    booster1 = PromptBooster(
        raw_prompt="Extract entities",
        schema='{"entities": []}',
        examples=["Example 1", "Example 2"],
    )

    selected1 = booster1.select_strategy()
    assert selected1.id == "multi-shot-structured"

    # Test single-shot selection (schema + single example)
    booster2 = PromptBooster(
        raw_prompt="Extract entities",
        schema='{"entities": []}',
        examples="Single example",
    )

    selected2 = booster2.select_strategy()
    assert selected2.id == "single-shot-structured"


def test_booster_render(sample_strategy):
    """Test rendering a prompt with the PromptBooster."""
    # Register our sample strategy
    register_prompt_strategy(sample_strategy)

    # Create a booster
    booster = PromptBooster(
        raw_prompt="Generate a story",
        schema='{"title": "string", "content": "string"}',
        strategy_id="test-strategy",
    )

    # Render the prompt
    rendered = booster.render()

    # Check the rendered prompt
    assert (
        rendered
        == 'Task: Generate a story\nSchema: {"title": "string", "content": "string"}'
    )
    assert booster.optimized_prompt == rendered


def test_booster_render_with_llm():
    """Test rendering a prompt with LLM enhancement."""
    # Create mock strategy
    mock_strategy = MagicMock()
    mock_strategy.id = "test-strategy"
    mock_strategy.input_vars = ["task_description"]
    mock_strategy.render_fn = (
        lambda task_description, **kwargs: f"Basic: {task_description}"
    )

    # Create a booster with this strategy already set
    booster = PromptBooster(raw_prompt="Generate a story about AI")
    booster.strategy = mock_strategy
    booster.strategy_id = "test-strategy"

    # Create a mock for enhance_with_llm
    with patch("quack_core.prompt.enhancer.enhance_with_llm") as mock_enhance:
        # Configure the mock
        mock_enhance.return_value = "Enhanced: Generate a story about AI"

        # Render with LLM enhancement
        rendered = booster.render(use_llm=True)

        # Check the rendered prompt
        assert rendered == "Enhanced: Generate a story about AI"
        assert booster.optimized_prompt == rendered

        # Verify the enhancer was called correctly
        mock_enhance.assert_called_once_with(
            task_description="Generate a story about AI",
            schema=None,
            examples=None,
            strategy_name="test-strategy",
            model=None,
            provider=None,
        )


def test_booster_render_llm_failure(sample_strategy):
    """Test fallback when LLM enhancement fails."""
    # Register our sample strategy
    register_prompt_strategy(sample_strategy)

    # Create a booster
    booster = PromptBooster(raw_prompt="Generate a story", strategy_id="test-strategy")

    # Mock the enhancer to raise an exception
    with patch(
        "quack_core.prompt.enhancer.enhance_with_llm",
        side_effect=ImportError("Test error"),
    ):
        # Render with LLM enhancement
        rendered = booster.render(use_llm=True)

        # Check that we fell back to the strategy-based rendering
        assert rendered == "Task: Generate a story"
        assert booster.optimized_prompt == rendered


def test_booster_metadata(sample_strategy):
    """Test getting metadata from the PromptBooster."""
    # Register our sample strategy
    register_prompt_strategy(sample_strategy)

    # Create a booster
    booster = PromptBooster(
        raw_prompt="Extract information",
        schema='{"info": "string"}',
        examples=["Example"],
        tags=["extraction"],
        strategy_id="test-strategy",
    )

    # Render to set optimized_prompt
    booster.render()

    # Get metadata
    metadata = booster.metadata()

    # Check metadata
    assert metadata["raw_prompt"] == "Extract information"
    assert metadata["has_schema"] is True
    assert metadata["has_examples"] is True
    assert metadata["tags"] == ["extraction"]
    assert "strategy" in metadata
    assert metadata["strategy"]["id"] == "test-strategy"
    assert metadata["strategy"]["label"] == "Test Strategy"
    assert "optimized_prompt_length" in metadata


def test_booster_metadata_with_token_count():
    """Test metadata with token count estimation."""
    # Create a mock token count function
    with (
        patch("quack_core.prompt.booster.PromptBooster.select_strategy") as mock_select,
        patch(
            "quack_core.prompt.booster.PromptBooster.estimate_token_count"
        ) as mock_count,
    ):
        # Configure the mocks
        mock_select.return_value = MagicMock(id="test-strategy")
        mock_count.return_value = 42

        # Create a booster
        booster = PromptBooster(raw_prompt="Test prompt")

        # Get metadata
        metadata = booster.metadata()

        # Check token count in metadata
        assert "estimated_token_count" in metadata
        assert metadata["estimated_token_count"] == 42


def test_booster_explain(sample_strategy):
    """Test getting an explanation of the selected strategy."""
    # Register our sample strategy
    register_prompt_strategy(sample_strategy)

    # Create a booster
    booster = PromptBooster(raw_prompt="Test prompt", strategy_id="test-strategy")

    # Get explanation
    explanation = booster.explain()

    # Check explanation
    assert "Test Strategy" in explanation
    assert "A strategy for testing" in explanation
    assert "Tags: test" in explanation
    assert "Origin: unknown" in explanation


def test_booster_explain_no_strategy():
    """Test explanation when no strategy is selected."""
    # Create a booster
    booster = PromptBooster(raw_prompt="Test prompt")

    # Get explanation before selecting a strategy
    explanation = booster.explain()

    # Check explanation
    assert explanation == "No strategy selected."


def test_booster_export(sample_strategy, tmp_path):
    """Test exporting a prompt to a file."""
    # Register our sample strategy
    register_prompt_strategy(sample_strategy)

    # Create a booster
    booster = PromptBooster(raw_prompt="Export test", strategy_id="test-strategy")

    # Render to set optimized_prompt
    booster.render()

    # Define export paths
    json_path = str(tmp_path / "export.json")
    text_path = str(tmp_path / "export.txt")

    # Mock the standalone functions to return success
    with patch("quack_core.prompt.booster.standalone") as mock_standalone:
        # Configure the split_path mock
        mock_standalone.split_path.return_value = MagicMock(
            success=True,
            data=[str(tmp_path), "export.json"]
        )

        # Configure the join_path mock
        mock_standalone.join_path.return_value = MagicMock(
            success=True,
            data=str(tmp_path)
        )

        # Configure the write_json mock
        mock_standalone.write_json.return_value = MagicMock(success=True)

        # Configure the create_directory mock
        mock_standalone.create_directory.return_value = MagicMock(success=True)

        # Export to JSON and check
        booster.export(json_path)

        # Verify mocks were called correctly
        mock_standalone.split_path.assert_called_with(json_path)
        mock_standalone.join_path.assert_called()
        mock_standalone.create_directory.assert_called()
        mock_standalone.write_json.assert_called_with(json_path, {
            "prompt": "Task: Export test",
            "metadata": booster.metadata(),
            "explanation": booster.explain(),
        }, indent=2)


def test_booster_export_fallback(sample_strategy, tmp_path):
    """Test exporting a prompt with fallback JSON formatting."""
    # Register our sample strategy
    register_prompt_strategy(sample_strategy)

    # Create a booster
    booster = PromptBooster(raw_prompt="Export test", strategy_id="test-strategy")

    # Render to set optimized_prompt
    booster.render()

    # Define export path
    text_path = str(tmp_path / "export.txt")

    # Mock the standalone functions
    with patch("quack_core.prompt.booster.standalone") as mock_standalone:
        # Configure the split_path mock
        mock_standalone.split_path.return_value = MagicMock(
            success=True,
            data=[str(tmp_path), "export.txt"]
        )

        # Configure the join_path mock
        mock_standalone.join_path.return_value = MagicMock(
            success=True,
            data=str(tmp_path)
        )

        # Configure the create_directory mock
        mock_standalone.create_directory.return_value = MagicMock(success=True)

        # Configure the write_text mock
        mock_standalone.write_text.return_value = MagicMock(success=True)

        # Configure the write_json mock to fail, which will trigger the fallback
        mock_standalone.write_json.return_value = MagicMock(success=False,
                                                            error="Test error")

        # Mock tempfile to force an exception in the try block
        with patch("tempfile.NamedTemporaryFile", side_effect=Exception("Test error")):
            # Now mock json.dumps for the fallback path
            with patch("json.dumps") as mock_dumps:
                mock_dumps.return_value = '{"mock": "json"}'

                # Export using the fallback
                booster.export(text_path)

                # Verify json.dumps was called
                mock_dumps.assert_called_once()

def test_booster_estimate_token_count():
    """Test token count estimation."""
    # Create a mock token count function
    with patch("quack_core.prompt.enhancer.count_prompt_tokens") as mock_count:
        # Configure the mock
        mock_count.return_value = 123

        # Create a booster
        booster = PromptBooster(
            raw_prompt="Count tokens test",
            schema='{"test": "schema"}',
            examples=["Example 1", "Example 2"],
            strategy_id="test-strategy",
        )

        # Set a mock strategy
        booster.strategy = MagicMock(id="test-strategy")

        # Estimate token count
        count = booster.estimate_token_count()

        # Check count
        assert count == 123

        # Verify mock was called correctly
        mock_count.assert_called_once_with(
            task_description="Count tokens test",
            schema='{"test": "schema"}',
            examples=["Example 1", "Example 2"],
            strategy_name="test-strategy",
        )


def test_booster_estimate_token_count_error():
    """Test token count estimation when an error occurs."""
    # Create a mock token count function that raises an exception
    with patch(
        "quack_core.prompt.enhancer.count_prompt_tokens",
        side_effect=ImportError("Test error"),
    ):
        # Create a booster
        booster = PromptBooster(raw_prompt="Count tokens test")

        # Estimate token count
        count = booster.estimate_token_count()

        # Check that None is returned on error
        assert count is None
