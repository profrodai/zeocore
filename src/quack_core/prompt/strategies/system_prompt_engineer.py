# quack-core/src/quack-core/prompt/strategies/system_prompt_engineer.py
"""
System Prompt Engineer strategy for the PromptBooster.

This strategy takes a provided prompt (referred to as {strategy})
and instructs the LLM to rewrite and improve it by:
1. Analyzing its structure, clarity, and any ambiguities
2. Considering improvements for enhanced effectiveness for LLMs
3. Rewriting it with precise instructions, clear constraints, and suitable examples
4. Incorporating step-by-step reasoning if the task calls for complex thinking
5. Ensuring the final prompt is complete and ready to use without further modifications

The output should be the rewritten prompt only.
"""

from quackcore.prompt.registry import register_prompt_strategy
from quackcore.prompt.strategy_base import PromptStrategy


def render(strategy: str) -> str:
    """
    Render a system prompt engineer prompt.

    Args:
        strategy: The original prompt to be rewritten and improved

    Returns:
        A formatted prompt instructing an LLM to improve the provided prompt.
    """
    return f"""
You are an expert prompt engineer with deep knowledge of LLM capabilities and limitations.

Your task is to rewrite and improve a given prompt {strategy}.

For each prompt you receive:
1. Analyze its structure, clarity, and potential ambiguities
2. Consider what would make the prompt more effective for an LLM
3. Rewrite it with precise instructions, clear constraints, and appropriate examples
4. Add step-by-step reasoning guidance if the task requires complex thinking
5. Ensure the prompt elicits the desired format and level of detail

Aim for clarity, precision, and effectiveness. The improved prompt should be complete and ready to use without further modification.

IMPORTANT: Only output the rewritten prompt without explanations or meta-commentary.
""".strip()


# Create and register the strategy
strategy = PromptStrategy(
    id="system-prompt-engineer",
    label="System Prompt Engineer",
    description="Generates improved system prompts by rewriting the provided prompt to enhance clarity, precision, and effectiveness.",
    input_vars=["strategy"],
    render_fn=render,
    tags=["system-prompt", "prompt-engineering", "rewriting"],
    origin="Based on the default prompt configuration for system prompt generation",
)

# Register the strategy
register_prompt_strategy(strategy)
