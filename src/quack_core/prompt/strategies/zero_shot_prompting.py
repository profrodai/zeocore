# quack-core/src/quack_core/prompt/strategies/zero_shot_prompting.py
"""
Zero-shot Prompting strategy for the PromptBooster.

This strategy uses a task description without examples to perform zero-shot prompting.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_description: str) -> str:
    return f"""
{task_description}
""".strip()

strategy = PromptStrategy(
    id="zero-shot-prompting",
    label="Zero-shot Prompting",
    description="Uses a task description without examples to perform zero-shot prompting.",
    input_vars=["task_description"],
    render_fn=render,
    tags=["zero-shot", "general-prompting"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    example="""
# Example Usage:

# Inputs:
task_description = "Translate the following English sentence into French: 'The weather is nice today.'"

# Generated Prompt (rendered):
Translate the following English sentence into French: 'The weather is nice today.'

# Note:
# - No examples are provided; the model must rely purely on the instruction.
# - Use this when you want a direct transformation without demonstration.
"""
)
register_prompt_strategy(strategy)
