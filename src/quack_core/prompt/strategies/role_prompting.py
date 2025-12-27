# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/role_prompting.py
# module: quack_core.prompt.strategies.role_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

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
