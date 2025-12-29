# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_tools/test_tools.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test_base.py, test_imports.py, test_mixins_integration.py (+2 more)
# exports: DummyQuackTool, YamlOutputTool, RemoteHandlerTool, UnavailableTool, IntegrationTool, CompleteTool
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===

"""
Test tool implementations for testing quack_core.tools.

This module provides concrete tool implementations for testing
the tools components.
"""

from typing import Any, TypeVar
from unittest.mock import MagicMock, patch

from quack_core.integrations.core import IntegrationResult
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.tools import (
    IntegrationEnabledMixin,
    OutputFormatMixin,
    QuackToolLifecycleMixin,
    ToolEnvInitializerMixin,
)
from quack_core.workflow.output import YAMLOutputWriter

from .mocks import BaseMockTool, MockIntegrationService


class DummyQuackTool(BaseMockTool):
    """
    Dummy implementation of BaseQuackToolPlugin for testing.

    This class provides a simple tool that can be used in tests.
    It implements the minimal required functionality.
    """

    def __init__(self) -> None:
        """Initialize the dummy tool."""
        super().__init__("dummy_tool", "1.0.0")
        self.process_calls: list[dict[str, Any]] = []

    def initialize_plugin(self) -> None:
        """Initialize the plugin (no-op for testing)."""
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """Process content by recording the call and returning modified content."""
        self.process_calls.append({"content": content, "options": options})
        return {"content": content, "options": options, "processed": True}


class YamlOutputTool(BaseMockTool):
    """
    Test tool that uses YAML output.

    This class demonstrates overriding output extension and writer.
    """

    def __init__(self) -> None:
        """Initialize the YAML output tool."""
        super().__init__("yaml_tool", "1.0.0")

    def initialize_plugin(self) -> None:
        """Initialize the plugin (no-op for testing)."""
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """Process content and return as a dict for YAML serialization."""
        return {"content": content, "options": options}

    def _get_output_extension(self) -> str:
        """Override to return YAML extension."""
        return ".yaml"

    def get_output_writer(self) -> YAMLOutputWriter:
        """Override to return YAML writer."""
        return YAMLOutputWriter()


class RemoteHandlerTool(BaseMockTool):
    """
    Test tool that provides a custom remote handler.

    This class demonstrates overriding the remote handler.
    """

    def __init__(self) -> None:
        """Initialize the remote handler tool."""
        super().__init__("remote_handler_tool", "1.0.0")
        self.remote_handler = MagicMock()

    def initialize_plugin(self) -> None:
        """Initialize the plugin (no-op for testing)."""
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """Process content using the remote handler."""
        return {"content": content, "options": options}

    def get_remote_handler(self) -> MagicMock:
        """Override to return a mock remote handler."""
        return self.remote_handler


class UnavailableTool(BaseMockTool):
    """
    Test tool that reports itself as unavailable.

    This class demonstrates overriding is_available.
    """

    def __init__(self) -> None:
        """Initialize the unavailable tool."""
        super().__init__("unavailable_tool", "1.0.0")

    def initialize_plugin(self) -> None:
        """Initialize the plugin (no-op for testing)."""
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """Process content (should never be called)."""
        return {"content": content, "options": options}

    def is_available(self) -> bool:
        """Override to return False."""
        return False


T = TypeVar("T", bound=BaseIntegrationService)


class IntegrationTool(IntegrationEnabledMixin[MockIntegrationService], BaseMockTool):
    """
    Test tool that uses integration services.

    This class demonstrates using IntegrationEnabledMixin.
    """

    def __init__(self) -> None:
        """Initialize the integration tool."""
        # Cache for integration service
        self._service: MockIntegrationService | None = None

        # Patch the integration service
        with patch("quack_core.integrations.core.get_integration_service",
                   return_value=MockIntegrationService()):
            # Initialize the base class
            super().__init__("integration_tool", "1.0.0")

    def initialize_plugin(self) -> None:
        """Initialize the plugin and resolve the integration service."""
        self._service = self.resolve_integration(MockIntegrationService)

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """Process content using the integration service."""
        if self._service:
            result = self._service.process(content, options)
            if result.success:
                return {"content": content, "processed": True, "options": options}

        return {"content": content, "processed": False, "options": options}


class CompleteTool(
    IntegrationEnabledMixin[MockIntegrationService],
    QuackToolLifecycleMixin,
    OutputFormatMixin,
    ToolEnvInitializerMixin,
    BaseMockTool
):
    """
    Complete tool using all mixins.

    This class demonstrates combining all available mixins.
    """

    def __init__(self) -> None:
        """Initialize the complete tool."""
        # Patch the integration service
        with patch("quack_core.integrations.core.get_integration_service",
                   return_value=MockIntegrationService()):
            # Initialize the base class
            super().__init__("complete_tool", "1.0.0")

        self.process_called = False
        self.processed_content = None
        self.processed_options = None

    def initialize_plugin(self) -> None:
        """Initialize the plugin and resolve the integration service."""
        self._service = self.resolve_integration(MockIntegrationService)

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """Process content and track call data."""
        self.process_called = True
        self.processed_content = content
        self.processed_options = options

        return {
            "result": "Processed successfully",
            "content": content,
            "options": options
        }

    def _get_output_extension(self) -> str:
        """Override to use YAML output."""
        return ".yaml"

    def get_output_writer(self) -> YAMLOutputWriter:
        """Override to provide YAML writer."""
        return YAMLOutputWriter()

    def run(self, options: dict[str, Any] | None = None) -> IntegrationResult:
        """Run the full tool workflow."""
        # Ensure options is a dict
        options = options or {}

        # Call pre_run from the lifecycle mixin
        pre_result = self.pre_run()
        if not pre_result.success:
            return pre_result

        # Process a sample file
        process_result = IntegrationResult.success_result(
            message="Processing completed",
            content={"processed": True, "options": options}
        )

        # Use the service if available
        if hasattr(self, "_service") and self._service:
            self._service.process({"sample": "data"}, options)

        # Call post_run from the lifecycle mixin
        post_result = self.post_run()
        if not post_result.success:
            return post_result

        return IntegrationResult.success_result(
            message="Tool execution complete",
            content={"result": "success"}
        )
