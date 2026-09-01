"""
Tests for zeo_core's top-level package __init__.py re-exports.

Regression coverage for the zeocore-dx-audit-SOW-1 finding: dir(zeo_core)
only showed the zeo_core.tools surface (BaseZeoTool, ToolContext, mixins)
and not CapabilityResult, even though every example's run() signature
depends on it and README.md's module table presents contracts as an
equally discoverable top-level module.

Also covers RULING-414: the published package misreported its own version
for three releases running (real PyPI 0.4.0 shipped __version__ == "0.3.0";
TestPyPI 0.6.0 shipped __version__ == "0.5.0") because __version__ was a
hand-maintained literal with nothing asserting it matched the distribution
that was actually built and published. `grep -rl __version__ tests/`
returned zero files before this test existed.
"""

import importlib.metadata

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


def test_version_matches_installed_distribution_metadata() -> None:
    """zeo_core.__version__ must agree with the installed distribution's version.

    RULING-414: real PyPI 0.4.0 shipped `zeo_core.__version__ == "0.3.0"`, and
    TestPyPI 0.6.0 shipped `zeo_core.__version__ == "0.5.0"` -- a hardcoded
    literal in src/zeo_core/__init__.py that drifted from pyproject.toml's
    `[project] version` because nothing tied them together and nothing
    tested it. `__version__` is now derived from
    `importlib.metadata.version("zeocore")` (the same value hatchling/pip
    publish as the distribution's version), so there is exactly one place
    left to edit and this test is what makes a re-introduced literal fail
    instead of silently shipping.

    This is a *behavioral* check, not a presence check: it asserts the two
    values are equal, not merely that `__version__` exists or is importable
    (a `hasattr`/`import` check would have passed on 0.4.0/0.6.0 too).
    """
    assert zeo_core.__version__ == importlib.metadata.version("zeocore")
