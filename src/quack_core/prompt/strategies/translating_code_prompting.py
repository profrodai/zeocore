# quack-core/src/quack_core/prompt/strategies/translating_code_prompting.py
"""
Translating Code Prompting strategy for the PromptBooster.

This strategy instructs the LLM to translate a code snippet into another programming language.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(source_code: str, target_language: str) -> str:
    return f"""
Translate the following code into {target_language}:
{source_code}
""".strip()

strategy = PromptStrategy(
    id="translating-code-prompting",
    label="Translating Code Prompting",
    description="Translates code from one language to another.",
    input_vars=["source_code", "target_language"],
    render_fn=render,
    tags=["code", "translation"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
