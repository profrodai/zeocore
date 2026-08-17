"""
Smoke test for the zeo_core.prompt package's public import surface.

Per RULING-118 s2: this is NOT a rewrite of the retired test_prompt/ suite (the old
suite asserted behavior of a module-level global registry, `PromptBooster`, and a
five-function `enhancer` API that commit 175956c8 deleted outright in Dec 2025, with
zero current consumers anywhere in the tree to protect). This is the floor beneath
"the module at least imports and constructs" -- so if `zeo_core.prompt` is itself
replaced again before ever being consumed, the next reader has one file telling them
what broke, not zero.
"""

from zeo_core.prompt import (
    PromptService,
    PromptStrategy,
    StrategyInfo,
    create_default_prompt_service,
)


def test_prompt_public_surface_imports() -> None:
    """The package's documented public names import without error."""
    assert PromptService is not None
    assert PromptStrategy is not None
    assert StrategyInfo is not None
    assert create_default_prompt_service is not None


def test_create_default_prompt_service_constructs() -> None:
    """The default factory constructs a PromptService without raising."""
    service = create_default_prompt_service()
    assert isinstance(service, PromptService)
