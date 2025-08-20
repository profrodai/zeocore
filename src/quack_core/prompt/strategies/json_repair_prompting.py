# quack-core/src/quack-core/prompt/strategies/json_repair_prompting.py
"""
JSON Repair Prompting strategy for the PromptBooster.

This strategy repairs incomplete or malformed JSON into valid JSON.
"""

from quackcore.prompt.registry import register_prompt_strategy
from quackcore.prompt.strategy_base import PromptStrategy


def render(incomplete_json: str) -> str:
    return f"""
The text below is a possibly incomplete or malformed JSON. Repair it to valid JSON:
{incomplete_json}
""".strip()

strategy = PromptStrategy(
    id="json-repair-prompting",
    label="JSON Repair Prompting",
    description="Fixes truncated or invalid JSON outputs to conform to JSON syntax.",
    input_vars=["incomplete_json"],
    render_fn=render,
    tags=["json", "repair"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
