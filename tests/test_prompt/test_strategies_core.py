"""
Tests for the built-in prompt strategies in zeo_core.prompt.strategies.core.

Each `render_*` function is a pure string-formatting function -- these tests
call the real functions directly with real inputs (no mocking, per RULING-235:
this package has no external SDK/network boundary), and also assert on the
`PromptStrategy` metadata objects and `get_internal_strategies()` collector.
"""

from zeo_core.prompt.models import PromptStrategy
from zeo_core.prompt.strategies import core

# --- Zero Shot ---


def test_render_zero_shot_strips_whitespace() -> None:
    assert core.render_zero_shot("  do the thing  ") == "do the thing"


def test_zero_shot_strategy_metadata() -> None:
    strat = core.zero_shot_strategy
    assert isinstance(strat, PromptStrategy)
    assert strat.id == "zero-shot-prompting"
    assert strat.input_vars == ["task_description"]
    assert strat.render_fn is core.render_zero_shot
    assert strat.priority == 100


# --- Multi-Shot Structured ---


def test_render_multi_shot_structured_with_list_examples() -> None:
    result = core.render_multi_shot_structured(
        "Extract fields", "{type: object}", ["ex1", "ex2"]
    )
    assert "Extract fields" in result
    assert "ex1\n\nex2" in result
    assert "{type: object}" in result


def test_render_multi_shot_structured_with_string_examples() -> None:
    result = core.render_multi_shot_structured(
        "Extract fields", "{type: object}", "single example string"
    )
    assert "single example string" in result
    assert "Extract fields" in result


def test_multi_shot_structured_strategy_metadata() -> None:
    strat = core.multi_shot_structured_strategy
    assert strat.id == "multi-shot-structured"
    assert strat.input_vars == ["task_description", "schema", "examples"]
    assert strat.priority == 50


# --- Single-Shot Structured ---


def test_render_single_shot_structured_with_example() -> None:
    result = core.render_single_shot_structured(
        "Extract fields", "{type: object}", example="ex1"
    )
    assert "Here is an example:\nex1" in result
    assert "{type: object}" in result


def test_render_single_shot_structured_without_example() -> None:
    result = core.render_single_shot_structured("Extract fields", "{type: object}")
    assert "Here is an example" not in result
    assert "Extract fields" in result
    assert "{type: object}" in result


def test_single_shot_structured_strategy_metadata() -> None:
    strat = core.single_shot_structured_strategy
    assert strat.id == "single-shot-structured"
    assert strat.priority == 60


# --- ReAct Agentic ---


def test_render_react_agentic_with_tool_list_and_params() -> None:
    tools = [
        {
            "name": "search",
            "description": "Searches the web",
            "parameters": {"query": "the search query"},
        }
    ]
    result = core.render_react_agentic("Find info", tools, examples=["ex1", "ex2"])
    assert "Available tools:" in result
    assert "- search: Searches the web" in result
    assert "Parameters:" in result
    assert "- query: the search query" in result
    assert "Examples:" in result
    assert "ex1\n\nex2" in result
    assert "Find info" in result


def test_render_react_agentic_tool_missing_name_and_description() -> None:
    tools: list[dict] = [{"parameters": {}}]
    result = core.render_react_agentic("Find info", tools)
    assert "Unnamed Tool" in result
    assert "No description" in result
    # No parameters section since parameters dict is empty
    assert "Parameters:" not in result


def test_render_react_agentic_with_string_tools_and_no_examples() -> None:
    result = core.render_react_agentic("Find info", "tool description string")
    assert "tool description string" in result
    assert "Examples:" not in result


def test_render_react_agentic_with_string_examples() -> None:
    result = core.render_react_agentic("Find info", "tools", examples="a single str")
    assert "Examples:" in result
    assert "a single str" in result


def test_react_agentic_strategy_metadata() -> None:
    strat = core.react_agentic_strategy
    assert strat.id == "react-agentic"
    assert strat.input_vars == ["task_description", "tools", "examples"]


