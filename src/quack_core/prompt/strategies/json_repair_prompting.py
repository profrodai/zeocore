# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/json_repair_prompting.py
# module: quack_core.prompt.strategies.json_repair_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
JSON Repair Prompting strategy for the PromptBooster.

This strategy repairs incomplete or malformed JSON into valid JSON.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(incomplete_json: str) -> str:
    return f"""
The text below is a possibly incomplete or malformed JSON. Repair it to valid JSON:
{incomplete_json}
""".strip()

strategy = PromptStrategy(
    id="json-repair-prompting",
    label="JSON Repair Prompting",
    description="Fixes truncated or invalid JSON outputs to conform to JSON syntax.",
    input_vars=["incomplete_json"],
    render_fn=render,
    tags=["json", "repair"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
