# quack-core/src/quack-core/prompt/strategies/few_shot_prompting.py
"""
Few-shot Prompting strategy for the PromptBooster.

This strategy provides multiple examples to show the desired pattern.
"""

from quackcore.prompt.registry import register_prompt_strategy
from quackcore.prompt.strategy_base import PromptStrategy


def render(task_description: str, examples: list[str] | str) -> str:
    if isinstance(examples, list):
        examples_str = "\n\n".join(examples)
    else:
        examples_str = examples

    return f"""
{task_description}

Examples:
{examples_str}
""".strip()

strategy = PromptStrategy(
    id="few-shot-prompting",
    label="Few-shot Prompting",
    description="Provides multiple examples to guide the model’s response.",
    input_vars=["task_description", "examples"],
    render_fn=render,
    tags=["few-shot", "demonstration"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    example="""
# Example Usage:

# Inputs:
task_description = "Classify these emails as SPAM or NOT SPAM."
examples = [
    "Email: 'You won a free cruise! Claim now.'\nLabel: SPAM",
    "Email: 'Meeting at 3pm in the main conference room.'\nLabel: NOT SPAM",
    "Email: 'Lowest prices on medicines, click here!'\nLabel: SPAM",
]

# Generated Prompt (rendered):
Classify these emails as SPAM or NOT SPAM.

Examples:
Email: 'You won a free cruise! Claim now.'
Label: SPAM

Email: 'Meeting at 3pm in the main conference room.'
Label: NOT SPAM

Email: 'Lowest prices on medicines, click here!'
Label: SPAM

# Note:
# - Include at least 3 examples covering both classes.
# - Mixing classes prevents bias toward a fixed order.
"""
)
register_prompt_strategy(strategy)
