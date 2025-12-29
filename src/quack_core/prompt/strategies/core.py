# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/core.py
# module: quack_core.prompt.strategies.core
# role: module
# neighbors: __init__.py
# exports: render_zero_shot, render_multi_shot_structured, render_single_shot_structured, render_react_agentic, render_zero_shot_cot, render_task_decomposition, render_apply_best_practices, render_automatic_prompt_engineering (+21 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 21a4e25
# === QV-LLM:END ===

"""
Core prompt strategies for the PromptService.

This module contains all the built-in prompt enhancement strategies.
"""

from quack_core.prompt.models import PromptStrategy

# --- Zero Shot ---
def render_zero_shot(task_description: str) -> str:
    return f"{task_description}".strip()

zero_shot_strategy = PromptStrategy(
    id="zero-shot-prompting",
    label="Zero-shot Prompting",
    description="Uses a task description without examples to perform zero-shot prompting.",
    input_vars=["task_description"],
    render_fn=render_zero_shot,
    tags=["zero-shot", "general-prompting"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Multi-Shot Structured ---
def render_multi_shot_structured(task_description: str, schema: str, examples: list[str] | str) -> str:
    ex_str = "\n\n".join(examples) if isinstance(examples, list) else examples
    return f"""
{task_description}

Here are some examples:
{ex_str}

Return your output in JSON using this schema:
{schema}
""".strip()

multi_shot_structured_strategy = PromptStrategy(
    id="multi-shot-structured",
    label="Multi-shot Structured",
    description="Uses several examples and a schema to extract structured data.",
    input_vars=["task_description", "schema", "examples"],
    render_fn=render_multi_shot_structured,
    tags=["structured-output", "few-shot", "stable"],
    origin="Internal strategy based on OpenAI Cookbook + CRM Podcast prompt iterations",
    priority=50,
    example=None,
)

# --- Single-Shot Structured ---
def render_single_shot_structured(task_description: str, schema: str, example: str | None = None) -> str:
    ex_section = f"\nHere is an example:\n{example}\n" if example else ""
    return f"""
{task_description}

{ex_section}Return your output in JSON using this schema:
{schema}
""".strip()

single_shot_structured_strategy = PromptStrategy(
    id="single-shot-structured",
    label="Single-shot Structured",
    description="Uses a single example and a schema to extract structured data.",
    input_vars=["task_description", "schema", "example"],
    render_fn=render_single_shot_structured,
    tags=["structured-output", "one-shot", "stable"],
    origin="Simplified version of few-shot learning with a focus on schema-alignment",
    priority=60,
    example=None,
)

# --- ReAct Agentic ---
def render_react_agentic(
    task_description: str,
    tools: list[dict] | str,
    examples: list[str] | str | None = None,
) -> str:
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

react_agentic_strategy = PromptStrategy(
    id="react-agentic",
    label="ReAct Agentic Prompt",
    description="Combines reasoning and acting steps for interactive agents.",
    input_vars=["task_description", "tools", "examples"],
    render_fn=render_react_agentic,
    tags=["reasoning", "tool-use", "multi-step"],
    origin="ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022)",
    priority=100,
    example=None,
)

# --- Zero-Shot Chain of Thought ---
def render_zero_shot_cot(task_description: str, final_instruction: str | None = None) -> str:
    final_instr = ""
    if final_instruction:
        final_instr = f"\n\n{final_instruction}"

    return f"""
{task_description}

Let's think through this step by step.{final_instr}
""".strip()

zero_shot_cot_strategy = PromptStrategy(
    id="zero-shot-cot",
    label="Zero-shot Chain of Thought",
    description="Encourages step-by-step reasoning without examples.",
    input_vars=["task_description", "final_instruction"],
    render_fn=render_zero_shot_cot,
    tags=["reasoning", "zero-shot", "step-by-step"],
    origin="Chain-of-Thought Prompting Elicits Reasoning in Large Language Models (Wei et al., 2022)",
    priority=100,
    example=None,
)

# --- Task Decomposition ---
def render_task_decomposition(task_description: str, output_format: str | None = None) -> str:
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

task_decomposition_strategy = PromptStrategy(
    id="task-decomposition",
    label="Task Decomposition",
    description="Breaks down complex tasks into manageable subtasks for sequential solving.",
    input_vars=["task_description", "output_format"],
    render_fn=render_task_decomposition,
    tags=["decomposition", "complex-tasks", "structured-thinking"],
    origin="Based on 'Least-to-Most Prompting' and 'Chain of Thought' research",
    priority=100,
    example=None,
)

# --- Apply Best Practices ---
def render_apply_best_practices(prompt_text: str, guidelines: list[str]) -> str:
    guidelines_str = "\n".join(f"- {g}" for g in guidelines)
    return f"""
You are a prompt engineer. Improve the following prompt by applying these guidelines:
{guidelines_str}

Original prompt:
{prompt_text}

Provide the improved prompt only.
""".strip()

apply_best_practices_strategy = PromptStrategy(
    id="apply-best-practices",
    label="Apply Best Practices",
    description="Enhances a prompt by systematically applying a set of guidelines.",
    input_vars=["prompt_text", "guidelines"],
    render_fn=render_apply_best_practices,
    tags=["best-practice", "meta-strategy"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Automatic Prompt Engineering ---
def render_automatic_prompt_engineering(task_goal: str, num_variants: int = 5) -> str:
    return f"""
We have the following goal: {task_goal}
Generate {num_variants} prompt variants that preserve the same semantics.
""".strip()

automatic_prompt_engineering_strategy = PromptStrategy(
    id="automatic-prompt-engineering",
    label="Automatic Prompt Engineering",
    description="Automates the generation and selection of effective prompts.",
    input_vars=["task_goal", "num_variants"],
    render_fn=render_automatic_prompt_engineering,
    tags=["automatic-prompt-engineering", "ape"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Chain of Thought Prompting ---
def render_chain_of_thought_prompting(task_description: str, final_instruction: str | None = None) -> str:
    final_instr = f"\n{final_instruction}" if final_instruction else ""
    return f"""
{task_description}

Let's think through this step by step.{final_instr}
""".strip()

chain_of_thought_prompting_strategy = PromptStrategy(
    id="chain-of-thought-prompting",
    label="Chain of Thought Prompting",
    description="Encourages the model to break down reasoning into intermediate steps.",
    input_vars=["task_description", "final_instruction"],
    render_fn=render_chain_of_thought_prompting,
    tags=["chain-of-thought", "reasoning"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Code Prompting ---
def render_code_prompting(code_task_description: str) -> str:
    return f"""
Write code to accomplish the following task:
{code_task_description}
""".strip()

code_prompting_strategy = PromptStrategy(
    id="code-prompting",
    label="Code Prompting",
    description="Generates code based on a natural language description of a task.",
    input_vars=["code_task_description"],
    render_fn=render_code_prompting,
    tags=["code", "generation"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Contextual Prompting ---
def render_contextual_prompting(context: str, task_description: str) -> str:
    return f"""
Context: {context}

{task_description}
""".strip()

contextual_prompting_strategy = PromptStrategy(
    id="contextual-prompting",
    label="Contextual Prompting",
    description="Supplies background context to guide the model's response.",
    input_vars=["context", "task_description"],
    render_fn=render_contextual_prompting,
    tags=["contextual-prompt", "background"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Debugging Code Prompting ---
def render_debugging_code_prompting(broken_code: str) -> str:
    return f"""
The following code has errors:
{broken_code}

Please debug it and explain the fixes.
""".strip()

debugging_code_prompting_strategy = PromptStrategy(
    id="debugging-code-prompting",
    label="Debugging Code Prompting",
    description="Identifies errors in code and provides corrected versions.",
    input_vars=["broken_code"],
    render_fn=render_debugging_code_prompting,
    tags=["code", "debugging"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Explaining Code Prompting ---
def render_explaining_code_prompting(code_snippet: str) -> str:
    return f"""
Explain what the following code does in plain English:
{code_snippet}
""".strip()

explaining_code_prompting_strategy = PromptStrategy(
    id="explaining-code-prompting",
    label="Explaining Code Prompting",
    description="Requests a natural language explanation of a code snippet.",
    input_vars=["code_snippet"],
    render_fn=render_explaining_code_prompting,
    tags=["code", "explanation"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Few-shot Prompting ---
def render_few_shot_prompting(task_description: str, examples: list[str] | str) -> str:
    if isinstance(examples, list):
        examples_str = "\n\n".join(examples)
    else:
        examples_str = examples

    return f"""
{task_description}

Examples:
{examples_str}
""".strip()

few_shot_prompting_strategy = PromptStrategy(
    id="few-shot-prompting",
    label="Few-shot Prompting",
    description="Provides multiple examples to guide the model's response.",
    input_vars=["task_description", "examples"],
    render_fn=render_few_shot_prompting,
    tags=["few-shot", "demonstration"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- JSON Repair Prompting ---
def render_json_repair_prompting(incomplete_json: str) -> str:
    return f"""
The text below is a possibly incomplete or malformed JSON. Repair it to valid JSON:
{incomplete_json}
""".strip()

json_repair_prompting_strategy = PromptStrategy(
    id="json-repair-prompting",
    label="JSON Repair Prompting",
    description="Fixes truncated or invalid JSON outputs to conform to JSON syntax.",
    input_vars=["incomplete_json"],
    render_fn=render_json_repair_prompting,
    tags=["json", "repair"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Multimodal Prompting ---
def render_multimodal_prompting(modalities_description: str, task_description: str) -> str:
    return f"""
You have the following inputs: {modalities_description}

{task_description}
""".strip()

multimodal_prompting_strategy = PromptStrategy(
    id="multimodal-prompting",
    label="Multimodal Prompting",
    description="Integrates multiple input modalities to guide the model.",
    input_vars=["modalities_description", "task_description"],
    render_fn=render_multimodal_prompting,
    tags=["multimodal", "prompting"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- One-shot Prompting ---
def render_one_shot_prompting(task_description: str, example: str) -> str:
    return f"""
{task_description}

Example:
{example}
""".strip()

one_shot_prompting_strategy = PromptStrategy(
    id="one-shot-prompting",
    label="One-shot Prompting",
    description="Provides one example to guide the model's response.",
    input_vars=["task_description", "example"],
    render_fn=render_one_shot_prompting,
    tags=["one-shot", "few-shot"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- ReAct Prompting ---
def render_react_prompting(
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

react_prompting_strategy = PromptStrategy(
    id="react-prompting",
    label="ReAct Prompting",
    description="Combines reasoning and tool use in an interleaved thought-action loop.",
    input_vars=["task_description", "tools", "examples"],
    render_fn=render_react_prompting,
    tags=["react", "agent"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Role Prompting ---
def render_role_prompting(role: str, task_description: str) -> str:
    return f"""
I want you to act as a {role}.
{task_description}
""".strip()

role_prompting_strategy = PromptStrategy(
    id="role-prompting",
    label="Role Prompting",
    description="Assigns a specific role to guide the model's tone and expertise.",
    input_vars=["role", "task_description"],
    render_fn=render_role_prompting,
    tags=["role-prompt", "persona"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Self-consistency Prompting ---
def render_self_consistency_prompting(task_description: str) -> str:
    return f"""
{task_description}

Generate multiple reasoning paths with a higher temperature and select the most common answer.
""".strip()

self_consistency_prompting_strategy = PromptStrategy(
    id="self-consistency-prompting",
    label="Self-consistency Prompting",
    description="Combines sampling and majority voting over multiple reasoning chains.",
    input_vars=["task_description"],
    render_fn=render_self_consistency_prompting,
    tags=["self-consistency", "robustness"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Simplify Prompt ---
def render_simplify_prompt(prompt_text: str) -> str:
    return f"""
Rewrite the following prompt to be clear and simple:
{prompt_text}
""".strip()

simplify_prompt_strategy = PromptStrategy(
    id="simplify-prompt",
    label="Simplify Prompt",
    description="Improves prompt clarity by trimming unnecessary complexity.",
    input_vars=["prompt_text"],
    render_fn=render_simplify_prompt,
    tags=["simplification", "best-practice"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Step-back Prompting ---
def render_step_back_prompting(background_prompt: str, main_task: str) -> str:
    return f"""
{background_prompt}

Now, using the above, {main_task}
""".strip()

step_back_prompting_strategy = PromptStrategy(
    id="step-back-prompting",
    label="Step-back Prompting",
    description="Activates background reasoning before the main task for better context.",
    input_vars=["background_prompt", "main_task"],
    render_fn=render_step_back_prompting,
    tags=["step-back", "reasoning"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- System Prompt Engineer ---
def render_system_prompt_engineer(strategy: str) -> str:
    return f"""
You are an expert prompt engineer with deep knowledge of LLM capabilities and limitations.

Your task is to rewrite and improve a given prompt {strategy}.

For each prompt you receive:
1. Analyze its structure, clarity, and potential ambiguities
2. Consider what would make the prompt more effective for an LLM
3. Rewrite it with precise instructions, clear constraints, and appropriate examples
4. Add step-by-step reasoning guidance if the task requires complex thinking
5. Ensure the prompt elicits the desired format and level of detail

Aim for clarity, precision, and effectiveness. The improved prompt should be complete and ready to use without further modification.

IMPORTANT: Only output the rewritten prompt without explanations or meta-commentary.
""".strip()

system_prompt_engineer_strategy = PromptStrategy(
    id="system-prompt-engineer",
    label="System Prompt Engineer",
    description="Generates improved system prompts by rewriting the provided prompt to enhance clarity, precision, and effectiveness.",
    input_vars=["strategy"],
    render_fn=render_system_prompt_engineer,
    tags=["system-prompt", "prompt-engineering", "rewriting"],
    origin="Based on the default prompt configuration for system prompt generation",
    priority=100,
    example=None,
)

# --- System Prompting ---
def render_system_prompting(task_description: str, system_instructions: str) -> str:
    return f"""
{system_instructions}

{task_description}
""".strip()

system_prompting_strategy = PromptStrategy(
    id="system-prompting",
    label="System Prompting",
    description="Adds system-level instructions or constraints before the task.",
    input_vars=["task_description", "system_instructions"],
    render_fn=render_system_prompting,
    tags=["system-prompt", "instructions"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Translating Code Prompting ---
def render_translating_code_prompting(source_code: str, target_language: str) -> str:
    return f"""
Translate the following code into {target_language}:
{source_code}
""".strip()

translating_code_prompting_strategy = PromptStrategy(
    id="translating-code-prompting",
    label="Translating Code Prompting",
    description="Translates code from one language to another.",
    input_vars=["source_code", "target_language"],
    render_fn=render_translating_code_prompting,
    tags=["code", "translation"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Tree of Thoughts Prompting ---
def render_tree_of_thought_prompting(task_description: str) -> str:
    return f"""
{task_description}

Explore several alternative intermediate steps in parallel and select the optimal result.
""".strip()

tree_of_thought_prompting_strategy = PromptStrategy(
    id="tree-of-thought-prompting",
    label="Tree of Thoughts Prompting",
    description="Maintains a tree of reasoning paths and chooses the best solution.",
    input_vars=["task_description"],
    render_fn=render_tree_of_thought_prompting,
    tags=["tree-of-thought", "search"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Working with Schemas Prompting ---
def render_working_with_schemas_prompting(schema: str, data: str) -> str:
    return f"""
Given the following JSON schema:
{schema}

And the data:
{data}

Generate a JSON object conforming to the schema.
""".strip()

working_with_schemas_prompting_strategy = PromptStrategy(
    id="working-with-schemas-prompting",
    label="Working with Schemas Prompting",
    description="Uses a JSON schema to structure the model's output precisely.",
    input_vars=["schema", "data"],
    render_fn=render_working_with_schemas_prompting,
    tags=["json", "schema", "structured-output"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

# --- Writing Code Prompting ---
def render_writing_code_prompting(task_description: str) -> str:
    return f"""
Write a code snippet in the appropriate programming language to:
{task_description}
""".strip()

writing_code_prompting_strategy = PromptStrategy(
    id="writing-code-prompting",
    label="Writing Code Prompting",
    description="Instructs the model to produce code for a defined problem.",
    input_vars=["task_description"],
    render_fn=render_writing_code_prompting,
    tags=["code", "snippet"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
    priority=100,
    example=None,
)

def get_internal_strategies() -> list[PromptStrategy]:
    """Returns a list of all core strategies defined in this module."""
    return [
        zero_shot_strategy,
        multi_shot_structured_strategy,
        single_shot_structured_strategy,
        react_agentic_strategy,
        zero_shot_cot_strategy,
        task_decomposition_strategy,
        apply_best_practices_strategy,
        automatic_prompt_engineering_strategy,
        chain_of_thought_prompting_strategy,
        code_prompting_strategy,
        contextual_prompting_strategy,
        debugging_code_prompting_strategy,
        explaining_code_prompting_strategy,
        few_shot_prompting_strategy,
        json_repair_prompting_strategy,
        multimodal_prompting_strategy,
        one_shot_prompting_strategy,
        react_prompting_strategy,
        role_prompting_strategy,
        self_consistency_prompting_strategy,
        simplify_prompt_strategy,
        step_back_prompting_strategy,
        system_prompt_engineer_strategy,
        system_prompting_strategy,
        translating_code_prompting_strategy,
        tree_of_thought_prompting_strategy,
        working_with_schemas_prompting_strategy,
        writing_code_prompting_strategy,
    ]