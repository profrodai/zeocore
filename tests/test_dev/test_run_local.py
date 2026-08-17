"""
Tests for quack_core._dev.run_local (0% covered before RULING-277 Bug 1's
fix, and previously an ImportError-pinning test for the bug this ruling
authorized fixing).

This is a DEV-ONLY manual orchestrator script (module docstring: "Use this
to test chains of capabilities without spinning up n8n") -- but the
coverage gate does not exempt _dev/ (checked pyproject.toml: only
"tests/*" is omitted), so it counts.

FORMER BUG (RULING-277 Bug 1, fixed): quack_core/_dev/run_local.py line 16
used to do `from quack_core.contracts.capabilities.demo import EchoRequest,
echo_text`, but quack_core/contracts/capabilities/demo/__init__.py's own
docstring says, verbatim: "NOTE: Demo implementations are NOT exported from
this module... See _impl.py for reference implementations." echo_text was
never re-exported, so the module was 100 percent unimportable. RULING-277
authorized importing echo_text from
quack_core.contracts.capabilities.demo._impl directly instead, matching
that docstring's own "for reference/testing only" carve-out for a
_dev/-only script. This file now exercises the fixed, real import and
run_flow() successfully, replacing the prior ImportError-pinning test per
that test's own instruction.
"""


class TestRunLocalModule:
    def test_module_imports_successfully(self) -> None:
        """RULING-277 Bug 1 regression: the module must import cleanly now
        that echo_text is pulled from its true (_impl) location."""
        import importlib

        import quack_core._dev.run_local as run_local_module

        importlib.reload(run_local_module)
        assert hasattr(run_local_module, "run_flow")

    def test_run_flow_executes_successfully(self) -> None:
        """The module's own run_flow() -- previously unreachable -- now
        runs end to end against the real (unmocked) echo_text
        implementation, exercising all three of its steps."""
        from quack_core._dev.run_local import run_flow

        run_flow()

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
