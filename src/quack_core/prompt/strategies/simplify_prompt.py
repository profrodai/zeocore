# quack-core/src/quack-core/prompt/strategies/simplify_prompt.py
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