# --- Zero-Shot Chain of Thought ---


def test_render_zero_shot_cot_with_final_instruction() -> None:
    result = core.render_zero_shot_cot("Solve X", final_instruction="Be concise.")
    assert "Let's think through this step by step." in result
    assert "Be concise." in result


def test_render_zero_shot_cot_without_final_instruction() -> None:
    result = core.render_zero_shot_cot("Solve X")
    assert result.endswith("Let's think through this step by step.")


def test_zero_shot_cot_strategy_metadata() -> None:
    assert core.zero_shot_cot_strategy.id == "zero-shot-cot"


# --- Task Decomposition ---


def test_render_task_decomposition_with_output_format() -> None:
    result = core.render_task_decomposition("Build a house", output_format="markdown")
    assert "Build a house" in result
    assert "markdown" in result
    assert "format your final answer" in result


def test_render_task_decomposition_without_output_format() -> None:
    result = core.render_task_decomposition("Build a house")
    assert "Build a house" in result
    assert "format your final answer" not in result


def test_task_decomposition_strategy_metadata() -> None:
    assert core.task_decomposition_strategy.id == "task-decomposition"


# --- Apply Best Practices ---


def test_render_apply_best_practices() -> None:
    result = core.render_apply_best_practices(
        "Original text", ["Be clear", "Be concise"]
    )
    assert "- Be clear" in result
    assert "- Be concise" in result
    assert "Original text" in result


def test_apply_best_practices_strategy_metadata() -> None:
    assert core.apply_best_practices_strategy.id == "apply-best-practices"


# --- Automatic Prompt Engineering ---


def test_render_automatic_prompt_engineering_default_variants() -> None:
    result = core.render_automatic_prompt_engineering("Summarize text")
    assert "Summarize text" in result
    assert "Generate 5 prompt variants" in result


def test_render_automatic_prompt_engineering_custom_variants() -> None:
    result = core.render_automatic_prompt_engineering("Summarize text", num_variants=3)
    assert "Generate 3 prompt variants" in result


def test_automatic_prompt_engineering_strategy_metadata() -> None:
    assert core.automatic_prompt_engineering_strategy.id == (
        "automatic-prompt-engineering"
    )


# --- Chain of Thought Prompting ---


def test_render_chain_of_thought_prompting_with_final_instruction() -> None:
    result = core.render_chain_of_thought_prompting(
        "Solve X", final_instruction="Double check your work."
    )
    assert "Double check your work." in result


def test_render_chain_of_thought_prompting_without_final_instruction() -> None:
    result = core.render_chain_of_thought_prompting("Solve X")
    assert result.endswith("Let's think through this step by step.")


def test_chain_of_thought_prompting_strategy_metadata() -> None:
    assert core.chain_of_thought_prompting_strategy.id == "chain-of-thought-prompting"


# --- Code Prompting ---


def test_render_code_prompting() -> None:
    result = core.render_code_prompting("reverse a string")
    assert "reverse a string" in result
    assert "Write code to accomplish" in result


def test_code_prompting_strategy_metadata() -> None:
    assert core.code_prompting_strategy.id == "code-prompting"


# --- Contextual Prompting ---


def test_render_contextual_prompting() -> None:
    result = core.render_contextual_prompting("some context", "do the task")
    assert "Context: some context" in result
    assert "do the task" in result


def test_contextual_prompting_strategy_metadata() -> None:
    assert core.contextual_prompting_strategy.id == "contextual-prompting"


# --- Debugging Code Prompting ---


def test_render_debugging_code_prompting() -> None:
    result = core.render_debugging_code_prompting("def f(): return 1/0")
    assert "def f(): return 1/0" in result
    assert "debug it" in result


def test_debugging_code_prompting_strategy_metadata() -> None:
    assert core.debugging_code_prompting_strategy.id == "debugging-code-prompting"


# --- Explaining Code Prompting ---


def test_render_explaining_code_prompting() -> None:
    result = core.render_explaining_code_prompting("x = 1 + 1")
    assert "x = 1 + 1" in result
    assert "Explain what the following code does" in result


