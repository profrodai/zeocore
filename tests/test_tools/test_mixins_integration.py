# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_tools/test_mixins_integration.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test_base.py, test_imports.py, test_protocol.py (+2 more)
# exports: MockIntegrationService, CompleteQuackTool, TestMixinIntegration
# git_branch: refactor/toolkitWorkflow
# git_commit: 21a4e25
# === QV-LLM:END ===

"""
Integration tests for QuackTool mixins.

These tests verify that the mixins work correctly when combined together
in different configurations.
"""

import os
import tempfile
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from quack_core.integrations.core import IntegrationResult
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.tools import (
    BaseQuackToolPlugin,
    IntegrationEnabledMixin,
    OutputFormatMixin,
    QuackToolLifecycleMixin,
    ToolEnvInitializerMixin,
)
from quack_core.workflow.output import YAMLOutputWriter

# Import OutputResult from the correct location


class MockIntegrationService(BaseIntegrationService):
    """
    Mock implementation of BaseIntegrationService for testing.
    """

    @property
    def name(self) -> str:
        return "mock_service"

    def __init__(self) -> None:
        super().__init__()
        self.initialized = False
        self.upload_called = False
        self.upload_file_path = None
        self.upload_destination = None

    def initialize(self) -> None:
        self.initialized = True

    def upload_file(self, file_path: str,
                    destination: str | None = None) -> IntegrationResult:
        """Mock upload file method."""
        self.upload_called = True
        self.upload_file_path = file_path
        self.upload_destination = destination
        return IntegrationResult.success_result(
            message=f"File {file_path} uploaded to {destination}"
        )


class CompleteQuackTool(
    IntegrationEnabledMixin[MockIntegrationService],
    QuackToolLifecycleMixin,
    OutputFormatMixin,
    ToolEnvInitializerMixin,
    BaseQuackToolPlugin
):
    """
    Complete tool implementation using all mixins for testing.
    """

    def __init__(self) -> None:
        # Patch filesystem access and logging to avoid issues
        with patch('quack_core.lib.fs.service.get_service') as mock_get_service, \
                patch('quack_core.tools.base.setup_tool_logging'), \
                patch('quack_core.tools.base.get_logger') as mock_get_logger, \
                patch('os.getcwd') as mock_getcwd:
            # Configure mocks
            mock_fs = MagicMock()
            temp_result = MagicMock()
            temp_result.success = True
            temp_path = tempfile.mkdtemp(prefix="quack_complete_tool_")
            temp_result.path = temp_path
            temp_result.data = temp_path
            mock_fs.create_temp_directory.return_value = temp_result

            # Set up path mocks
            cwd_result = MagicMock()
            cwd_result.success = True
            cwd_path = tempfile.gettempdir()
            cwd_result.path = cwd_path
            cwd_result.data = cwd_path
            mock_fs.normalize_path.return_value = cwd_result

            output_path_result = MagicMock()
            output_path_result.success = True
            output_path = os.path.join(tempfile.gettempdir(), "output")
            output_path_result.path = output_path
            output_path_result.data = output_path
            mock_fs.join_path.return_value = output_path_result

            dir_result = MagicMock()
            dir_result.success = True
            dir_result.path = output_path
            dir_result.data = output_path
            mock_fs.ensure_directory.return_value = dir_result

            # Set up file info for process_file
            file_info_result = MagicMock()
            file_info_result.exists = True
            mock_fs.get_file_info.return_value = file_info_result

            # Configure other mocks
            mock_get_service.return_value = mock_fs
            mock_getcwd.return_value = tempfile.gettempdir()
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            super().__init__("complete_tool", "1.0.0")

            # Save for testing
            self.mock_fs = mock_fs

        self.env_initialized = False
        self.run_called = False
        self.run_options = None
        self._service = None

    def initialize_plugin(self) -> None:
        """Initialize the plugin."""
        # Resolve the integration service
        self._service = self.resolve_integration(MockIntegrationService)

        # Initialize the environment
        env_result = self._initialize_environment("mock_tool_env")
        self.env_initialized = env_result.success

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """Process content with this tool."""
        return {"content": content, "processed": True, "options": options}

    def _get_output_extension(self) -> str:
        """Override to return a custom extension."""
        return ".yaml"

    def get_output_writer(self) -> YAMLOutputWriter:
        """Override to return a YAML writer."""
        return YAMLOutputWriter()

    def run(self, options: dict[str, Any] | None = None) -> IntegrationResult:
        """Override run to implement custom behavior."""
        self.run_called = True
        self.run_options = options or {}

        # Run pre_run first
        pre_result = self.pre_run()
        if not pre_result.success:
            return pre_result

        try:
            # For test_complete_tool_run, create a real sample file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            temp_file.write(b'sample content')
            temp_file.close()
            sample_path = temp_file.name

            # Process the real file instead of "sample.txt"
            process_result = self.process_file(sample_path, options=self.run_options)
            if not process_result.success:
                return process_result

            # Generate output path
            output_path = os.path.join(
                self._output_dir,
                f"{os.path.basename(sample_path)}_output{self._get_output_extension()}"
            )

            # Upload the output if we have an upload service
            if self._upload_service:
                upload_result = self._upload_service.upload_file(
                    output_path, f"results/{os.path.basename(output_path)}"
                )
                if not upload_result.success:
                    return upload_result

            # Call post_run from the lifecycle mixin
            post_result = self.post_run()
            if not post_result.success:
                return post_result

            # Create a successful result with metadata in the content
            return IntegrationResult.success_result(
                message="Run completed successfully",
                content={
                    "input_file": sample_path,
                    "output_file": output_path
                }
            )
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error during run: {e}")
            return IntegrationResult.error_result(
                error=str(e),
                message="Run failed with exception"
            )
        finally:
            # Clean up the temporary file
            if 'sample_path' in locals() and os.path.exists(sample_path):
                try:
                    os.unlink(sample_path)
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.warning(f"Failed to delete temporary file: {e}")
    def upload(self, file_path: str,
               destination: str | None = None) -> IntegrationResult:
        """Override upload to use the integration service."""
        if not self._service:
            return IntegrationResult.error_result(
                error="Integration service not available",
                message="Cannot upload file without integration service"
            )

        return self._service.upload_file(file_path, destination)


