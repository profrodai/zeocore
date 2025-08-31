# quack-core/src/quack-core/prompt/strategies/react_agentic.py
"""
ReAct agentic strategy for the PromptBooster.

This strategy combines reasoning and acting steps for interactive agents,
based on the ReAct paper by Yao et al.
"""

from quack_core.prompt.registry import register_prompt_strategy
from quack_core.prompt.strategy_base import PromptStrategy


def render(
    task_description: str,
    tools: list[dict] | str,
    examples: list[str] | str | None = None,
) -> str:
    """
    Render a ReAct agentic prompt.

    This strategy is effective for tasks that require reasoning and tool use,
    especially for complex, multi-step problems.

    Args:
        task_description: The basic description of the task
        tools: List of tool definitions or string describing available tools
        examples: Optional examples of the ReAct process

    Returns:
        A formatted prompt combining reasoning and acting steps
    """
    # Format tools if they're provided as a list
    if isinstance(tools, list):
        tools_str = "Available tools:\n"
        for tool in tools:
            name = tool.get("name", "Unnamed Tool")
            description = tool.get("description", "No description")
            parameters = tool.get("parameters", {})

            tools_str += f"- {name}: {description}\n"
            if parameters:
                tools_str += "  Parameters:\n"
                for param, param_desc in parameters.items():
                    tools_str += f"  - {param}: {param_desc}\n"
    else:
        tools_str = tools

    # Format examples if provided
    examples_section = ""
    if examples:
        if isinstance(examples, list):
            examples_str = "\n\n".join(examples)
        else:
            examples_str = examples

        examples_section = f"""
Examples:
{examples_str}

"""

    return f"""
{task_description}

{tools_str}

To solve this problem, think through this step-by-step:

1. First, understand what is being asked
2. Form a plan using the available tools
3. For each step in your plan:
   - Think: What do you know and what do you need to find out?
   - Act: Select and use the appropriate tool
   - Observe: Note the result
   - Decide: Determine the next step based on your observation

{examples_section}For each step, use the following format:

Thought: <your reasoning about what to do next>
Action: <tool_name>(<parameters>)
Observation: <result of the action>
...
Thought: I now know the answer
Final Answer: <your final answer to the task>

Begin!
""".strip()


# Create and register the strategy
strategy = PromptStrategy(
    id="react-agentic",
    label="ReAct Agentic Prompt",
    description="Combines reasoning and acting steps for interactive agents.",
    input_vars=["task_description", "tools", "examples"],
    render_fn=render,
    tags=["reasoning", "tool-use", "multi-step"],
    origin="ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022)",
)

# Register the strategy
register_prompt_strategy(strategy)
