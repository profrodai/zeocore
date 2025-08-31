# quack-core/src/quack-core/prompt/strategies/multimodal_prompting.py
"""
Multimodal Prompting strategy for the PromptBooster.

This strategy combines text with other modalities like images or audio in a single prompt.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(modalities_description: str, task_description: str) -> str:
    return f"""
You have the following inputs: {modalities_description}

{task_description}
""".strip()

strategy = PromptStrategy(
    id="multimodal-prompting",
    label="Multimodal Prompting",
    description="Integrates multiple input modalities to guide the model.",
    input_vars=["modalities_description", "task_description"],
    render_fn=render,
    tags=["multimodal", "prompting"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
