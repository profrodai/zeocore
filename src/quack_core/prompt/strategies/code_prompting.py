# quack-core/src/quack-core/prompt/strategies/code_prompting.py
"""
Code Prompting strategy for the PromptBooster.

This generic strategy asks the LLM to produce code for a given task.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(code_task_description: str) -> str:
    return f"""
Write code to accomplish the following task:
{code_task_description}
""".strip()

strategy = PromptStrategy(
    id="code-prompting",
    label="Code Prompting",
    description="Generates code based on a natural language description of a task.",
    input_vars=["code_task_description"],
    render_fn=render,
    tags=["code", "generation"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
