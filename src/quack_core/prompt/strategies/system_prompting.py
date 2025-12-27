# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/system_prompting.py
# module: quack_core.prompt.strategies.system_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
System Prompting strategy for the PromptBooster.

This strategy sets additional instructions or constraints at the system level.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_description: str, system_instructions: str) -> str:
    return f"""
{system_instructions}

{task_description}
""".strip()

strategy = PromptStrategy(
    id="system-prompting",
    label="System Prompting",
    description="Adds system-level instructions or constraints before the task.",
    input_vars=["task_description", "system_instructions"],
    render_fn=render,
    tags=["system-prompt", "instructions"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
