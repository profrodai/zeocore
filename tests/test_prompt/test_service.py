"""
Tests for zeo_core.prompt.service.PromptService.

PromptService is the orchestration layer tying together the strategy
registry, selector, and (optional) LLM-based enhancement. Per RULING-235,
these tests exercise the real registry/selector/strategy machinery directly
-- the only mocked boundary is the LLM enhancement call itself
(zeo_core.prompt._internal.enhancer.enhance_with_llm_safe), which crosses
into an external LLM-provider SDK boundary (network calls, API keys).
"""

from unittest.mock import patch

import pytest

from zeo_core.prompt.models import PromptStrategy
from zeo_core.prompt.service import PromptService

# --- __init__ / load_pack ---


def test_init_with_defaults_loads_internal_pack() -> None:
    service = PromptService(load_defaults=True)
    listing = service.list_strategies()
    assert listing.success is True
    assert len(listing.strategies) == 28


def test_init_without_defaults_has_empty_registry() -> None:
    service = PromptService(load_defaults=False)
    listing = service.list_strategies()
    assert listing.success is True
    assert listing.strategies == []


def test_load_pack_internal_explicit_call_returns_loaded_count() -> None:
    service = PromptService(load_defaults=False)
    result = service.load_pack("internal")
    assert result.success is True
    assert result.loaded_count == 28


def test_load_pack_unknown_pack_name() -> None:
    service = PromptService(load_defaults=False)
    result = service.load_pack("does-not-exist")
    assert result.success is False
    assert result.error == "Unknown pack: does-not-exist"


def test_load_pack_internal_twice_still_reports_success_but_zero_new() -> None:
    """
    load() in packs/internal/__init__.py swallows ValueError (duplicate ID) per
    strategy and just doesn't count it -- so re-loading "internal" into a
    registry that already has it succeeds with loaded_count == 0, not an error.
    """
    service = PromptService(load_defaults=True)
    result = service.load_pack("internal")
    assert result.success is True
    assert result.loaded_count == 0


def test_load_pack_exception_path_returns_failure() -> None:
    """
    Force the `except Exception` branch in load_pack by making the internal
    loader explode. This crosses into an internal-import failure path,
    which we simulate the only way possible: patching the dynamically-imported
    `load` symbol's module attribute so the real code's `import` + call raises.
    """
    service = PromptService(load_defaults=False)
    with patch(
        "zeo_core.prompt.packs.internal.load",
        side_effect=RuntimeError("boom"),
    ):
        result = service.load_pack("internal")
    assert result.success is False
    assert result.error == "boom"


# --- register_strategy ---


def _make_strategy(strategy_id: str = "custom-strategy") -> PromptStrategy:
    def render_fn(task_description: str) -> str:
        return f"CUSTOM: {task_description}"

    return PromptStrategy(
        id=strategy_id,
        label="Custom",
        description="A custom test strategy",
        input_vars=["task_description"],
        render_fn=render_fn,
        tags=["custom"],
    )


def test_register_strategy_success() -> None:
    service = PromptService(load_defaults=False)
    result = service.register_strategy(_make_strategy())
    assert result.success is True
    assert result.strategy_id == "custom-strategy"
    fetched = service.get_strategy("custom-strategy")
    assert fetched.success is True
    assert fetched.strategy is not None
    assert fetched.strategy.id == "custom-strategy"


def test_register_strategy_duplicate_id_fails() -> None:
    service = PromptService(load_defaults=False)
    service.register_strategy(_make_strategy())
    result = service.register_strategy(_make_strategy())
    assert result.success is False
    assert result.error is not None
    assert "already exists" in result.error


def test_register_strategy_unexpected_exception_path() -> None:
    """
    Exercises the generic `except Exception` branch (distinct from the
    ValueError branch) in register_strategy by making the registry's
    register() raise something other than ValueError.
    """
    service = PromptService(load_defaults=False)
    with patch.object(
        service._registry, "register", side_effect=RuntimeError("registry exploded")
    ):
        result = service.register_strategy(_make_strategy())
    assert result.success is False
    assert result.error == "registry exploded"


