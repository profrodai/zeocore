# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_tools/mixins/test_env_init.py
# === QV-LLM:END ===

"""
Tests for the ToolEnvInitializerMixin.

NOTE: this file previously tested a pre-doctrine shape of this mixin --
a `_initialize_environment(tool_name: str)` method that dynamically
`importlib.import_module`'d a tool's own module and called its module-level
`initialize()` hook, returning an `IntegrationResult`. That method and that
whole "dynamic module init hook" behavior do not exist anywhere in the
current `quack_core.tools.mixins.env_init.ToolEnvInitializerMixin` (read in
full from src/ before writing this file): the current mixin's public method
is `initialize_environment(ctx: ToolContext) -> CapabilityResult[None]`, and
it does something entirely different -- strict validation that `ctx.work_dir`
/`ctx.output_dir` exist and are directories, via `ctx.require_fs().
get_file_info(path)`. This is a redesign, not a rename: the old behavior has
no current equivalent to "rework a method name onto," so every test in this
file below exercises the real current method with its real current
signature and real current contract objects (CapabilityResult/
CapabilityStatus, FileInfoResult), rather than assuming a mechanical rename
of `_initialize_environment` -> `initialize_environment` would still make
sense against the old assertions (it would not -- the old assertions target
IntegrationResult.success/.message and importlib patching, neither of which
this method touches at all).

RESTAUFWAND (named here, not fixed -- out of this stream's charter to touch
src/): `_normalize_fs_result()`'s MIGRATION COMPAT fallback reads
`getattr(result, "data", None)` then `getattr(result, "value", None)` to
populate `info`, but the real return type of `fs.get_file_info()` is
`FileInfoResult` (quack_core.core.fs.results), which carries `.exists`/
`.is_dir` directly on itself and has neither a `.data` nor a `.value`
attribute anywhere in its class hierarchy (only the unrelated `DataResult`
subclass has `.data`). Confirmed behaviorally: constructing a real, valid,
existing-directory `FileInfoResult(ok=True, exists=True, is_dir=True, ...)`
and passing it through `_validate_directory` still fails with "FS returned
no info for <name> directory" -- `initialize_environment()` can never
succeed against a real `fs.get_file_info()` call, for ANY directory state,
existing or missing. This looks like a genuine source bug (`info` should
most likely just be `result` itself, not `result.data`), not a test-staleness
issue -- but fixing mixins/env_init.py's source is outside this stream's
five-file test-only charter (RULING-226 SS3), so it is named here rather
than silently fixed or silently glossed over. The tests below assert the
REAL current behavior, bug included: a valid, existing, real-shaped
FileInfoResult still yields a `CapabilityStatus.error` result. Whoever picks
up this restaufwand item can flip that one assertion once the source bug is
fixed.
"""

import unittest
from unittest.mock import MagicMock

import pytest
from quack_core.contracts.common.enums import CapabilityStatus
from quack_core.core.fs.results import FileInfoResult
from quack_core.tools.context import ToolContext
from quack_core.tools.mixins.env_init import ToolEnvInitializerMixin


def _make_tool_context(fs: MagicMock) -> ToolContext:
    """Build a minimal valid ToolContext wrapping the given mock fs service."""
    return ToolContext(
        run_id="test-run-id",
        tool_name="test-tool",
        tool_version="0.0.0",
        logger=None,
        fs=fs,
        work_dir="/tmp/work",  # noqa: S108 -- path only used inside a pydantic model construction, never touches real filesystem
        output_dir="/tmp/output",  # noqa: S108 -- path only used inside a pydantic model construction, never touches real filesystem
    )


