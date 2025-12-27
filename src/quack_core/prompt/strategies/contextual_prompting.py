# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/contextual_prompting.py
# module: quack_core.prompt.strategies.contextual_prompting
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, debugging_code_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Contextual Prompting strategy for the PromptBooster.

This strategy provides task-specific context or background information.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(context: str, task_description: str) -> str:
    return f"""
Context: {context}

{task_description}
""".strip()

strategy = PromptStrategy(
    id="contextual-prompting",
    label="Contextual Prompting",
    description="Supplies background context to guide the model’s response.",
    input_vars=["context", "task_description"],
    render_fn=render,
    tags=["contextual-prompt", "background"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    example="""
# Example Usage:

# Inputs:
context = "You are writing for a blog about 80's retro arcade video games."
task_description = "Suggest 3 topics to write an article about, each with a brief description of what the article should cover."

# Generated Prompt (rendered):
Context: You are writing for a blog about 80's retro arcade video games.

Suggest 3 topics to write an article about, each with a brief description of what the article should cover.

# Note:
# - The 'Context:' line sets the background. 
# - The next line is the task itself, clear and concise. 
# - Use this structure to guide the model with additional context before the request.
"""
)
register_prompt_strategy(strategy)
