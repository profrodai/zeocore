# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/self_consistency_prompting.py
# module: quack_core.prompt.strategies.self_consistency_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Self-consistency Prompting strategy for the PromptBooster.

This strategy generates multiple reasoning paths and votes on the most consistent answer.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_description: str) -> str:
    return f"""
{task_description}

Generate multiple reasoning paths with a higher temperature and select the most common answer.
""".strip()

strategy = PromptStrategy(
    id="self-consistency-prompting",
    label="Self-consistency Prompting",
    description="Combines sampling and majority voting over multiple reasoning chains.",
    input_vars=["task_description"],
    render_fn=render,
    tags=["self-consistency", "robustness"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
