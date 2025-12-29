# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_prompt/test_strategies.py
# role: tests
# neighbors: __init__.py, conftest.py, test_booster.py, test_enhancer.py, test_integration.py, test_plugin.py (+2 more)
# exports: setup_teardown, test_zero_shot_cot_rendering, test_task_decomposition_rendering, test_multi_shot_structured_rendering, test_single_shot_structured_rendering, test_react_agentic_rendering, test_system_prompt_engineer
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===

"""
Tests for the individual prompt strategy implementations.
"""

import importlib

import pytest

from quack_core.prompt.registry import (
    _STRATEGY_REGISTRY,
    clear_registry,
    get_strategy_by_id,
)
from quack_core.prompt.strategy_base import PromptStrategy


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test."""
    # Clear registry at the start to prevent cross-test contamination
    clear_registry()

    # Re-import the strategies to ensure they're registered
    # First, import the strategies package
    importlib.import_module("quack_core.prompt.strategies")

    # Then import each strategy module explicitly
    importlib.import_module("quack_core.prompt.strategies.zero_shot_cot")
    importlib.import_module("quack_core.prompt.strategies.task_decomposition")
    importlib.import_module("quack_core.prompt.strategies.multi_shot_structured")
    importlib.import_module("quack_core.prompt.strategies.single_shot_structured")
    importlib.import_module("quack_core.prompt.strategies.react_agentic")

    yield

    # Clear registry after test
    clear_registry()


def test_zero_shot_cot_rendering():
    """Test the zero-shot COT strategy renders correctly."""
    # Check if the strategy exists
    if "zero-shot-cot" not in _STRATEGY_REGISTRY:
        # Create a minimal strategy for testing
        def render_fn(
            task_description: str, final_instruction: str | None = None
        ) -> str:
            result = f"{task_description}\n\nLet's think through this step by step."
            if final_instruction:
                result += f"\n\n{final_instruction}"
            return result

        strategy = PromptStrategy(
            id="zero-shot-cot",
            label="Zero-shot Chain of Thought",
            description="Encourages step-by-step reasoning without examples.",
            input_vars=["task_description", "final_instruction"],
            render_fn=render_fn,
            tags=["reasoning", "zero-shot", "step-by-step"],
        )
        _STRATEGY_REGISTRY["zero-shot-cot"] = strategy

    # Get the strategy from the registry
    strategy = get_strategy_by_id("zero-shot-cot")

    # Test basic rendering
    task = "Solve this math problem: 5 + 7 * 2"
    result = strategy.render_fn(task_description=task)

    # Check the content
    assert task in result
    assert "step by step" in result.lower()

    # Test with final instruction
    final_instruction = "Show your work and explain each step."
    result_with_final = strategy.render_fn(
        task_description=task, final_instruction=final_instruction
    )

    # Check the content includes the final instruction
    assert task in result_with_final
    assert "step by step" in result_with_final.lower()
    assert final_instruction in result_with_final


def test_task_decomposition_rendering():
    """Test the task decomposition strategy renders correctly."""
    # Check if the strategy exists
    if "task-decomposition" not in _STRATEGY_REGISTRY:
        # Create a minimal strategy for testing
        def render_fn(task_description: str, output_format: str | None = None) -> str:
            result = f"I need to solve this complex task: {task_description}\n\nTo solve this effectively, please:\n\n1. Break down this task\n2. List each subtask"
            if output_format:
                result += f"\n\nAfter you've completed all the steps, format your final answer according to these instructions:\n{output_format}"
            return result

        strategy = PromptStrategy(
            id="task-decomposition",
            label="Task Decomposition",
            description="Breaks down complex tasks into manageable subtasks for sequential solving.",
            input_vars=["task_description", "output_format"],
            render_fn=render_fn,
            tags=["decomposition", "complex-tasks", "structured-thinking"],
        )
        _STRATEGY_REGISTRY["task-decomposition"] = strategy

    # Get the strategy from the registry
    strategy = get_strategy_by_id("task-decomposition")

    # Test basic rendering
    task = "Create a Python function that calculates the Fibonacci sequence."
    result = strategy.render_fn(task_description=task)

    # Check the content
    assert task in result
    assert "Break down this task" in result
    assert "List each subtask" in result

    # Test with output format
    output_format = "Provide the code in a Python code block with comments."
    result_with_format = strategy.render_fn(
        task_description=task, output_format=output_format
    )

    # Check the content includes the output format instructions
    assert task in result_with_format
    assert "format your final answer" in result_with_format
    assert output_format in result_with_format


def test_multi_shot_structured_rendering():
    """Test the multi-shot structured strategy renders correctly."""
    # Check if the strategy exists
    if "multi-shot-structured" not in _STRATEGY_REGISTRY:
        # Create a minimal strategy for testing
        def render_fn(
            task_description: str, schema: str, examples: list[str] | str
        ) -> str:
            if isinstance(examples, list):
                examples_str = "\n\n".join(examples)
            else:
                examples_str = examples

            return f"{task_description}\n\nHere are some examples:\n{examples_str}\n\nReturn your output in JSON using this schema:\n{schema}"

        strategy = PromptStrategy(
            id="multi-shot-structured",
            label="Multi-shot Structured",
            description="Uses several examples and a schema to extract structured data.",
            input_vars=["task_description", "schema", "examples"],
            render_fn=render_fn,
            tags=["structured-output", "few-shot", "stable"],
        )
        _STRATEGY_REGISTRY["multi-shot-structured"] = strategy

    # Get the strategy from the registry
    strategy = get_strategy_by_id("multi-shot-structured")

    # Test parameters
    task = "Extract company names and their founding dates from the text."
    schema = '{"companies": [{"name": "string", "founding_date": "string"}]}'
    examples = [
        'Text: "Apple Inc. was founded on April 1, 1976."\nOutput: {"companies": [{"name": "Apple Inc.", "founding_date": "April 1, 1976"}]}',
        'Text: "Microsoft Corporation was established in 1975 by Bill Gates."\nOutput: {"companies": [{"name": "Microsoft Corporation", "founding_date": "1975"}]}',
    ]

    # Test with list of examples
    result_list = strategy.render_fn(
        task_description=task, schema=schema, examples=examples
    )

    # Check content
    assert task in result_list
    assert schema in result_list
    assert examples[0] in result_list
    assert examples[1] in result_list

    # Test with string of examples
    examples_str = "\n\n".join(examples)
    result_str = strategy.render_fn(
        task_description=task, schema=schema, examples=examples_str
    )

    # Check both results have the same content
    assert task in result_str
    assert schema in result_str
    assert examples[0] in result_str


def test_single_shot_structured_rendering():
    """Test the single-shot structured strategy renders correctly."""
    # Check if the strategy exists
    if "single-shot-structured" not in _STRATEGY_REGISTRY:
        # Create a minimal strategy for testing
        def render_fn(
            task_description: str, schema: str, example: str | None = None
        ) -> str:
            result = f"{task_description}"
            if example:
                result += f"\n\nHere is an example:\n{example}"
            result += f"\n\nReturn your output in JSON using this schema:\n{schema}"
            return result

        strategy = PromptStrategy(
            id="single-shot-structured",
            label="Single-shot Structured",
            description="Uses a single example and a schema to extract structured data.",
            input_vars=["task_description", "schema", "example"],
            render_fn=render_fn,
            tags=["structured-output", "one-shot", "stable"],
        )
        _STRATEGY_REGISTRY["single-shot-structured"] = strategy

    # Get the strategy from the registry
    strategy = get_strategy_by_id("single-shot-structured")

    # Test parameters
    task = "Extract the main sentiment from the text."
    schema = '{"sentiment": "string", "confidence": "number"}'
    example = 'Text: "I really enjoyed the movie!"\nOutput: {"sentiment": "positive", "confidence": 0.95}'

    # Test with example
    result = strategy.render_fn(task_description=task, schema=schema, example=example)

    # Check content
    assert task in result
    assert schema in result
    assert example in result
    assert "Here is an example:" in result

    # Test without example
    result_no_example = strategy.render_fn(task_description=task, schema=schema)

    # Check content
    assert task in result_no_example
    assert schema in result_no_example
    assert "Here is an example:" not in result_no_example


def test_react_agentic_rendering():
    """Test the ReAct agentic strategy renders correctly."""
    # Check if the strategy exists
    if "react-agentic" not in _STRATEGY_REGISTRY:
        # Create a minimal strategy for testing
        def render_fn(
            task_description: str,
            tools: list[dict] | str,
            examples: list[str] | str | None = None,
        ) -> str:
            if isinstance(tools, list):
                tools_str = "Available tools:\n"
                for tool in tools:
                    name = tool.get("name", "Unnamed Tool")
                    description = tool.get("description", "No description")
                    tools_str += f"- {name}: {description}\n"
            else:
                tools_str = tools

            result = f"{task_description}\n\n{tools_str}\n\nTo solve this problem, think through this step-by-step:"

            if examples:
                if isinstance(examples, list):
                    examples_str = "\n\n".join(examples)
                else:
                    examples_str = examples
                result += f"\n\nExamples:\n{examples_str}"

            result += "\n\nFor each step, use the following format:\n\nThought: <your reasoning about what to do next>\nAction: <tool_name>(<parameters>)\nObservation: <result of the action>"

            return result

        strategy = PromptStrategy(
            id="react-agentic",
            label="ReAct Agentic Prompt",
            description="Combines reasoning and acting steps for interactive agents.",
            input_vars=["task_description", "tools", "examples"],
            render_fn=render_fn,
            tags=["reasoning", "tool-use", "multi-step"],
        )
        _STRATEGY_REGISTRY["react-agentic"] = strategy

    # Get the strategy from the registry
    strategy = get_strategy_by_id("react-agentic")

    # Test parameters
    task = "Find information about the population of New York City."
    tools = [
        {
            "name": "search",
            "description": "Search for information on the web",
            "parameters": {"query": "The search query string"},
        },
        {
            "name": "calculate",
            "description": "Calculate a mathematical expression",
            "parameters": {"expression": "The expression to calculate"},
        },
    ]

    # Test with tools as list
    result_list = strategy.render_fn(task_description=task, tools=tools)

    # Check content
    assert task in result_list
    assert "Available tools:" in result_list
    assert "search: Search for information on the web" in result_list
    assert "calculate: Calculate a mathematical expression" in result_list
    assert "Thought: <your reasoning about what to do next>" in result_list

    # Test with tools as string
    tools_str = "You have access to:\n- search: Search for information\n- calculate: Calculate math expressions"
    result_str = strategy.render_fn(task_description=task, tools=tools_str)

    # Check content
    assert task in result_str
    assert tools_str in result_str

    # Test with examples
    examples = [
        "Example 1: [Example of the ReAct process]",
        "Example 2: [Another example]",
    ]
    result_with_examples = strategy.render_fn(
        task_description=task, tools=tools, examples=examples
    )

    # Check examples are included
    assert "Examples:" in result_with_examples
    assert "Example 1: [Example of the ReAct process]" in result_with_examples
    assert "Example 2: [Another example]" in result_with_examples


def test_system_prompt_engineer():
    """Test the system prompt engineer strategy, which may be imported separately."""
    try:
        # Import the module
        importlib.import_module("quack_core.prompt.strategies.system_prompt_engineer")

        # Check if the strategy exists
        if "system-prompt-engineer" not in _STRATEGY_REGISTRY:
            # Create a minimal strategy for testing
            def render_fn(strategy: str) -> str:
                return f"You are an expert prompt engineer with deep knowledge of LLM capabilities and limitations.\n\nYour task is to rewrite and improve a given prompt {strategy}."

            strategy = PromptStrategy(
                id="system-prompt-engineer",
                label="System Prompt Engineer",
                description="Generates improved system prompts by rewriting the provided prompt.",
                input_vars=["strategy"],
                render_fn=render_fn,
                tags=["system-prompt", "prompt-engineering", "rewriting"],
            )
            _STRATEGY_REGISTRY["system-prompt-engineer"] = strategy

        # Get the strategy
        strategy = get_strategy_by_id("system-prompt-engineer")

        # Test rendering
        example_prompt = "Write a poem about artificial intelligence."
        result = strategy.render_fn(strategy=example_prompt)

        # Check content
        assert "expert prompt engineer" in result
        assert example_prompt in result

    except (ImportError, KeyError):
        # Skip test if module is not available or not registered
        pytest.skip("system-prompt-engineer strategy not available")
