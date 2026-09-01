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


def test_package_identity_the_shipped_artifact_must_agree_with_its_own_metadata() -> (
    None
):
    """THE PACKAGE MUST KNOW WHAT VERSION IT IS. If this is red, DO NOT SHIP.

    Deliberately not named like a `test_version_*` handling test: `pytest -k
    version` currently collects 60+ OTHER tests that exercise version
    *parsing/comparison/handling* logic and pass cleanly regardless of this
    defect. NONE of them test version *identity* -- whether the running
    package's own __version__ agrees with the metadata of the distribution
    it was actually installed/published as. That distinction was invisible
    from a green suite, which is exactly why real PyPI 0.4.0 is LIVE, RIGHT
    NOW, shipping `zeo_core.__version__ == "0.3.0"` (confirmed by installing
    it from the index and importing it) -- and TestPyPI 0.6.0 shipped
    `__version__ == "0.5.0"`. Both releases passed `make verify`'s full
    eight-stage gate. This is the one test that would have caught either.

    RULING-414 (zeocore org corpus, 2026-09-01): `src/zeo_core/__init__.py`
    hardcoded `__version__` as a literal that drifted silently from
    `pyproject.toml`'s `[project] version` because nothing tied them
    together. Confirmed red against UNMODIFIED trunk before the fix
    (zeocore@6f271337: `__version__ = "0.5.0"` vs installed metadata
    `0.6.0"` -- `AssertionError: assert '0.5.0' == '0.6.0'`), then fixed by
    deriving `__version__` from `importlib.metadata.version("zeocore")`
    (RULING-415 §0 item 2: derive, don't hand-maintain a literal beside a
    test) so there is exactly one source of truth left to edit.

    This is a *behavioral* check, not a presence check: it asserts the two
    values are EQUAL, not merely that `__version__` exists or is importable
    (a `hasattr`/`import` check would have passed on 0.3.0/0.4.0/0.5.0/0.6.0
    identically -- presence was never the gap).
    """
    assert zeo_core.__version__ == importlib.metadata.version("zeocore"), (
        f"PACKAGE IDENTITY MISMATCH, DO NOT SHIP: zeo_core.__version__ "
        f"({zeo_core.__version__!r}) does not match the installed "
        f"distribution's own metadata "
        f"({importlib.metadata.version('zeocore')!r}). This is the exact "
        "RULING-414 defect (real PyPI 0.4.0 is live today reporting "
        "__version__ '0.3.0'). Fix: __version__ must be derived from "
        "importlib.metadata.version('zeocore') in src/zeo_core/__init__.py, "
        "never a hand-maintained literal."
    )