# --- get_strategy ---


def test_get_strategy_not_found() -> None:
    service = PromptService(load_defaults=False)
    result = service.get_strategy("nonexistent")
    assert result.success is False
    assert result.error == "Strategy 'nonexistent' not found"
    assert result.strategy is None


def test_get_strategy_found() -> None:
    service = PromptService(load_defaults=True)
    result = service.get_strategy("zero-shot-prompting")
    assert result.success is True
    assert result.strategy is not None
    assert result.strategy.id == "zero-shot-prompting"


# --- list_strategies ---


def test_list_strategies_returns_strategy_info_objects() -> None:
    service = PromptService(load_defaults=True)
    result = service.list_strategies()
    assert result.success is True
    ids = {s.id for s in result.strategies}
    assert "zero-shot-prompting" in ids
    # StrategyInfo should not carry the render_fn callable.
    assert not hasattr(result.strategies[0], "render_fn")


# --- render() ---


def test_render_with_explicit_strategy_id() -> None:
    service = PromptService(load_defaults=True)
    result = service.render(
        "Summarize this document", strategy_id="zero-shot-prompting"
    )
    assert result.success is True
    assert result.prompt == "Summarize this document"
    assert result.strategy_id == "zero-shot-prompting"
    assert result.strategy_label == "Zero-shot Prompting"
    assert result.estimated_words == 3
    assert result.metadata["strategy_id"] == "zero-shot-prompting"
    assert result.metadata["input_vars"] == ["task_description"]


def test_render_with_unknown_explicit_strategy_id_fails() -> None:
    service = PromptService(load_defaults=True)
    result = service.render("Do something", strategy_id="not-a-real-strategy")
    assert result.success is False
    assert result.error == "Strategy 'not-a-real-strategy' not found"


def test_render_with_no_strategy_id_uses_selector_default() -> None:
    """No tags/schema/examples -> selector falls back to zero-shot-prompting."""
    service = PromptService(load_defaults=True)
    result = service.render("Just do the task")
    assert result.success is True
    assert result.strategy_id == "zero-shot-prompting"
    assert result.prompt == "Just do the task"


def test_render_with_schema_and_multiple_examples_selects_multi_shot() -> None:
    service = PromptService(load_defaults=True)
    result = service.render(
        "Extract entities",
        schema="{type: object}",
        examples=["ex1", "ex2"],
    )
    assert result.success is True
    assert result.strategy_id == "multi-shot-structured"
    assert result.prompt is not None
    assert "ex1\n\nex2" in result.prompt


def test_render_with_schema_and_single_example_selects_single_shot() -> None:
    service = PromptService(load_defaults=True)
    result = service.render(
        "Extract entities",
        schema="{type: object}",
        examples=["only-one"],
    )
    assert result.success is True
    assert result.strategy_id == "single-shot-structured"
    # The service derives `example` (singular) from examples[0] for
    # single-shot-structured's `example` input var.
    assert result.prompt is not None
    assert "only-one" in result.prompt


def test_render_with_tags_selects_matching_strategy() -> None:
    service = PromptService(load_defaults=True)
    # code-prompting's sole input var is "code_task_description" (not the
    # standard "task_description" alias), so it must be passed as a kwarg.
    result = service.render(
        "Write a login function",
        tags=["code", "generation"],
        code_task_description="Write a login function",
    )
    assert result.success is True
    assert result.strategy_id == "code-prompting"


def test_render_no_strategy_found_when_registry_empty() -> None:
    service = PromptService(load_defaults=False)
    result = service.render("Do something")
    assert result.success is False
    assert result.error == "No suitable strategy found and no defaults available."


