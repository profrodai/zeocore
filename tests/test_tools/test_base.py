# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_tools/test_base.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test_imports.py, test_mixins_integration.py, test_protocol.py (+2 more)
# exports: DummyQuackTool, CustomExtensionTool, RemoteHandlerTool, CustomWriterTool, UnavailableTool, TestBaseQuackToolPlugin, TestBaseQuackToolPluginWithPytest, get_path_from_result (+2 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Tests for the BaseQuackToolPlugin class.
"""

import os
import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from quack_core.core.fs import DataResult, OperationResult
from quack_core.tools.base import BaseQuackToolPlugin
from quack_core.workflow.output import DefaultOutputWriter, YAMLOutputWriter


def get_path_from_result(result: Any) -> str:
    """
    Extract a path string from various types of operation results.

    This helper function handles different result types and extracts a string path,
    regardless of whether the result uses .data, .path, or is already a string.

    Args:
        result: Result object which could be DataResult, OperationResult, or string

    Returns:
        str: The extracted path as a string
    """
    # Handle different result types
    if hasattr(result, 'path') and result.path:
        return str(result.path)
    elif hasattr(result, 'data') and result.data:
        return str(result.data)
    elif isinstance(result, str):
        return result
    elif isinstance(result, Path):
        return str(result)
    else:
        # Fallback - try to convert to string
        return str(result)


# Global mock for use in tests to avoid filesystem issues
def create_mock_fs() -> MagicMock:
    """Create a mock filesystem service for testing."""
    mock_fs = MagicMock()

    # Configure successful temp directory creation
    temp_result = MagicMock()
    temp_result.success = True
    temp_dir = tempfile.mkdtemp(prefix="quack_test_")
    temp_result.path = Path(temp_dir)
    temp_result.data = temp_dir
    mock_fs.create_temp_directory.return_value = temp_result

    # Configure successful path handling
    cwd_result = MagicMock()
    cwd_result.success = True
    cwd_path = tempfile.gettempdir()
    cwd_result.path = Path(cwd_path)
    cwd_result.data = cwd_path
    mock_fs.normalize_path.return_value = cwd_result

    output_path_result = MagicMock()
    output_path_result.success = True
    output_path = os.path.join(tempfile.gettempdir(), "output")
    output_path_result.path = Path(output_path)
    output_path_result.data = output_path
    mock_fs.join_path.return_value = output_path_result

    # Configure successful directory creation
    dir_result = MagicMock()
    dir_result.success = True
    dir_result.path = Path(output_path)
    dir_result.data = output_path
    mock_fs.ensure_directory.return_value = dir_result

    # Set up for file_info in process_file tests
    file_info_result = MagicMock()
    file_info_result.exists = True
    mock_fs.get_file_info.return_value = file_info_result

    return mock_fs


class DummyQuackTool(BaseQuackToolPlugin):
    """
    Dummy implementation of BaseQuackToolPlugin for testing.
    """

    def __init__(self) -> None:
        # Patch get_service to avoid filesystem issues
        with patch('quack_core.core.fs.service.get_service') as mock_get_service, \
                patch('os.getcwd') as mock_getcwd:
            # Configure mocks
            mock_fs = create_mock_fs()
            mock_get_service.return_value = mock_fs
            mock_getcwd.return_value = tempfile.gettempdir()

            # Initialize base class
            super().__init__("dummy_tool", "1.0.0")

            # Save mock filesystem for testing
            self.mock_fs = mock_fs

    def initialize_plugin(self) -> None:
        """No-op implementation for testing"""
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """
        Simple echo for testing.

        Returns a dictionary compatible with what FileWorkflowRunner expects.
        """
        return {"content": content, "options": options}

class CustomExtensionTool(BaseQuackToolPlugin):
    """
    Tool that uses a custom extension.
    """

    def __init__(self) -> None:
        # Patch get_service to avoid filesystem issues
        with patch('quack_core.core.fs.service.get_service') as mock_get_service, \
                patch('quack_core.tools.base.setup_tool_logging') as mock_setup_logging, \
                patch('quack_core.tools.base.get_logger') as mock_get_logger, \
                patch('os.getcwd') as mock_getcwd:
            # Configure mocks
            mock_fs = create_mock_fs()
            mock_get_service.return_value = mock_fs
            mock_getcwd.return_value = tempfile.gettempdir()
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # Initialize
            super().__init__("custom_ext_tool", "1.0.0")

            # Save mock filesystem for testing
            self.mock_fs = mock_fs

    def initialize_plugin(self) -> None:
        # No-op for testing
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        return {"content": content}

    def _get_output_extension(self) -> str:
        return ".yaml"


class RemoteHandlerTool(BaseQuackToolPlugin):
    """
    Tool that provides a custom remote handler.
    """

    def __init__(self) -> None:
        # Patch get_service to avoid filesystem issues
        with patch('quack_core.core.fs.service.get_service') as mock_get_service, \
                patch('quack_core.tools.base.setup_tool_logging') as mock_setup_logging, \
                patch('quack_core.tools.base.get_logger') as mock_get_logger, \
                patch('os.getcwd') as mock_getcwd:
            # Configure mocks
            mock_fs = create_mock_fs()
            mock_get_service.return_value = mock_fs
            mock_getcwd.return_value = tempfile.gettempdir()
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # Initialize
            super().__init__("remote_handler_tool", "1.0.0")

            # Save mock filesystem for testing
            self.mock_fs = mock_fs

    def initialize_plugin(self) -> None:
        # No-op for testing
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        return {"content": content}

    def get_remote_handler(self) -> Any:
        return MagicMock()


class CustomWriterTool(BaseQuackToolPlugin):
    """
    Tool that provides a custom output writer.
    """

    def __init__(self) -> None:
        # Patch get_service to avoid filesystem issues
        with patch('quack_core.core.fs.service.get_service') as mock_get_service, \
                patch('quack_core.tools.base.setup_tool_logging') as mock_setup_logging, \
                patch('quack_core.tools.base.get_logger') as mock_get_logger, \
                patch('os.getcwd') as mock_getcwd:
            # Configure mocks
            mock_fs = create_mock_fs()
            mock_get_service.return_value = mock_fs
            mock_getcwd.return_value = tempfile.gettempdir()
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # Initialize
            super().__init__("custom_writer_tool", "1.0.0")

            # Save mock filesystem for testing
            self.mock_fs = mock_fs

    def initialize_plugin(self) -> None:
        # No-op for testing
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        return {"content": content}

    def get_output_writer(self) -> YAMLOutputWriter:
        return YAMLOutputWriter()


class UnavailableTool(BaseQuackToolPlugin):
    """
    Tool that is not available.
    """

    def __init__(self) -> None:
        # Patch get_service to avoid filesystem issues
        with patch('quack_core.core.fs.service.get_service') as mock_get_service, \
                patch('quack_core.tools.base.setup_tool_logging') as mock_setup_logging, \
                patch('quack_core.tools.base.get_logger') as mock_get_logger, \
                patch('os.getcwd') as mock_getcwd:
            # Configure mocks
            mock_fs = create_mock_fs()
            mock_get_service.return_value = mock_fs
            mock_getcwd.return_value = tempfile.gettempdir()
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # Initialize
            super().__init__("unavailable_tool", "1.0.0")

            # Save mock filesystem for testing
            self.mock_fs = mock_fs

    def initialize_plugin(self) -> None:
        # No-op for testing
        pass

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        return {"content": content}

    def is_available(self) -> bool:
        return False


@pytest.fixture
def dummy_tool() -> Generator[DummyQuackTool, None, None]:
    """Fixture that creates a DummyQuackTool for pytest-style tests."""
    # The DummyQuackTool constructor already includes the necessary patching
    tool = DummyQuackTool()
    yield tool


class TestBaseQuackToolPlugin(unittest.TestCase):
    """
    Test cases for BaseQuackToolPlugin.
    """

    def setUp(self) -> None:
        """
        Set up test fixtures.
        """
        with patch('quack_core.tools.base.setup_tool_logging'), \
                patch('quack_core.tools.base.get_logger'):
            self.tool = DummyQuackTool()

        # Create a temp file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(b'{"test": "data"}')
        self.temp_file.close()

    def tearDown(self) -> None:
        """
        Tear down test fixtures.
        """
        os.unlink(self.temp_file.name)

    def test_initialization(self) -> None:
        """
        Test that initialization sets up the tool correctly.
        """
        # Create a direct mock for setup_tool_logging to ensure it's called
        setup_tool_logging_mock = MagicMock()

        # Use simple patching to avoid complex nesting
        with patch("quack_core.tools.base.setup_tool_logging",
                   setup_tool_logging_mock), \
                patch('quack_core.core.fs.service.get_service') as mock_get_service, \
                patch('os.getcwd') as mock_getcwd:
            # Configure mocks
            mock_fs = create_mock_fs()
            mock_get_service.return_value = mock_fs
            mock_getcwd.return_value = tempfile.gettempdir()

            # Create the tool with the mocked filesystem
            tool = DummyQuackTool()

            # Verify basic properties
            self.assertEqual(tool.name, "dummy_tool")
            self.assertEqual(tool.version, "1.0.0")

            # Verify logging was set up - with any args since we just want to verify it was called
            setup_tool_logging_mock.assert_called_once()

    def test_get_metadata(self) -> None:
        """
        Test that metadata is returned correctly.
        """
        metadata = self.tool.get_metadata()

        self.assertEqual(metadata.name, "dummy_tool")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertTrue(isinstance(metadata.description, str))

    def test_is_available(self) -> None:
        """
        Test that is_available returns True by default.
        """
        self.assertTrue(self.tool.is_available())

    def test_initialize(self) -> None:
        """
        Test that initialize works correctly.
        """
        result = self.tool.initialize()

        self.assertTrue(result.success)
        self.assertIn("Successfully initialized dummy_tool", result.message)

    def test_initialize_unavailable(self) -> None:
        """
        Test that initialize handles unavailable tools.
        """
        with patch('quack_core.tools.base.setup_tool_logging'), \
                patch('quack_core.tools.base.get_logger'):
            tool = UnavailableTool()

        result = tool.initialize()

        self.assertFalse(result.success)
        self.assertIn("Tool is not available", result.error)
        self.assertIn("not available", result.message)

    def test_initialize_exception(self) -> None:
        """
        Test that initialize handles exceptions.
        """
        with patch.object(DummyQuackTool, 'is_available',
                          side_effect=Exception("Test exception")):
            result = self.tool.initialize()

            self.assertFalse(result.success)
            self.assertEqual(result.error, "Test exception")
            self.assertIn("Failed to initialize", result.message)

    @patch("quack_core.workflow.runners.file_runner.FileWorkflowRunner")
    def test_process_file_success(self, mock_runner: MagicMock) -> None:
        """
        Test that process_file works correctly on success.
        """
        # Set up mock file info
        self.tool.mock_fs.get_file_info.return_value = MagicMock(exists=True)

        # Setup mock runner
        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance

        # Create a mock result with the correct structure
        mock_result = MagicMock()
        mock_result.success = True
        # Don't use .error property as it might cause issues
        mock_runner_instance.run.return_value = mock_result

        # Call method
        result = self.tool.process_file(self.temp_file.name)

        # Assertions
        self.assertTrue(result.success)
        self.assertIn("File processed successfully", result.message)
        mock_runner.assert_called_once()
        mock_runner_instance.run.assert_called_once()

    @patch("quack_core.workflow.runners.file_runner.FileWorkflowRunner")
    def test_process_file_failure(self, mock_runner: MagicMock) -> None:
        """
        Test that process_file handles failure correctly.
        """
        # Set up mock file info
        self.tool.mock_fs.get_file_info.return_value = MagicMock(exists=True)

        # Setup mock runner
        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance

        # Create a mock result with failure status
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Test error"
        mock_runner_instance.run.return_value = mock_result

        # Call method
        result = self.tool.process_file(self.temp_file.name)

        # Assertions
        self.assertFalse(result.success)
        self.assertIn("File processing failed", result.message)
        self.assertEqual(result.error, "Test error")

    @patch("quack_core.workflow.runners.file_runner.FileWorkflowRunner")
    def test_process_file_error_from_result(self, mock_runner: MagicMock) -> None:
        """
        Test that process_file handles failure with error property.
        """
        # Set up mock file info
        self.tool.mock_fs.get_file_info.return_value = MagicMock(exists=True)

        # Setup mock runner
        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance

        # Create a mock result with failure status
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Direct error property"
        mock_runner_instance.run.return_value = mock_result

        # Call method
        result = self.tool.process_file(self.temp_file.name)

        # Assertions
        self.assertFalse(result.success)
        self.assertIn("File processing failed", result.message)
        self.assertEqual(result.error, "Direct error property")

    @patch("quack_core.workflow.runners.file_runner.FileWorkflowRunner")
    def test_process_file_exception(self, mock_runner: MagicMock) -> None:
        """
        Test that process_file handles exceptions correctly.
        """
        # Set up mock file info
        self.tool.mock_fs.get_file_info.return_value = MagicMock(exists=True)

        # Make FileWorkflowRunner raise an exception
        exception_msg = "Test exception"
        mock_runner.side_effect = Exception(exception_msg)

        # Call method
        result = self.tool.process_file(self.temp_file.name)

        # Assertions
        self.assertFalse(result.success)
        self.assertEqual(result.error, exception_msg)
        self.assertIn("File processing failed", result.message)

    def test_process_file_not_found(self) -> None:
        """
        Test that process_file handles file not found correctly.
        """
        # Configure file_info to return file not found
        file_info = MagicMock()
        file_info.exists = False
        self.tool.mock_fs.get_file_info.return_value = file_info

        # Call method
        result = self.tool.process_file("nonexistent_file.txt")

        # Assertions
        self.assertFalse(result.success)
        self.assertIn("No such file", result.error)
        # self.assertIn("input file not found", result.message)

    def test_get_output_extension(self) -> None:
        """
        Test that _get_output_extension returns the default extension.
        """
        self.assertEqual(self.tool._get_output_extension(), ".json")

    def test_get_output_extension_custom(self) -> None:
        """
        Test that _get_output_extension returns custom extension when overridden.
        """
        with patch('quack_core.tools.base.setup_tool_logging'), \
                patch('quack_core.tools.base.get_logger'):
            tool = CustomExtensionTool()

        self.assertEqual(tool._get_output_extension(), ".yaml")

    def test_get_remote_handler(self) -> None:
        """
        Test that get_remote_handler returns None by default.
        """
        self.assertIsNone(self.tool.get_remote_handler())

    def test_get_remote_handler_custom(self) -> None:
        """
        Test that get_remote_handler returns custom handler when overridden.
        """
        with patch('quack_core.tools.base.setup_tool_logging'), \
                patch('quack_core.tools.base.get_logger'):
            tool = RemoteHandlerTool()

        self.assertIsNotNone(tool.get_remote_handler())

    def test_get_output_writer(self) -> None:
        """
        Test that get_output_writer returns a DefaultOutputWriter.
        """
        writer = self.tool.get_output_writer()
        self.assertIsInstance(writer, DefaultOutputWriter)

    def test_get_output_writer_yaml(self) -> None:
        """
        Test that get_output_writer returns a YAMLOutputWriter when extension is .yaml.
        """
        with patch('quack_core.tools.base.setup_tool_logging'), \
                patch('quack_core.tools.base.get_logger'):
            tool = CustomExtensionTool()

        writer = tool.get_output_writer()
        self.assertIsInstance(writer, YAMLOutputWriter)

    def test_get_output_writer_custom(self) -> None:
        """
        Test that get_output_writer returns custom writer when overridden.
        """
        with patch('quack_core.tools.base.setup_tool_logging'), \
                patch('quack_core.tools.base.get_logger'):
            tool = CustomWriterTool()

        writer = tool.get_output_writer()
        self.assertIsInstance(writer, YAMLOutputWriter)

    def test_filesystem_error_handling(self) -> None:
        """
        Test that initialization handles filesystem errors gracefully.
        """
        with patch('quack_core.core.fs.service.get_service') as mock_get_service, \
                patch('os.getcwd', return_value=tempfile.gettempdir()), \
                patch('quack_core.tools.base.setup_tool_logging'), \
                patch('quack_core.tools.base.get_logger'):
            # Setup the filesystem service to fail when creating temp directory
            mock_fs = MagicMock()
            mock_get_service.return_value = mock_fs

            temp_result = MagicMock()
            temp_result.success = False
            mock_fs.create_temp_directory.return_value = temp_result

            # Set up the dir_result for the output directory to fail as well
            dir_result = MagicMock()
            dir_result.success = False
            mock_fs.ensure_directory.return_value = dir_result

            # Configure successful path handling
            cwd_result = MagicMock()
            cwd_result.success = True
            cwd_path = tempfile.gettempdir()
            cwd_result.path = Path(cwd_path)
            cwd_result.data = cwd_path
            mock_fs.normalize_path.return_value = cwd_result

            output_path_result = MagicMock()
            output_path_result.success = True
            output_path = os.path.join(tempfile.gettempdir(), "output")
            output_path_result.path = Path(output_path)
            output_path_result.data = output_path
            mock_fs.join_path.return_value = output_path_result

            # Initialize a tool with these mocked services
            tool = DummyQuackTool()

            # The tool should have fallen back to using tempfile
            self.assertTrue(os.path.exists(tool._temp_dir))

            # Directory should have the prefix
            self.assertTrue("quack_" in os.path.basename(tool._temp_dir))


class TestBaseQuackToolPluginWithPytest:
    """
    Test cases using pytest fixtures for BaseQuackToolPlugin.
    """

    def test_fixture_initialization(self, dummy_tool: DummyQuackTool) -> None:
        """Test that the fixture correctly initializes the tool."""
        assert dummy_tool.name == "dummy_tool"
        assert dummy_tool.version == "1.0.0"

    def test_dataresult_handling(self, dummy_tool: DummyQuackTool) -> None:
        """Test how the tool handles DataResult objects."""
        # Create a DataResult to pass to a Path
        data_result = DataResult(data="test_path", success=True, path="test_path",
                                 format="path")

        # Test extracting path from the result
        path_str = get_path_from_result(data_result)

        # Verify the path was extracted correctly
        assert path_str == "test_path"

        # Test creating a Path object from the result
        path = Path(path_str)
        assert str(path) == "test_path"

    def test_operationresult_handling(self, dummy_tool: DummyQuackTool) -> None:
        """Test how the tool handles OperationResult objects."""
        # Create an OperationResult to pass to a Path
        op_result = OperationResult(data="op_path", success=True, path="op_path")

        # Test extracting path from the result
        path_str = get_path_from_result(op_result)

        # Verify the path was extracted correctly
        assert path_str == "op_path"

        # Test creating a Path object from the result
        path = Path(path_str)
        assert str(path) == "op_path"


if __name__ == "__main__":
    unittest.main()
