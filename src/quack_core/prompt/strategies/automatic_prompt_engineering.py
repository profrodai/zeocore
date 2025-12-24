# quack-core/src/quack_core/prompt/strategies/automatic_prompt_engineering.py
"""
Automatic Prompt Engineering strategy for the PromptBooster.

This strategy prompts an LLM to generate and evaluate alternative prompts automatically.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_goal: str, num_variants: int = 5) -> str:
    return f"""
We have the following goal: {task_goal}
Generate {num_variants} prompt variants that preserve the same semantics.
""".strip()

strategy = PromptStrategy(
    id="automatic-prompt-engineering",
    label="Automatic Prompt Engineering",
    description="Automates the generation and selection of effective prompts.",
    input_vars=["task_goal", "num_variants"],
    render_fn=render,
    tags=["automatic-prompt-engineering", "ape"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
