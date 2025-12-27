# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/code_prompting.py
# module: quack_core.prompt.strategies.code_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, contextual_prompting.py, debugging_code_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

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
