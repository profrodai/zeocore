# quack-core/src/quack_core/prompt/strategies/debugging_code_prompting.py
"""
Debugging Code Prompting strategy for the PromptBooster.

This strategy asks the LLM to identify and fix errors in a provided code snippet.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(broken_code: str) -> str:
    return f"""
The following code has errors:
{broken_code}

Please debug it and explain the fixes.
""".strip()

strategy = PromptStrategy(
    id="debugging-code-prompting",
    label="Debugging Code Prompting",
    description="Identifies errors in code and provides corrected versions.",
    input_vars=["broken_code"],
    render_fn=render,
    tags=["code", "debugging"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
