# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/multimodal_prompting.py
# module: quack_core.prompt.strategies.multimodal_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

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
