# quack-core/src/quack-core/prompt/strategies/writing_code_prompting.py
"""
Writing Code Prompting strategy for the PromptBooster.

This strategy instructs the LLM to write a code snippet for a specified task.
"""

from quackcore.prompt.registry import register_prompt_strategy
from quackcore.prompt.strategy_base import PromptStrategy


def render(task_description: str) -> str:
    return f"""
Write a code snippet in the appropriate programming language to:
{task_description}
""".strip()

strategy = PromptStrategy(
    id="writing-code-prompting",
    label="Writing Code Prompting",
    description="Instructs the model to produce code for a defined problem.",
    input_vars=["task_description"],
    render_fn=render,
    tags=["code", "snippet"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
