# quack-core/src/quack-core/prompt/strategies/self_consistency_prompting.py
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
