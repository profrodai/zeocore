# quack-core/src/quack-core/prompt/strategies/zero_shot_cot.py
"""
Zero-shot Chain of Thought (CoT) strategy for the PromptBooster.

This strategy encourages the model to think step-by-step without
providing explicit examples, which can improve reasoning performance.
"""

from quackcore.prompt.registry import register_prompt_strategy
from quackcore.prompt.strategy_base import PromptStrategy


def render(task_description: str, final_instruction: str | None = None) -> str:
    """
    Render a zero-shot chain of thought prompt.

    This strategy encourages the model to break down complex reasoning
    tasks step by step, which often improves performance on tasks
    requiring multi-step reasoning.

    Args:
        task_description: The basic description of the task
        final_instruction: Optional final instruction after thinking step

    Returns:
        A formatted prompt that encourages step-by-step reasoning
    """
    final_instr = ""
    if final_instruction:
        final_instr = f"\n\n{final_instruction}"

    return f"""
{task_description}

Let's think through this step by step.{final_instr}
""".strip()


# Create and register the strategy
strategy = PromptStrategy(
    id="zero-shot-cot",
    label="Zero-shot Chain of Thought",
    description="Encourages step-by-step reasoning without examples.",
    input_vars=["task_description", "final_instruction"],
    render_fn=render,
    tags=["reasoning", "zero-shot", "step-by-step"],
    origin="Chain-of-Thought Prompting Elicits Reasoning in Large Language Models (Wei et al., 2022)",
)

# Register the strategy
register_prompt_strategy(strategy)