def test_render_missing_required_inputs_reports_missing_fields() -> None:
    service = PromptService(load_defaults=True)
    # role-prompting needs "role" and "task_description"; we don't supply "role".
    result = service.render("Review this PR", strategy_id="role-prompting")
    assert result.success is False
    assert result.error is not None
    assert "Missing required inputs for strategy 'role-prompting'" in result.error
    assert "role" in result.error


def test_render_passes_through_kwargs_for_dynamic_inputs() -> None:
    service = PromptService(load_defaults=True)
    result = service.render(
        "Assist the user",
        strategy_id="role-prompting",
        role="senior engineer",
    )
    assert result.success is True
    assert result.prompt is not None
    assert "senior engineer" in result.prompt
    assert "Assist the user" in result.prompt


def test_render_estimated_words_zero_for_empty_prompt() -> None:
    service = PromptService(load_defaults=True)
    result = service.render("", strategy_id="zero-shot-prompting")
    assert result.success is True
    assert result.prompt == ""
    assert result.estimated_words == 0


def test_render_unexpected_exception_is_caught_and_reported() -> None:
    """
    Forces a strategy whose render_fn raises, to exercise the outer
    try/except in render() (lines 183-185).
    """

    def exploding_render(task_description: str) -> str:
        raise RuntimeError("render exploded")

    service = PromptService(load_defaults=False)
    service.register_strategy(
        PromptStrategy(
            id="exploding",
            label="Exploding",
            description="Always raises",
            input_vars=["task_description"],
            render_fn=exploding_render,
        )
    )
    result = service.render("anything", strategy_id="exploding")
    assert result.success is False
    assert result.error == "render exploded"


def test_render_with_use_llm_true_calls_enhancer_and_sets_metadata() -> None:
    """
    Mocks only the external-SDK-adjacent enhancer boundary
    (enhance_with_llm_safe), not any internal zeo_core prompt logic.
    """
    service = PromptService(load_defaults=True)
    with patch(
        "zeo_core.prompt.service.enhance_with_llm_safe",
        return_value="ENHANCED PROMPT",
    ) as mock_enhance:
        result = service.render(
            "Summarize this",
            strategy_id="zero-shot-prompting",
            use_llm=True,
            llm_model="some-model",
            llm_provider="some-provider",
        )
    assert result.success is True
    assert result.prompt == "ENHANCED PROMPT"
    assert result.metadata["enhanced_by_llm"] is True
    mock_enhance.assert_called_once_with(
        "Summarize this", model="some-model", provider="some-provider"
    )


def test_render_with_use_llm_false_does_not_call_enhancer() -> None:
    service = PromptService(load_defaults=True)
    with patch("zeo_core.prompt.service.enhance_with_llm_safe") as mock_enhance:
        result = service.render(
            "Summarize this", strategy_id="zero-shot-prompting", use_llm=False
        )
    assert result.success is True
    mock_enhance.assert_not_called()
    assert "enhanced_by_llm" not in result.metadata


def test_render_use_llm_real_unmocked_call_falls_back_without_api_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Real (unmocked) end-to-end call through enhance_with_llm_safe with
    use_llm=True. With no LLM provider API keys configured,
    LLMIntegration.initialize() genuinely fails and enhance_with_llm_safe
    falls back to returning the original prompt unchanged -- this is real
    production behavior, not a mock. Other tests (or leaked global state
    from the wider suite) may set provider credentials in os.environ, so
    explicitly clear them here to make this deterministic.
    """
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_ORGANIZATION",
    ):
        monkeypatch.delenv(key, raising=False)

    service = PromptService(load_defaults=True)
    result = service.render(
        "Summarize this", strategy_id="zero-shot-prompting", use_llm=True
    )
    assert result.success is True
    # Falls back to the original rendered prompt since the LLM could not init.
    assert result.prompt == "Summarize this"
    assert result.metadata["enhanced_by_llm"] is True
