# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_tools/mocks.py
# role: tests
# neighbors: __init__.py, conftest.py, test_base.py, test_imports.py, test_mixins_integration.py, test_protocol.py (+2 more)
# exports: MockIntegrationService, MockLogger, MockWorkflowRunner, BaseMockTool, BaseMockToolWithIntegration, create_mock_fs, mock_data_result, mock_operation_result (+2 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===

"""
Mocks for testing the quack_core.tools module.

This module provides mock objects and helper functions for testing
the tools components without actually using the real implementations
of services, filesystem operations, etc.
"""

import os
import tempfile
from typing import Any, TypeVar, cast
from unittest.mock import MagicMock, patch

from quack_core.lib.fs import DataResult, OperationResult
from quack_core.integrations.core import IntegrationResult
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.tools.base import BaseQuackToolPlugin


def create_mock_fs() -> MagicMock:
    """
    Create a mock filesystem service for testing.

    Returns:
        MagicMock: A configured mock filesystem service
    """
    mock_fs = MagicMock()

    # Configure common result patterns

    # Mock temp directory creation
    temp_result = MagicMock(spec=DataResult)
    temp_result.success = True
    temp_result.path = os.path.join(tempfile.gettempdir(), "mock_temp_dir")
    # Make sure path is also available as data for backward compatibility
    temp_result.data = temp_result.path
    mock_fs.create_temp_directory.return_value = temp_result

    # Mock path normalization
    norm_result = MagicMock(spec=DataResult)
    norm_result.success = True
    norm_result.path = tempfile.gettempdir()
    norm_result.data = norm_result.path
    mock_fs.normalize_path.return_value = norm_result

    # Mock path joining
    join_result = MagicMock(spec=DataResult)
    join_result.success = True
    join_result.path = os.path.join(tempfile.gettempdir(), "output")
    join_result.data = join_result.path
    mock_fs.join_path.return_value = join_result

    # Mock directory creation
    dir_result = MagicMock(spec=OperationResult)
    dir_result.success = True
    dir_result.path = os.path.join(tempfile.gettempdir(), "output")
    dir_result.data = dir_result.path
    mock_fs.ensure_directory.return_value = dir_result

    # Mock file info
    file_info = MagicMock()
    file_info.exists = True
    mock_fs.get_file_info.return_value = file_info

    return mock_fs


def mock_data_result(data: Any, success: bool = True) -> DataResult:
    """
    Create a mock DataResult with the required fields.

    Args:
        data: The data to be contained in the result
        success: Whether the operation was successful

    Returns:
        DataResult: A properly constructed DataResult
    """
    return DataResult(
        data=data,
        success=success,
        path=str(data) if data is not None else None,
        format="path"
    )


def mock_operation_result(data: Any, success: bool = True) -> OperationResult:
    """
    Create a mock OperationResult with the required fields.

    Args:
        data: The data to be contained in the result
        success: Whether the operation was successful

    Returns:
        OperationResult: A properly constructed OperationResult
    """
    return OperationResult(
        data=data,
        success=success,
        path=str(data) if data is not None else None
    )


def mock_integration_result(success: bool = True, message: str = "Success",
                            content: Any = None,
                            error: str = None) -> IntegrationResult:
    """
    Create a mock IntegrationResult.

    Args:
        success: Whether the integration operation was successful
        message: Success or error message
        content: Optional content returned by the integration
        error: Error message if not successful

    Returns:
        IntegrationResult: A properly constructed IntegrationResult
    """
    if success:
        return IntegrationResult.success_result(message=message, content=content)
    else:
        return IntegrationResult.error_result(message=message,
                                              error=error or "Unknown error")


class MockIntegrationService(BaseIntegrationService):
    """
    Mock implementation of BaseIntegrationService for testing.
    """

    @property
    def name(self) -> str:
        return "mock_service"

    def __init__(self) -> None:
        self.initialized = False
        self.called_methods: list[str] = []
        self.call_args: dict[str, list[Any]] = {}

    def initialize(self) -> None:
        """Record that initialize was called."""
        self.initialized = True
        self.called_methods.append("initialize")

    def process(self, data: Any,
                options: dict[str, Any] | None = None) -> IntegrationResult:
        """Process data with the mock service."""
        self.called_methods.append("process")
        self.call_args["process"] = [data, options]
        return mock_integration_result(success=True, message="Processed successfully",
                                       content=data)

    def upload(self, data: Any, path: str | None = None) -> IntegrationResult:
        """Mock uploading data to the service."""
        self.called_methods.append("upload")
        self.call_args["upload"] = [data, path]
        return mock_integration_result(success=True,
                                       message=f"Uploaded to {path or 'default location'}")

    def download(self, resource_id: str,
                 path: str | None = None) -> IntegrationResult:
        """Mock downloading data from the service."""
        self.called_methods.append("download")
        self.call_args["download"] = [resource_id, path]
        return mock_integration_result(success=True,
                                       message=f"Downloaded {resource_id}")


