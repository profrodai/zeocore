from typing import Any

from zeo_core.prompt.models import PromptStrategy

from .registry import StrategyRegistry


def _match_by_schema_and_examples(
    registry: StrategyRegistry,
    schema: str | None,
    examples: list[str] | str | None,
    inputs: dict[str, Any],
) -> list[PromptStrategy]:
    """
    Try schema and examples heuristics to find a matching strategy.

    Args:
        registry: Strategy registry to look up strategies in.
        schema: Optional schema identifier.
        examples: Optional examples, a list implies multi-shot.
        inputs: Extra inputs, checked for a "data" key for schema fallback.

    Returns:
        list[PromptStrategy]: Zero or one matching strategy, mirroring the
        original inline logic's early-exit-on-first-match behavior.
    """
    matches: list[PromptStrategy] = []

    if not schema:
        return matches

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

    return matches


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
    if not matches:
        matches = _match_by_schema_and_examples(registry, schema, examples, inputs)

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
