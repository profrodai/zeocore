# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_dev/test_run_local.py
# === QV-LLM:END ===

"""
Tests for quack_core._dev.run_local (0% covered before this file, and
PINS A REAL PRODUCTION BUG -- the module is currently unimportable).

This is a DEV-ONLY manual orchestrator script (module docstring: "Use this
to test chains of capabilities without spinning up n8n") -- but the
coverage gate does not exempt _dev/ (checked pyproject.toml: only
"tests/*" is omitted), so it counts, and being "dev-only" doesn't make a
broken import acceptable.

BUG (found writing this coverage pass, NOT fixed here -- a ruling must
authorize any production fix, per this stream's charter):

quack_core/_dev/run_local.py line 16 does:
    from quack_core.contracts.capabilities.demo import EchoRequest, echo_text

But quack_core/contracts/capabilities/demo/__init__.py's own docstring
says, verbatim: "NOTE: Demo implementations are NOT exported from this
module. They are internal examples only[...] See _impl.py for reference
implementations (prefixed with _ to mark as internal)." Its __all__ is
literally `["EchoRequest", "VideoRefRequest"]` -- models only. echo_text
lives in demo/_impl.py, never re-exported from demo/__init__.py.

Effect: `import quack_core._dev.run_local` raises ImportError immediately
(verified directly, unmocked):
    >>> from quack_core._dev.run_local import run_flow
    ImportError: cannot import name 'echo_text' from
    'quack_core.contracts.capabilities.demo'

The module's own run_flow() can never execute -- this script is currently
100 percent broken, not merely uncovered. The likely correct fix (not
applied here) is importing echo_text from
quack_core.contracts.capabilities.demo._impl instead of the package's
public __init__, matching the "DO NOT export implementations" contract
the package itself documents.
"""

import pytest


class TestRunLocalModuleImportBug:
    def test_module_import_raises_import_error_BUG(self) -> None:
        """PINS the current (broken) behavior. Once a ruling authorizes
        fixing run_local.py's import to pull echo_text from
        quack_core.contracts.capabilities.demo._impl (matching the
        package's own documented "implementations are not exported"
        contract), this test must be replaced with one that imports and
        exercises run_flow() successfully -- not left passing on a
        now-stale ImportError."""
        with pytest.raises(ImportError, match="echo_text"):
            import importlib

            import quack_core._dev.run_local as run_local_module

            importlib.reload(run_local_module)

    def test_the_underlying_implementation_the_script_wants_to_call_does_work(
        self,
    ) -> None:
        """Confirms the import bug is purely a path mistake in
        run_local.py, not a deeper break in the demo capability itself --
        calling echo_text via its real (private, _impl) location works
        fine end to end, which is exactly what run_flow() would do if its
        import were corrected.

        Note: echo_text does NOT actually validate `preset` against any
        known list -- it accepts any string and echoes it back in
        metadata (see _impl.py:48-54). run_local.py's own Step 3 comment
        ("Expect Error") for an unrecognized preset name does not match
        this. That is a separate, second-order documentation/expectation
        mismatch inside the same broken, currently-unreachable script --
        recorded here for completeness, not separately pinned as its own
        bug, since the script cannot run at all regardless."""
        from quack_core.contracts.capabilities.demo._impl import echo_text
        from quack_core.contracts.capabilities.demo.models import EchoRequest

        result = echo_text(EchoRequest(text="World"))
        assert result.status.value == "success"
        assert result.data == "Hello World"

        # An "invalid" preset name is accepted as-is, not rejected --
        # echo_text has no preset validation/lookup at all.
        result_unknown_preset = echo_text(
            EchoRequest(text="World", preset="missing_preset")
        )
        assert result_unknown_preset.status.value == "success"
        assert result_unknown_preset.metadata["used_preset"] == "missing_preset"
