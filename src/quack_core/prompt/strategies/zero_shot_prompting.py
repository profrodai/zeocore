# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/zero_shot_prompting.py
# module: quack_core.prompt.strategies.zero_shot_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Zero-shot Prompting strategy for the PromptBooster.

This strategy uses a task description without examples to perform zero-shot prompting.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_description: str) -> str:
    return f"""
{task_description}
""".strip()

strategy = PromptStrategy(
    id="zero-shot-prompting",
    label="Zero-shot Prompting",
    description="Uses a task description without examples to perform zero-shot prompting.",
    input_vars=["task_description"],
    render_fn=render,
    tags=["zero-shot", "general-prompting"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    example="""
# Example Usage:

# Inputs:
task_description = "Translate the following English sentence into French: 'The weather is nice today.'"

# Generated Prompt (rendered):
Translate the following English sentence into French: 'The weather is nice today.'

# Note:
# - No examples are provided; the model must rely purely on the instruction.
# - Use this when you want a direct transformation without demonstration.
"""
)
register_prompt_strategy(strategy)
