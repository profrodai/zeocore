# quack-core/src/quack-core/prompt/strategies/react_prompting.py
"""
ReAct Prompting strategy for the PromptBooster.

This strategy alternates between reasoning and external tool actions in a loop.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(
    task_description: str,
    tools: list[dict] | str,
    examples: list[str] | str | None = None,
) -> str:
    if isinstance(tools, list):
        tools_str = "Available tools:\n" + "\n".join(
            f"- {t['name']}: {t['description']}" for t in tools
        )
    else:
        tools_str = tools
    examples_section = f"\nExamples:\n{('\n\n'.join(examples))}\n" if examples else ""
    return f"""
{task_description}

{tools_str}

To solve this problem, think and act as follows:
1. Thought: <your reasoning>
2. Action: <tool>(<params>)
3. Observation: <result>
...
Thought: I now know the answer
Final Answer: <your answer>
{examples_section}
""".strip()

strategy = PromptStrategy(
    id="react-prompting",
    label="ReAct Prompting",
    description="Combines reasoning and tool use in an interleaved thought-action loop.",
    input_vars=["task_description", "tools", "examples"],
    render_fn=render,
    tags=["react", "agent"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
