# quack-core/src/quack-core/prompt/strategies/step_back_prompting.py
"""
Step-back Prompting strategy for the PromptBooster.

This strategy first asks a general question, then uses its answer as context for the main task.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(background_prompt: str, main_task: str) -> str:
    return f"""
{background_prompt}

Now, using the above, {main_task}
""".strip()

strategy = PromptStrategy(
    id="step-back-prompting",
    label="Step-back Prompting",
    description="Activates background reasoning before the main task for better context.",
    input_vars=["background_prompt", "main_task"],
    render_fn=render,
    tags=["step-back", "reasoning"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
