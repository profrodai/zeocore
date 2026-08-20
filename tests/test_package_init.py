"""
Tests for zeo_core's top-level package __init__.py re-exports.

Regression coverage for the zeocore-dx-audit-SOW-1 finding: dir(zeo_core)
only showed the zeo_core.tools surface (BaseZeoTool, ToolContext, mixins)
and not CapabilityResult, even though every example's run() signature
depends on it and README.md's module table presents contracts as an
equally discoverable top-level module.
"""

import zeo_core


def test_capability_result_reachable_from_top_level() -> None:
    """CapabilityResult must be importable as `from zeo_core import CapabilityResult`.

    Previously only reachable via `from zeo_core.contracts import
    CapabilityResult` -- every example did this correctly, but nothing at
    the top level signaled the split to an agent relying on
    dir()/autocomplete introspection.
    """
    assert hasattr(zeo_core, "CapabilityResult")
    assert "CapabilityResult" in zeo_core.__all__

    result = zeo_core.CapabilityResult.ok(data={"x": 1}, msg="ok")
    assert result.status.value == "success"


def test_tools_surface_still_reachable_from_top_level() -> None:
    """The pre-existing tools re-exports must not regress."""
    for name in (
        "BaseZeoTool",
        "ToolContext",
        "ZeoToolProtocol",
        "IntegrationEnabledMixin",
        "LifecycleMixin",
        "ToolEnvInitializerMixin",
    ):
        assert hasattr(zeo_core, name), f"zeo_core.{name} should be re-exported"
        assert name in zeo_core.__all__


def test_all_matches_actual_attributes() -> None:
    """Every name in __all__ must actually resolve on the module."""
    for name in zeo_core.__all__:
        assert hasattr(zeo_core, name)
