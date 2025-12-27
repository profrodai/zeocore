# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/writing_code_prompting.py
# module: quack_core.prompt.strategies.writing_code_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Writing Code Prompting strategy for the PromptBooster.

This strategy instructs the LLM to write a code snippet for a specified task.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


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
