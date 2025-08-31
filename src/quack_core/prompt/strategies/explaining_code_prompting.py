# quack-core/src/quack-core/prompt/strategies/explaining_code_prompting.py
"""
Explaining Code Prompting strategy for the PromptBooster.

This strategy asks the LLM to explain the functionality of a given code snippet.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(code_snippet: str) -> str:
    return f"""
Explain what the following code does in plain English:
{code_snippet}
""".strip()

strategy = PromptStrategy(
    id="explaining-code-prompting",
    label="Explaining Code Prompting",
    description="Requests a natural language explanation of a code snippet.",
    input_vars=["code_snippet"],
    render_fn=render,
    tags=["code", "explanation"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
