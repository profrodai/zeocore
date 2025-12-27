# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/simplify_prompt.py
# module: quack_core.prompt.strategies.simplify_prompt
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Simplify Prompt strategy for the PromptBooster.

This strategy rewrites a prompt to be clearer and more concise.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(prompt_text: str) -> str:
    return f"""
Rewrite the following prompt to be clear and simple:
{prompt_text}
""".strip()

strategy = PromptStrategy(
    id="simplify-prompt",
    label="Simplify Prompt",
    description="Improves prompt clarity by trimming unnecessary complexity.",
    input_vars=["prompt_text"],
    render_fn=render,
    tags=["simplification", "best-practice"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
