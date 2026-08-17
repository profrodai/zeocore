"""
Tests for the IntegrationEnabledMixin.

NOTE: this file previously tested a pre-doctrine shape of this mixin --
Generic[T]-subscriptable, resolve_integration()/`.integration` property,
backed by module-level zeo_core.integrations.core.get_integration_service().
That shape does not exist on zeo_core.tools.mixins.integration_enabled.
IntegrationEnabledMixin in this codebase's current history: the module's own
docstring ("Services come from ToolContext.services (runner-provided)")
and its two methods (get_service/require_service, both taking an explicit
ctx: ToolContext) show a deliberate redesign, not a rename -- services are
now read from ToolContext.services rather than resolved from a global
registry, and the class is no longer Generic (collection previously aborted
here with `TypeError: type 'IntegrationEnabledMixin' is not subscriptable`).
Rewritten to exercise the mixin's actual current API: get_service(name, ctx,
expected_type=None) and require_service(name, ctx, expected_type=None),
both reading from ctx.services (confirmed via zeo_core.tools.context.
ToolContext.get_service/require_service, read in full before writing these
assertions).
"""

import unittest

import pytest
from zeo_core.tools.context import ToolContext
from zeo_core.tools.mixins.integration_enabled import IntegrationEnabledMixin


class _DummyService:
    """A minimal stand-in service object -- no BaseIntegrationService coupling
    is needed since the current mixin has no integration-service-specific
    behavior at all, it just reads arbitrary objects out of ctx.services."""

    def __init__(self, label: str) -> None:
        self.label = label


class _AnotherService:
    """A second, unrelated type -- used to exercise expected_type mismatches."""


def _make_tool_context(services: dict[str, object] | None = None) -> ToolContext:
    """Build a minimal valid ToolContext, optionally carrying services."""
    return ToolContext(
        run_id="test-run-id",
        tool_name="test-tool",
        tool_version="0.0.0",
        logger=None,
        fs=None,
        work_dir="/tmp/work",  # noqa: S108 -- path only used inside a pydantic model construction, never touches real filesystem
        output_dir="/tmp/output",  # noqa: S108 -- path only used inside a pydantic model construction, never touches real filesystem
        services=services or {},
    )


class MyTool(IntegrationEnabledMixin):
    """A trivial class combining the mixin, matching how tools actually use it."""


class TestIntegrationEnabledMixin(unittest.TestCase):
    """
    Test cases for IntegrationEnabledMixin using unittest.
    """

    def setUp(self) -> None:
        self.tool = MyTool()
        self.service = _DummyService("mock_service")
        self.ctx = _make_tool_context({"mock_service": self.service})

    def test_get_service_found(self) -> None:
        """get_service returns the service registered under that name."""
        result = self.tool.get_service("mock_service", self.ctx)
        self.assertIs(result, self.service)

    def test_get_service_missing_returns_none(self) -> None:
        """get_service returns None (does not raise) when the name isn't registered."""
        result = self.tool.get_service("absent_service", self.ctx)
        self.assertIsNone(result)

    def test_get_service_type_check_pass(self) -> None:
        """get_service returns the service when it matches expected_type."""
        result = self.tool.get_service(
            "mock_service", self.ctx, expected_type=_DummyService
        )
        self.assertIs(result, self.service)

    def test_get_service_type_check_fail(self) -> None:
        """get_service raises TypeError when the service doesn't match expected_type."""
        with self.assertRaises(TypeError):
            self.tool.get_service(
                "mock_service", self.ctx, expected_type=_AnotherService
            )

    def test_require_service_found(self) -> None:
        """require_service returns the service registered under that name."""
        result = self.tool.require_service("mock_service", self.ctx)
        self.assertIs(result, self.service)

    def test_require_service_missing_raises(self) -> None:
        """require_service raises ValueError (not None) when name isn't registered."""
        with self.assertRaises(ValueError):
            self.tool.require_service("absent_service", self.ctx)

    def test_require_service_type_check_fail(self) -> None:
        """require_service raises TypeError when the service type mismatches."""
        with self.assertRaises(TypeError):
            self.tool.require_service(
                "mock_service", self.ctx, expected_type=_AnotherService
            )


@pytest.fixture
def integration_enabled_tool() -> MyTool:
    """Fixture that creates a tool combining IntegrationEnabledMixin."""
    return MyTool()


class TestIntegrationEnabledMixinWithPytest:
    """
    Test cases for IntegrationEnabledMixin using pytest fixtures.
    """

    def test_get_service_resolves_from_context(
        self, integration_enabled_tool: MyTool
    ) -> None:
        """get_service reads the service straight out of ctx.services."""
        service = _DummyService("another_service")
        ctx = _make_tool_context({"another_service": service})

        result = integration_enabled_tool.get_service("another_service", ctx)

        assert result is service

    def test_require_service_resolves_from_context(
        self, integration_enabled_tool: MyTool
    ) -> None:
        """require_service reads the service straight out of ctx.services."""
        service = _DummyService("another_service")
        ctx = _make_tool_context({"another_service": service})

        result = integration_enabled_tool.require_service("another_service", ctx)

        assert result is service

    def test_get_service_no_services_registered(
        self, integration_enabled_tool: MyTool
    ) -> None:
        """get_service returns None against an empty services mapping."""
        ctx = _make_tool_context()

        result = integration_enabled_tool.get_service("anything", ctx)

        assert result is None


if __name__ == "__main__":
    unittest.main()
