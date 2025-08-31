# quack-core/src/quack-core/prompt/strategies/role_prompting.py
"""
Role Prompting strategy for the PromptBooster.

This strategy assigns a character or expertise role for the LLM to adopt.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(role: str, task_description: str) -> str:
    return f"""
I want you to act as a {role}.
{task_description}
""".strip()

strategy = PromptStrategy(
    id="role-prompting",
    label="Role Prompting",
    description="Assigns a specific role to guide the model’s tone and expertise.",
    input_vars=["role", "task_description"],
    render_fn=render,
    tags=["role-prompt", "persona"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
