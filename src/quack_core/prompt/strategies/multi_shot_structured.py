# quack-core/src/quack-core/prompt/strategies/multi_shot_structured.py
"""
Multi-shot structured strategy for the PromptBooster.

This strategy provides a template for extracting structured data
using multiple examples and a schema.
"""

from quackcore.prompt.registry import register_prompt_strategy
from quackcore.prompt.strategy_base import PromptStrategy


def render(task_description: str, schema: str, examples: list[str] | str) -> str:
    """
    Render a multi-shot structured prompt.

    This strategy is effective for tasks that require structured output
    and benefit from multiple examples demonstrating the desired format.

    Args:
        task_description: The basic description of the task
        schema: The schema for the structured output
        examples: List of examples or string containing examples

    Returns:
        A formatted prompt with task description, examples, and schema
    """
    # Convert examples to string if it's a list
    if isinstance(examples, list):
        examples_str = "\n\n".join(examples)
    else:
        examples_str = examples

    return f"""
{task_description}

Here are some examples:
{examples_str}

Return your output in JSON using this schema:
{schema}
""".strip()


# Create and register the strategy
strategy = PromptStrategy(
    id="multi-shot-structured",
    label="Multi-shot Structured",
    description="Uses several examples and a schema to extract structured data.",
    input_vars=["task_description", "schema", "examples"],
    render_fn=render,
    tags=["structured-output", "few-shot", "stable"],
    origin="Internal strategy based on OpenAI Cookbook + CRM Podcast prompt iterations",
)

# Register the strategy
register_prompt_strategy(strategy)
