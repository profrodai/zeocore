# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/task_decomposition.py
# module: quack_core.prompt.strategies.task_decomposition
# role: module
# neighbors: __init__.py, apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py (+22 more)
# exports: render
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Task decomposition strategy for the PromptBooster.

This strategy helps break down complex tasks into smaller,
more manageable subtasks for better handling by LLMs.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(task_description: str, output_format: str | None = None) -> str:
    """
    Render a task decomposition prompt.

    This strategy is effective for complex tasks that can be broken down
    into smaller, sequential steps. It helps the model address each part
    of the problem methodically.

    Args:
        task_description: The basic description of the task
        output_format: Optional instruction for how to format the final output

    Returns:
        A formatted prompt that encourages task decomposition
    """
    output_format_section = ""
    if output_format:
        output_format_section = f"""
After you've completed all the steps, format your final answer according to these instructions:
{output_format}
"""

    return f"""
I need to solve this complex task: {task_description}

To solve this effectively, please:

1. Break down this task into smaller, manageable subtasks
2. List each subtask in the order they should be addressed
3. Solve each subtask step by step
4. For each subtask, explain your approach and reasoning
5. Combine the results of all subtasks to solve the original problem

{output_format_section}
""".strip()


# Create and register the strategy
strategy = PromptStrategy(
    id="task-decomposition",
    label="Task Decomposition",
    description="Breaks down complex tasks into manageable subtasks for sequential solving.",
    input_vars=["task_description", "output_format"],
    render_fn=render,
    tags=["decomposition", "complex-tasks", "structured-thinking"],
    origin="Based on 'Least-to-Most Prompting' and 'Chain of Thought' research",
)

# Register the strategy
register_prompt_strategy(strategy)
