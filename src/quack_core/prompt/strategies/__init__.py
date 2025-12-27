# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/strategies/__init__.py
# module: quack_core.prompt.strategies.__init__
# role: module
# neighbors: apply_best_practices.py, automatic_prompt_engineering.py, chain_of_thought_prompting.py, code_prompting.py, contextual_prompting.py, debugging_code_prompting.py (+22 more)
# exports: multi_shot_structured, single_shot_structured, react_agentic, zero_shot_cot, task_decomposition
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Prompt strategies package for the PromptBooster.

This package contains various prompt enhancement strategies.
"""

# Import all strategies to register them
from . import (
    multi_shot_structured,
    react_agentic,
    single_shot_structured,
    task_decomposition,
    zero_shot_cot,
)

__all__ = [
    "multi_shot_structured",
    "single_shot_structured",
    "react_agentic",
    "zero_shot_cot",
    "task_decomposition",
]
