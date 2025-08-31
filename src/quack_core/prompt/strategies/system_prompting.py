# quack-core/src/quack-core/prompt/strategies/system_prompting.py
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