class TestMixinIntegration(unittest.TestCase):
    """
    Integration tests for mixins used together.
    """

    def setUp(self) -> None:
        """
        Set up test fixtures.
        """
        # Create a mock service and fully initialize it
        self.mock_service = MockIntegrationService()
        self.mock_service.initialize()  # Explicitly initialize

        # Create a temporary file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(b'{"test": "data"}')
        self.temp_file.close()

        # Create the tool instance with proper patching
        # Import the module directly for patching
        import quack_core.integrations.core

        with patch.object(quack_core.integrations.core, 'get_integration_service',
                          return_value=self.mock_service), \
                patch('importlib.import_module') as mock_import:
            # Set up mock module
            self.mock_module = MagicMock()
            self.mock_module.initialize.return_value = IntegrationResult.success_result(
                message="Environment initialized successfully"
            )
            mock_import.return_value = self.mock_module

            # Create the tool - CompleteQuackTool needs to have _upload_service already defined
            self.tool = CompleteQuackTool()

            # Call resolve_integration which should work now with the patching
            self.tool._service = self.tool.resolve_integration(MockIntegrationService)

        # Verify initialization
        self.assertTrue(self.mock_service.initialized)
        self.assertEqual(self.tool._service, self.mock_service)
    def tearDown(self) -> None:
        """
        Tear down test fixtures.
        """
        os.unlink(self.temp_file.name)

    def test_initialization(self) -> None:
        """
        Test that all mixins are initialized correctly.
        """
        # Verify properties from BaseQuackToolPlugin
        self.assertEqual(self.tool.name, "complete_tool")
        self.assertEqual(self.tool.version, "1.0.0")

        # Verify integration service from IntegrationEnabledMixin
        self.assertEqual(self.tool.integration, self.mock_service)

        # Verify output settings from OutputFormatMixin
        self.assertEqual(self.tool._get_output_extension(), ".yaml")
        self.assertIsInstance(self.tool.get_output_writer(), YAMLOutputWriter)

    @patch("quack_core.workflow.runners.file_runner.FileWorkflowRunner")
    def test_run_workflow(self, mock_runner: MagicMock) -> None:
        """
        Test the complete workflow using run method.
        """
        # Setup mock runner
        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance

        # Create a mock run result with the correct structure
        mock_result = MagicMock()
        mock_result.success = True
        mock_runner_instance.run.return_value = mock_result

        # Patch the pre_run and post_run methods to ensure they return success
        with patch.object(self.tool, 'pre_run',
                          return_value=IntegrationResult.success_result(
                                  message="Pre-run success")), \
                patch.object(self.tool, 'post_run',
                             return_value=IntegrationResult.success_result(
                                 message="Post-run success")):
            # Run the tool with options
            options = {"option1": "value1", "option2": "value2"}
            result = self.tool.run(options)

            # Assert the result
            self.assertTrue(result.success)
            self.assertIn("Run completed successfully", result.message)

            # Verify run was called with correct options
            self.assertTrue(self.tool.run_called)
            self.assertEqual(self.tool.run_options, options)

    def test_upload_via_integration(self) -> None:
        """
        Test uploading a file via the integration service.
        """
        # Upload the file
        destination = "test_destination"
        result = self.tool.upload(self.temp_file.name, destination)

        # Assert the result
        self.assertTrue(result.success)
        self.assertIn("uploaded", result.message)

        # Verify the service was called correctly
        self.assertTrue(self.mock_service.upload_called)
        self.assertEqual(self.mock_service.upload_file_path, self.temp_file.name)
        self.assertEqual(self.mock_service.upload_destination, destination)

    @patch("quack_core.integrations.core.get_integration_service")
    def test_upload_without_service(self, mock_get_integration: MagicMock) -> None:
        """
        Test uploading a file when integration service is not available.
        """
        # Create a new tool without an integration service
        mock_get_integration.return_value = None

        tool = CompleteQuackTool()

        # Upload the file
        result = tool.upload(self.temp_file.name)

        # Assert the result
        self.assertFalse(result.success)
        self.assertIn("Integration service not available", result.error)

    def test_lifecycle_methods(self) -> None:
        """
        Test that lifecycle methods from QuackToolLifecycleMixin work.
        """
        # Test pre_run
        pre_result = self.tool.pre_run()
        self.assertTrue(pre_result.success)
        self.assertIn("Pre-run completed", pre_result.message)

        # Test post_run
        post_result = self.tool.post_run()
        self.assertTrue(post_result.success)
        self.assertIn("Post-run completed", post_result.message)

        # Test validate
        validate_result = self.tool.validate()
        self.assertTrue(validate_result.success)
        self.assertIn("not implemented", validate_result.message)


if __name__ == "__main__":
    unittest.main()