def test_explaining_code_prompting_strategy_metadata() -> None:
    assert core.explaining_code_prompting_strategy.id == "explaining-code-prompting"


# --- Few-shot Prompting ---


def test_render_few_shot_prompting_with_list() -> None:
    result = core.render_few_shot_prompting("Classify sentiment", ["ex1", "ex2"])
    assert "ex1\n\nex2" in result
    assert "Classify sentiment" in result


def test_render_few_shot_prompting_with_string() -> None:
    result = core.render_few_shot_prompting("Classify sentiment", "just one example")
    assert "just one example" in result


def test_few_shot_prompting_strategy_metadata() -> None:
    assert core.few_shot_prompting_strategy.id == "few-shot-prompting"


# --- JSON Repair Prompting ---


def test_render_json_repair_prompting() -> None:
    result = core.render_json_repair_prompting('{"a": 1,')
    assert '{"a": 1,' in result
    assert "Repair it to valid JSON" in result


def test_json_repair_prompting_strategy_metadata() -> None:
    assert core.json_repair_prompting_strategy.id == "json-repair-prompting"


# --- Multimodal Prompting ---


def test_render_multimodal_prompting() -> None:
    result = core.render_multimodal_prompting("an image and text", "describe them")
    assert "an image and text" in result
    assert "describe them" in result


def test_multimodal_prompting_strategy_metadata() -> None:
    assert core.multimodal_prompting_strategy.id == "multimodal-prompting"


# --- One-shot Prompting ---


def test_render_one_shot_prompting() -> None:
    result = core.render_one_shot_prompting("Translate to French", "Hello -> Bonjour")
    assert "Translate to French" in result
    assert "Hello -> Bonjour" in result


def test_one_shot_prompting_strategy_metadata() -> None:
    assert core.one_shot_prompting_strategy.id == "one-shot-prompting"


# --- ReAct Prompting ---


def test_render_react_prompting_with_tool_list() -> None:
    tools = [{"name": "calc", "description": "does math"}]
    result = core.render_react_prompting("Solve equation", tools, examples=["ex1"])
    assert "Available tools:" in result
    assert "- calc: does math" in result
    assert "Examples:" in result
    assert "ex1" in result


def test_render_react_prompting_with_string_tools_and_no_examples() -> None:
    result = core.render_react_prompting("Solve equation", "a tool description")
    assert "a tool description" in result
    assert "Examples:" not in result


def test_render_react_prompting_tool_missing_keys_raises_keyerror() -> None:
    """
    PRODUCTION BUG (pinned, not fixed -- ruling required to change source):

    render_react_prompting (zeo_core/prompt/strategies/core.py:502-504) builds
    its tools listing with `t['name']` / `t['description']` (bare dict subscript),
    unlike its sibling render_react_agentic (same file, lines 98-99) which uses
    `tool.get("name", "Unnamed Tool")` / `tool.get("description", "No description")`
    for the exact same "tool dict" shape. Both strategies declare the same
    `tools: list[dict] | str` input type and are selected interchangeably by tags
    ("tool-use" / "agent") via the selector, so callers have no way to know that
    one variant will silently crash on a tool dict missing "name" or
    "description" while the other degrades gracefully. This test pins the
    current (buggy) crashing behavior with a real, unmocked call.
    """
    import pytest

    tools = [{"description": "does math"}]  # no "name" key
    with pytest.raises(KeyError):
        core.render_react_prompting("Solve equation", tools)


def test_react_prompting_strategy_metadata() -> None:
    assert core.react_prompting_strategy.id == "react-prompting"


# --- Role Prompting ---


def test_render_role_prompting() -> None:
    result = core.render_role_prompting("senior python developer", "review this PR")
    assert "act as a senior python developer" in result
    assert "review this PR" in result


def test_role_prompting_strategy_metadata() -> None:
    assert core.role_prompting_strategy.id == "role-prompting"


# --- Self-consistency Prompting ---


