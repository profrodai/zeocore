# quack-core/src/quack_core/prompt/strategies/tree_of_thought_prompting.py
"""
Tree of Thoughts Prompting strategy for the PromptBooster.

This strategy explores multiple reasoning branches simultaneously to find the best path.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_description: str) -> str:
    return f"""
{task_description}

Explore several alternative intermediate steps in parallel and select the optimal result.
""".strip()

strategy = PromptStrategy(
    id="tree-of-thought-prompting",
    label="Tree of Thoughts Prompting",
    description="Maintains a tree of reasoning paths and chooses the best solution.",
    input_vars=["task_description"],
    render_fn=render,
    tags=["tree-of-thought", "search"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
