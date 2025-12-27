# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/one_shot_prompting.py
# module: quack_core.prompt.strategies.one_shot_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
One-shot Prompting strategy for the PromptBooster.

This strategy provides a single example demonstration to guide the LLM.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_description: str, example: str) -> str:
    return f"""
{task_description}

Example:
{example}
""".strip()

strategy = PromptStrategy(
    id="one-shot-prompting",
    label="One-shot Prompting",
    description="Provides one example to guide the model’s response.",
    input_vars=["task_description", "example"],
    render_fn=render,
    tags=["one-shot", "few-shot"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    example="""
# Example Usage:

# Inputs:
task_description = "Convert the following temperature from Celsius to Fahrenheit: 25°C."
example = "Convert the following temperature from Celsius to Fahrenheit: 0°C.\nResult: 32°F."

# Generated Prompt (rendered):
Convert the following temperature from Celsius to Fahrenheit: 25°C.

Example:
Convert the following temperature from Celsius to Fahrenheit: 0°C.
Result: 32°F.

# Note:
# - The example shows the format the model should follow.
# - Only one demonstration is required to teach the pattern.
"""
)
register_prompt_strategy(strategy)