def test_render_self_consistency_prompting() -> None:
    result = core.render_self_consistency_prompting("What is 2 + 2?")
    assert "What is 2 + 2?" in result
    assert "multiple reasoning paths" in result


def test_self_consistency_prompting_strategy_metadata() -> None:
    assert core.self_consistency_prompting_strategy.id == "self-consistency-prompting"


# --- Simplify Prompt ---


def test_render_simplify_prompt() -> None:
    result = core.render_simplify_prompt("A very convoluted prompt with jargon")
    assert "A very convoluted prompt with jargon" in result
    assert "clear and simple" in result


def test_simplify_prompt_strategy_metadata() -> None:
    assert core.simplify_prompt_strategy.id == "simplify-prompt"


# --- Step-back Prompting ---


def test_render_step_back_prompting() -> None:
    result = core.render_step_back_prompting(
        "Physics principles at play", "solve the projectile problem"
    )
    assert "Physics principles at play" in result
    assert "solve the projectile problem" in result


def test_step_back_prompting_strategy_metadata() -> None:
    assert core.step_back_prompting_strategy.id == "step-back-prompting"


# --- System Prompt Engineer ---


def test_render_system_prompt_engineer() -> None:
    result = core.render_system_prompt_engineer("for a coding assistant")
    assert "for a coding assistant" in result
    assert "expert prompt engineer" in result


def test_system_prompt_engineer_strategy_metadata() -> None:
    assert core.system_prompt_engineer_strategy.id == "system-prompt-engineer"


# --- System Prompting ---


def test_render_system_prompting() -> None:
    result = core.render_system_prompting("Answer the question", "You are terse.")
    assert "You are terse." in result
    assert "Answer the question" in result


def test_system_prompting_strategy_metadata() -> None:
    assert core.system_prompting_strategy.id == "system-prompting"


# --- Translating Code Prompting ---


def test_render_translating_code_prompting() -> None:
    result = core.render_translating_code_prompting("print('hi')", "Rust")
    assert "print('hi')" in result
    assert "Rust" in result


def test_translating_code_prompting_strategy_metadata() -> None:
    assert core.translating_code_prompting_strategy.id == "translating-code-prompting"


# --- Tree of Thoughts Prompting ---


def test_render_tree_of_thought_prompting() -> None:
    result = core.render_tree_of_thought_prompting("Plan a trip")
    assert "Plan a trip" in result
    assert "several alternative intermediate steps" in result


def test_tree_of_thought_prompting_strategy_metadata() -> None:
    assert core.tree_of_thought_prompting_strategy.id == "tree-of-thought-prompting"


# --- Working with Schemas Prompting ---


def test_render_working_with_schemas_prompting() -> None:
    result = core.render_working_with_schemas_prompting("{type: object}", '{"a": 1}')
    assert "{type: object}" in result
    assert '{"a": 1}' in result


def test_working_with_schemas_prompting_strategy_metadata() -> None:
    assert core.working_with_schemas_prompting_strategy.id == (
        "working-with-schemas-prompting"
    )


# --- Writing Code Prompting ---


def test_render_writing_code_prompting() -> None:
    result = core.render_writing_code_prompting("a fibonacci generator")
    assert "a fibonacci generator" in result
    assert "Write a code snippet" in result


def test_writing_code_prompting_strategy_metadata() -> None:
    assert core.writing_code_prompting_strategy.id == "writing-code-prompting"


# --- get_internal_strategies ---


def test_get_internal_strategies_returns_all_28_strategies() -> None:
    strategies = core.get_internal_strategies()
    assert len(strategies) == 28
    assert all(isinstance(s, PromptStrategy) for s in strategies)
    # All IDs must be unique.
    ids = [s.id for s in strategies]
    assert len(ids) == len(set(ids))


def test_get_internal_strategies_includes_known_ids() -> None:
    ids = {s.id for s in core.get_internal_strategies()}
    assert "zero-shot-prompting" in ids
    assert "react-agentic" in ids
    assert "working-with-schemas-prompting" in ids