class MockLogger:
    """Mock logger for testing."""

    def __init__(self) -> None:
        self.logs: dict[str, list[str]] = {
            "debug": [],
            "info": [],
            "warning": [],
            "error": [],
            "critical": []
        }

    def debug(self, msg: str) -> None:
        self.logs["debug"].append(msg)

    def info(self, msg: str) -> None:
        self.logs["info"].append(msg)

    def warning(self, msg: str) -> None:
        self.logs["warning"].append(msg)

    def error(self, msg: str) -> None:
        self.logs["error"].append(msg)

    def critical(self, msg: str) -> None:
        self.logs["critical"].append(msg)

    def exception(self, msg: str) -> None:
        self.logs["error"].append(f"Exception: {msg}")


class MockWorkflowRunner:
    """Mock for the FileWorkflowRunner."""

    def __init__(self, processor: Any = None, remote_handler: Any = None,
                 output_writer: Any = None) -> None:
        self.processor = processor
        self.remote_handler = remote_handler
        self.output_writer = output_writer
        self.run_called = False
        self.run_args: list[Any] = []

    def run(self, file_path: str, options: dict[str, Any]) -> IntegrationResult:
        """Mock running the workflow."""
        self.run_called = True
        self.run_args = [file_path, options]
        return mock_integration_result(success=True,
                                       message="File processed successfully")


class BaseMockTool(BaseQuackToolPlugin):
    """
    Base class for mock tools that handles common patching.

    This class should be subclassed by specific mock tool implementations.
    It handles patching common dependencies for testing.
    """

    def __init__(self, name: str, version: str) -> None:
        """
        Initialize with mocked dependencies.

        Args:
            name: The name of the tool
            version: The version of the tool
        """
        # We need to patch all external dependencies
        patch_targets = [
            # Filesystem
            ("quack_core.lib.fs.service.get_service", create_mock_fs()),
            # Logging
            ("quack_core.config.tooling.logger.setup_tool_logging", MagicMock()),
            ("quack_core.config.tooling.logger.get_logger",
             MagicMock(return_value=MockLogger())),
            # OS
            ("os.getcwd", MagicMock(return_value=tempfile.gettempdir())),
            # FileWorkflowRunner
            ("quack_core.workflow.runners.file_runner.FileWorkflowRunner",
             MockWorkflowRunner),
        ]

        # Apply all patches
        patchers = [patch(target, return_value=value) for target, value in
                    patch_targets]

        # Start all patchers
        for patcher in patchers:
            patcher.start()

        try:
            # Initialize the base class
            super().__init__(name, version)
        finally:
            # Stop all patchers to ensure they don't affect other tests
            for patcher in patchers:
                patcher.stop()


T = TypeVar("T", bound=BaseIntegrationService)


class BaseMockToolWithIntegration(BaseMockTool):
    """
    Base class for mock tools that use integration services.

    This class adds support for mocking integration services.
    """

    def __init__(self, name: str, version: str, service_class: type[T],
                 service_instance: T | None = None) -> None:
        """
        Initialize with mocked dependencies including integration service.

        Args:
            name: The name of the tool
            version: The version of the tool
            service_class: The class of integration service to mock
            service_instance: Optional specific instance to use
        """
        # Create or use the service instance
        self.mock_service = service_instance or cast(T, MockIntegrationService())

        # Patch the integration service
        with patch("quack_core.integrations.core.get_integration_service",
                   return_value=self.mock_service):
            # Initialize the base class
            super().__init__(name, version)


def create_patched_base_tool(name: str = "dummy_tool",
                             version: str = "1.0.0") -> MagicMock:
    """
    Create a properly patched BaseQuackToolPlugin for tests.

    This function applies all necessary patches and returns an instance
    of a mock tool that can be used in tests without affecting the real
    environment.

    Args:
        name: The name of the tool
        version: The version of the tool

    Returns:
        MagicMock: A mocked tool instance
    """
    mock_tool = MagicMock(spec=BaseQuackToolPlugin)
    mock_tool.name = name
    mock_tool.version = version
    mock_tool._logger = MockLogger()
    mock_tool.logger = mock_tool._logger
    mock_tool.fs = create_mock_fs()
    mock_tool._temp_dir = os.path.join(tempfile.gettempdir(), f"quack_{name}_temp")
    mock_tool._output_dir = os.path.join(tempfile.gettempdir(), f"quack_{name}_output")

    return mock_tool