class TestToolEnvInitializerMixin(unittest.TestCase):
    """
    Test cases for ToolEnvInitializerMixin using unittest.
    """

    def setUp(self) -> None:
        self.mixin = ToolEnvInitializerMixin()

    def test_initialize_environment_real_fileinforesult_still_errors(self) -> None:
        """
        Documents the current (buggy) real-contract behavior: even a valid,
        existing, real-shaped FileInfoResult trips the .data/.value
        MIGRATION COMPAT fallback (see module docstring RESTAUFWAND) and
        yields an error, not success.
        """
        fs = MagicMock()
        fs.get_file_info.return_value = FileInfoResult(
            ok=True,
            exists=True,
            is_dir=True,
            path="/tmp/work",  # noqa: S108
        )
        ctx = _make_tool_context(fs)

        result = self.mixin.initialize_environment(ctx)

        self.assertEqual(result.status, CapabilityStatus.error)
        self.assertIn("FS returned no info", result.human_message)
        fs.get_file_info.assert_called_with("/tmp/work")  # noqa: S108

    def test_initialize_environment_missing_directory(self) -> None:
        """A FileInfoResult reporting exists=False also surfaces as an error
        (currently masked by the same .data/.value fallback -- the 'no info'
        message fires before the exists check is ever reached)."""
        fs = MagicMock()
        fs.get_file_info.return_value = FileInfoResult(
            ok=True,
            exists=False,
            is_dir=False,
            path="/tmp/work",  # noqa: S108
        )
        ctx = _make_tool_context(fs)

        result = self.mixin.initialize_environment(ctx)

        self.assertEqual(result.status, CapabilityStatus.error)

    def test_initialize_environment_fs_raises(self) -> None:
        """A raising fs.get_file_info is caught and reported as validation failure."""
        fs = MagicMock()
        fs.get_file_info.side_effect = Exception("boom")
        ctx = _make_tool_context(fs)

        result = self.mixin.initialize_environment(ctx)

        self.assertEqual(result.status, CapabilityStatus.error)
        self.assertIn("Environment validation failed", result.human_message)

    def test_initialize_environment_empty_dirs_skips_validation(self) -> None:
        """Falsy work_dir/output_dir short-circuit validation entirely (no fs
        call at all) and the overall result is success."""
        fs = MagicMock()
        ctx = ToolContext(
            run_id="test-run-id",
            tool_name="test-tool",
            tool_version="0.0.0",
            logger=None,
            fs=fs,
            work_dir="",
            output_dir="",
        )

        result = self.mixin.initialize_environment(ctx)

        self.assertEqual(result.status, CapabilityStatus.success)
        fs.get_file_info.assert_not_called()

    def test_validate_directory_missing_exists_attribute_reports_contract_breach(
        self,
    ) -> None:
        """A result missing .exists entirely (once past the .data/.value
        fallback) is reported as a distinct FS-contract-breach error, not
        conflated with a generic failure."""
        fs = MagicMock()
        bare_result = MagicMock(spec=["success", "data"])
        bare_result.success = True
        bare_result.data = MagicMock(spec=[])  # no .exists at all
        fs.get_file_info.return_value = bare_result
        ctx = _make_tool_context(fs)

        result = self.mixin.initialize_environment(ctx)

        self.assertEqual(result.status, CapabilityStatus.error)
        self.assertIn("FileInfo missing 'exists' attribute", result.human_message)


# Pytest-style tests


@pytest.fixture
def tool_env_initializer_mixin() -> ToolEnvInitializerMixin:
    """Fixture that creates a ToolEnvInitializerMixin."""
    return ToolEnvInitializerMixin()


class TestToolEnvInitializerMixinWithPytest:
    """
    Test cases for ToolEnvInitializerMixin using pytest fixtures.
    """

    def test_initialize_environment_real_fileinforesult_still_errors_pytest(
        self, tool_env_initializer_mixin: ToolEnvInitializerMixin
    ) -> None:
        """Pytest-style mirror of the unittest real-contract case above."""
        fs = MagicMock()
        fs.get_file_info.return_value = FileInfoResult(
            ok=True,
            exists=True,
            is_dir=True,
            path="/tmp/work",  # noqa: S108
        )
        ctx = _make_tool_context(fs)

        result = tool_env_initializer_mixin.initialize_environment(ctx)

        assert result.status == CapabilityStatus.error
        assert "FS returned no info" in result.human_message

    def test_initialize_environment_fs_raises_pytest(
        self, tool_env_initializer_mixin: ToolEnvInitializerMixin
    ) -> None:
        """Pytest-style mirror of the exception-handling case above."""
        fs = MagicMock()
        fs.get_file_info.side_effect = Exception("boom")
        ctx = _make_tool_context(fs)

        result = tool_env_initializer_mixin.initialize_environment(ctx)

        assert result.status == CapabilityStatus.error
        assert "Environment validation failed" in result.human_message

    def test_initialize_environment_empty_dirs_skips_validation_pytest(
        self, tool_env_initializer_mixin: ToolEnvInitializerMixin
    ) -> None:
        """Pytest-style mirror of the empty-dirs short-circuit case above."""
        fs = MagicMock()
        ctx = ToolContext(
            run_id="test-run-id",
            tool_name="test-tool",
            tool_version="0.0.0",
            logger=None,
            fs=fs,
            work_dir="",
            output_dir="",
        )

        result = tool_env_initializer_mixin.initialize_environment(ctx)

        assert result.status == CapabilityStatus.success
        fs.get_file_info.assert_not_called()


if __name__ == "__main__":
    unittest.main()
