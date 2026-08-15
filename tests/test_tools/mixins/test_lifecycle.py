# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_tools/mixins/test_lifecycle.py
# role: tests
# neighbors: __init__.py, test_env_init.py, test_integration_enabled.py (+1 more)
# exports: TestLifecycleMixin, TestLifecycleMixinWithPytest, lifecycle_mixin,
#   tool_context
# git_branch: main
# git_commit: dd3d8757
# === QV-LLM:END ===

"""
Tests for the LifecycleMixin (aliased QuackToolLifecycleMixin).

NOTE: this file previously tested a pre-doctrine shape of this mixin --
no-arg pre_run()/post_run()/validate(), plus run()/upload() methods and an
IntegrationResult(.success/.message) return type. None of that shape has
existed on quack_core.tools.mixins.lifecycle.LifecycleMixin since the module
was introduced into this history (commit 21a4e25a, 2025-12-29) -- the test
file itself was added earlier (commit 59e3eb9a, 2025-04-26, "adding tests to
quackcore.toolkit") and was never reconciled against the doctrine-compliant
rewrite. These tests were unreachable (masked by conftest.py's
OutputFormatMixin collection-abort) until a prior stream fixed that collection
break, at which point they surfaced as 16 failures -- confirmed pre-existing,
not a regression. Rewritten here to match the CURRENT mixin: pre_run/post_run/
validate take (request, ctx) [post_run also takes result], return
CapabilityResult (status=CapabilityStatus.success, human_message=...), and
there is no run() or upload() method on this mixin at all (run() lives on
BaseQuackTool per this mixin's own docstring; there is no upload hook).
"""

import unittest

import pytest
from quack_core.contracts import CapabilityResult
from quack_core.contracts.common.enums import CapabilityStatus
from quack_core.tools.context import ToolContext
from quack_core.tools.mixins.lifecycle import QuackToolLifecycleMixin


def _make_tool_context() -> ToolContext:
    """Build a minimal valid ToolContext for exercising lifecycle hooks."""
    return ToolContext(
        run_id="test-run-id",
        tool_name="test-tool",
        tool_version="0.0.0",
        logger=None,
        fs=None,
        work_dir="/tmp/work",  # noqa: S108 -- path used only inside a pydantic model construction, never touches real filesystem
        output_dir="/tmp/output",  # noqa: S108 -- path used only inside a pydantic model construction, never touches real filesystem
    )


class TestLifecycleMixin(unittest.TestCase):
    """
    Test cases for LifecycleMixin using unittest.
    """

    def setUp(self) -> None:
        """
        Set up test fixtures.
        """
        self.mixin = QuackToolLifecycleMixin()
        self.ctx = _make_tool_context()

    def test_pre_run(self) -> None:
        """
        Test that pre_run returns a success result.
        """
        result = self.mixin.pre_run(request=None, ctx=self.ctx)
        self.assertEqual(result.status, CapabilityStatus.success)
        self.assertIn("Pre-run", result.human_message)

    def test_post_run(self) -> None:
        """
        Test that post_run passes the inner result through unchanged.
        """
        inner = CapabilityResult.ok(data=None, msg="Run completed")
        result = self.mixin.post_run(request=None, result=inner, ctx=self.ctx)
        self.assertIs(result, inner)
        self.assertEqual(result.status, CapabilityStatus.success)

    def test_validate(self) -> None:
        """
        Test that validate returns a success result.
        """
        result = self.mixin.validate(request=None, ctx=self.ctx)
        self.assertEqual(result.status, CapabilityStatus.success)
        self.assertIn("Validation", result.human_message)

    def test_cleanup(self) -> None:
        """
        Test that cleanup returns a success result.
        """
        result = self.mixin.cleanup(ctx=self.ctx)
        self.assertEqual(result.status, CapabilityStatus.success)
        self.assertIn("Cleanup", result.human_message)


# Pytest-style tests


@pytest.fixture
def lifecycle_mixin() -> QuackToolLifecycleMixin:
    """Fixture that creates a QuackToolLifecycleMixin."""
    return QuackToolLifecycleMixin()


@pytest.fixture
def tool_context() -> ToolContext:
    """Fixture that creates a minimal valid ToolContext."""
    return _make_tool_context()


class TestLifecycleMixinWithPytest:
    """
    Test cases for LifecycleMixin using pytest fixtures.
    """

    def test_lifecycle_pre_run(
        self, lifecycle_mixin: QuackToolLifecycleMixin, tool_context: ToolContext
    ) -> None:
        """Test pre_run with pytest fixtures."""
        result = lifecycle_mixin.pre_run(request=None, ctx=tool_context)
        assert result.status == CapabilityStatus.success
        assert "Pre-run" in result.human_message

    def test_lifecycle_post_run(
        self, lifecycle_mixin: QuackToolLifecycleMixin, tool_context: ToolContext
    ) -> None:
        """Test post_run with pytest fixtures passes the inner result through."""
        inner = CapabilityResult.ok(data=None, msg="Run completed")
        result = lifecycle_mixin.post_run(request=None, result=inner, ctx=tool_context)
        assert result is inner
        assert result.status == CapabilityStatus.success

    def test_lifecycle_validate(
        self, lifecycle_mixin: QuackToolLifecycleMixin, tool_context: ToolContext
    ) -> None:
        """Test validate method with pytest fixtures."""
        result = lifecycle_mixin.validate(request=None, ctx=tool_context)
        assert result.status == CapabilityStatus.success
        assert "Validation" in result.human_message

    def test_lifecycle_cleanup(
        self, lifecycle_mixin: QuackToolLifecycleMixin, tool_context: ToolContext
    ) -> None:
        """Test cleanup method with pytest fixtures."""
        result = lifecycle_mixin.cleanup(ctx=tool_context)
        assert result.status == CapabilityStatus.success
        assert "Cleanup" in result.human_message
