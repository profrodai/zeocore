# quack-core/tests/test_integrations/pandoc/test_pandoc_integration_edge_cases.py
"""
Additional tests for edge cases in the pandoc integration.

This module tests edge cases and error handling in the pandoc integration
to ensure robust behavior in all situations.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc import (
    ConversionMetrics,
    FileInfo,
)
from quack_core.integrations.pandoc.service import PandocIntegration

# --- Tests for PandocIntegration edge cases ---

def test_integration_with_custom_config_path():
    """Test PandocIntegration with custom config path."""
    # Mock config provider
    mock_config_provider = MagicMock()
    mock_config_provider.load_config.return_value = {"output_dir": "/custom/path"}

    # Mock the PathResolver to avoid 'no attribute service' error
    with patch('quack_core.paths.service', MagicMock()), \
            patch('quack_core.integrations.pandoc.config.PandocConfigProvider',
                  return_value=mock_config_provider), \
            patch('quack_core.fs.service.standalone.resolve_path',
                  return_value=SimpleNamespace(success=True, path="/resolved/path")):
        integration = PandocIntegration(config_path="/path/to/config.yaml")

        # Initialize to trigger config loading
        with patch('quack_core.integrations.pandoc.service.verify_pandoc',
                   return_value="2.11.0"):
            integration.initialize()

            # Verify config was loaded from the custom path
            mock_config_provider.load_config.assert_called_once_with(
                "/path/to/config.yaml")


def test_integration_with_custom_output_dir():
    """Test PandocIntegration with custom output directory."""
    integration = PandocIntegration(output_dir="/custom/output")

    # Initialize with proper mocks
    with patch('quack_core.paths.service', MagicMock()), \
            patch('quack_core.integrations.pandoc.service.verify_pandoc',
                  return_value="2.11.0"), \
            patch('quack_core.fs.service.standalone.create_directory',
                  return_value=SimpleNamespace(success=True)):
        result = integration.initialize()
        assert result.success

        # Check if output_dir was set correctly in config
        assert integration.output_dir == "/custom/output"
        if integration.converter and integration.converter.config:
            assert integration.converter.config.output_dir == "/custom/output"


def test_integration_initialize_with_invalid_config():
    """Test initialization with invalid configuration."""
    integration = PandocIntegration()

    # Set invalid config explicitly
    integration.config = {"invalid_key": "value"}

    # Mock the validate_config method to actually check our invalid config
    with patch(
            'quack_core.integrations.pandoc.config.PandocConfigProvider.validate_config',
            return_value=False):
        # Initialize - should fail on config validation
        result = integration.initialize()

        assert not result.success
        assert "Invalid configuration" in result.error


@patch('quack_core.fs.service.standalone')
def test_integration_directory_conversion_edge_cases(mock_fs):
    """Test directory conversion edge cases."""
    integration = PandocIntegration()

    # Initialize with proper mocks
    with patch('quack_core.paths.service', MagicMock()), \
            patch('quack_core.integrations.pandoc.service.verify_pandoc',
                  return_value="2.11.0"), \
            patch('quack_core.fs.service.standalone.create_directory',
                  return_value=SimpleNamespace(success=True)):
        result = integration.initialize()
        assert result.success

    # Test with input directory not existing
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=False, is_dir=False
    )

    result = integration.convert_directory("input_dir", "markdown")
    assert not result.success
    assert "directory does not exist" in result.error or "not found" in result.error

    # Test with no matching files
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=True
    )
    mock_fs.find_files.return_value = SimpleNamespace(
        success=True, files=[]
    )

    result = integration.convert_directory("input_dir", "markdown")
    assert not result.success
    assert "No matching files found" in result.error

    # Test with find_files operation failing
    mock_fs.find_files.return_value = SimpleNamespace(
        success=False, error="Find operation failed"
    )

    result = integration.convert_directory("input_dir", "markdown")
    assert not result.success
    assert "Failed to find files" in result.error

    # Test with unsupported output format
    mock_fs.find_files.return_value = SimpleNamespace(
        success=True, files=["file1.html"]
    )

    result = integration.convert_directory("input_dir", "pdf")  # Unsupported format
    assert not result.success
    assert "Unsupported output format" in result.error


def test_integration_determine_conversion_params():
    """Test the _determine_conversion_params method."""
    integration = PandocIntegration()

    # Test supported formats
    markdown_params = integration._determine_conversion_params("markdown", None)
    assert markdown_params == ("html", "*.html")

    docx_params = integration._determine_conversion_params("docx", None)
    assert docx_params == ("markdown", "*.md")

    # Test with custom file pattern
    custom_params = integration._determine_conversion_params("markdown", "*.htm")
    assert custom_params == ("html", "*.htm")

    # Test unsupported format
    unsupported = integration._determine_conversion_params("pdf", None)
    assert unsupported is None


@patch('quack_core.integrations.pandoc.operations.get_file_info')
@patch('quack_core.fs.service.standalone')
def test_integration_create_conversion_tasks(mock_fs, mock_get_file_info):
    """Test the _create_conversion_tasks method."""
    integration = PandocIntegration()

    # Mock filesystem operations
    mock_fs.split_path.return_value = SimpleNamespace(
        success=True, data=["path", "file1.html"]
    )
    mock_fs.join_path.return_value = SimpleNamespace(
        success=True, data="/output/dir/file1.md"
    )

    # Mock get_file_info to return valid info
    mock_get_file_info.return_value = FileInfo(
        path="file1.html", format="html", size=100, modified=None, extra_args=[]
    )

    # Test task creation for HTML to Markdown
    tasks = integration._create_conversion_tasks(
        ["file1.html", "file2.html"],
        "html",
        "markdown",
        "/output/dir"
    )

    assert len(tasks) == 2
    assert tasks[0].source.path == "file1.html"
    assert tasks[0].target_format == "markdown"
    assert tasks[0].output_path is not None


def test_integration_get_metrics():
    """Test the get_metrics method."""
    integration = PandocIntegration()

    # Without initialization
    metrics = integration.get_metrics()
    assert isinstance(metrics, ConversionMetrics)
    assert metrics.successful_conversions == 0

    # After initialization with mocks
    with patch('quack_core.paths.service', MagicMock()), \
            patch('quack_core.integrations.pandoc.service.verify_pandoc',
                  return_value="2.11.0"), \
            patch('quack_core.fs.service.standalone.create_directory',
                  return_value=SimpleNamespace(success=True)):
        integration.initialize()

        # Manually set some metrics for testing
        if integration.converter:
            integration.converter.metrics.successful_conversions = 5
            integration.converter.metrics.failed_conversions = 2
            metrics = integration.get_metrics()
            assert metrics.successful_conversions == 5
            assert metrics.failed_conversions == 2


@patch('quack_core.fs.service.standalone')
@patch('quack_core.paths.service')
def test_mock_services_integration(mock_paths, mock_fs):
    """Test integration with mocked services."""
    # Setup mocks
    mock_fs.normalize_path.return_value = SimpleNamespace(success=True,
                                                          path="/resolved/path")
    mock_fs.get_file_info.return_value = SimpleNamespace(success=True, exists=True,
                                                         size=100)
    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.join_path.return_value = SimpleNamespace(success=True, data="/joined/path")
    mock_fs.read_text.return_value = SimpleNamespace(success=True,
                                                     content="HTML content")

    mock_paths.resolve_project_path.return_value = "/project/path"

    # Create integration with mocked config provider
    mock_config_provider = MagicMock()
    mock_config_provider.load_config.return_value = {}

    with patch('quack_core.integrations.pandoc.config.PandocConfigProvider',
               return_value=mock_config_provider):
        integration = PandocIntegration()

        # Initialize with mocked verify_pandoc
        with patch('quack_core.integrations.pandoc.service.verify_pandoc',
                   return_value="2.11.0"):
            init_result = integration.initialize()
            assert init_result.success

        # Mock converter methods for testing
        if integration.converter:
            integration.converter.convert_file = MagicMock(
                return_value=IntegrationResult.success_result("output.md"))

        # Test HTML to Markdown conversion
        result = integration.html_to_markdown("input.html")
        assert result.success
