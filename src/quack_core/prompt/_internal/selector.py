# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/_internal/selector.py
# module: quack_core.prompt._internal.selector
# role: module
# neighbors: __init__.py, registry.py, enhancer.py
# exports: select_best_strategy
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

from typing import Any

from quack_core.prompt.models import PromptStrategy

from .registry import StrategyRegistry


def select_best_strategy(
        registry: StrategyRegistry,
        tags: list[str] | None = None,
        schema: str | None = None,
        examples: list[str] | str | None = None,
        extra_inputs: dict[str, Any] | None = None,
) -> PromptStrategy | None:
    """
    Heuristic logic to select the best strategy based on inputs.
    Selection is deterministic based on (priority, id).
    """
    matches: list[PromptStrategy] = []
    inputs = extra_inputs or {}

    # 1. Try tags (Exact match by default via registry)
    if tags:
        matches = registry.find_by_tags(tags)

    # 2. Try Schema + Examples heuristics if no tag matches
    if not matches and schema:
        # Check for multi-shot structured
        if isinstance(examples, list) and len(examples) > 1:
            strat = registry.get("multi-shot-structured")
            if strat:
                matches.append(strat)

        # Check for single-shot structured
        if not matches and examples:
            strat = registry.get("single-shot-structured")
            if strat:
                matches.append(strat)

        # Fallback for schema ONLY if we have data to process
        if not matches and inputs.get("data") is not None:
            strat = registry.get("working-with-schemas-prompting")
            if strat:
                matches.append(strat)

    # 3. Default fallback (Zero shot)
    if not matches:
        strat = registry.get("zero-shot-prompting")
        if strat:
            matches.append(strat)

    if not matches:
        return None

    # Sort deterministically: Lower priority score first, then alphabetical ID
    matches.sort(key=lambda s: (s.priority, s.id))

    return matches[0]
