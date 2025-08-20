# quack-core/src/quack-core/prompt/strategies/working_with_schemas_prompting.py
"""
Working with Schemas Prompting strategy for the PromptBooster.

This strategy provides a JSON schema and data to guide structured output generation.
"""

from quackcore.prompt.registry import register_prompt_strategy
from quackcore.prompt.strategy_base import PromptStrategy


def render(schema: str, data: str) -> str:
    return f"""
Given the following JSON schema:
{schema}

And the data:
{data}

Generate a JSON object conforming to the schema.
""".strip()

strategy = PromptStrategy(
    id="working-with-schemas-prompting",
    label="Working with Schemas Prompting",
    description="Uses a JSON schema to structure the model’s output precisely.",
    input_vars=["schema", "data"],
    render_fn=render,
    tags=["json", "schema", "structured-output"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
