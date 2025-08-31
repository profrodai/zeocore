# quack-core/src/quack-core/prompt/strategies/single_shot_structured.py
"""
Single-shot structured strategy for the PromptBooster.

This strategy provides a template for extracting structured data
using a single example and a schema.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_description: str, schema: str, example: str | None = None) -> str:
    """
    Render a single-shot structured prompt.

    This strategy is effective for simpler structured data extraction tasks
    where a full set of examples isn't necessary.

    Args:
        task_description: The basic description of the task
        schema: The schema for the structured output
        example: Optional single example of the desired output

    Returns:
        A formatted prompt with task description, optional example, and schema
    """
    example_section = ""
    if example:
        example_section = f"""
Here is an example:
{example}

"""

    return f"""
{task_description}

{example_section}Return your output in JSON using this schema:
{schema}
""".strip()


# Create and register the strategy
strategy = PromptStrategy(
    id="single-shot-structured",
    label="Single-shot Structured",
    description="Uses a single example and a schema to extract structured data.",
    input_vars=["task_description", "schema", "example"],
    render_fn=render,
    tags=["structured-output", "one-shot", "stable"],
    origin="Simplified version of few-shot learning with a focus on schema-alignment",
)

# Register the strategy
register_prompt_strategy(strategy)
