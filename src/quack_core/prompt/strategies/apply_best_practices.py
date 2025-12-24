# quack-core/src/quack_core/prompt/strategies/apply_best_practices.py
"""
Apply Best Practices strategy for the PromptBooster.

This meta-strategy takes a list of guidelines and applies them to improve an existing prompt.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(prompt_text: str, guidelines: list[str]) -> str:
    guidelines_str = "\n".join(f"- {g}" for g in guidelines)
    return f"""
You are a prompt engineer. Improve the following prompt by applying these guidelines:
{guidelines_str}

Original prompt:
{prompt_text}

Provide the improved prompt only.
""".strip()

strategy = PromptStrategy(
    id="apply-best-practices",
    label="Apply Best Practices",
    description="Enhances a prompt by systematically applying a set of guidelines.",
    input_vars=["prompt_text", "guidelines"],
    render_fn=render,
    tags=["best-practice", "meta-strategy"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
