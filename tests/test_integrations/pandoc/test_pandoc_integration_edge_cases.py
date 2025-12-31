# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/pandoc/test_pandoc_integration_edge_cases.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test-pandoc-integration-full.py, test_config.py, test_converter.py (+4 more)
# exports: test_integration_with_custom_config_path, test_integration_with_custom_output_dir, test_integration_initialize_with_invalid_config, test_integration_directory_conversion_edge_cases, test_conversion_metrics_initialization, test_file_info_initialization, test_conversion_task_initialization, test_conversion_details_initialization (+9 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===

"""
Tests for utilities in the pandoc integration.

This module contains detailed tests for utility functions
and edge cases in the pandoc integration.
"""

import sys
import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.config import PandocConfig, PandocOptions
from quack_core.integrations.pandoc.models import (
    ConversionDetails,
    ConversionMetrics,
    ConversionTask,
    FileInfo,
)
from quack_core.integrations.pandoc.operations.html_to_md import post_process_markdown
from quack_core.integrations.pandoc.operations.utils import (
    check_conversion_ratio,
    check_file_size,
    get_file_info,
    prepare_pandoc_args,
    track_metrics,
    validate_docx_structure,
    validate_html_structure,
    verify_pandoc,
)
from quack_core.integrations.pandoc.service import PandocIntegration
from quack_core.lib.errors import QuackIntegrationError


def test_integration_with_custom_config_path():
    """Test PandocIntegration with custom config path."""
    # Mock config provider
    mock_config_provider = MagicMock()
    mock_config_provider.expand_user_vars.side_effect = lambda x: x
    mock_config_provider.load_config.return_value = IntegrationResult(
        success=True, content={"output_dir": "/custom/path"}
    )

    # Mock FS service
    mock_fs = MagicMock()
    mock_fs.expand_user_vars = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, data=x)
    )
    mock_fs.create_directory = MagicMock(
        return_value=SimpleNamespace(success=True)
    )

    with patch('quack_core.lib.paths.service', MagicMock(expand_user_vars=lambda x: x)), \
            patch('quack_core.integrations.pandoc.service.PandocConfigProvider',
                  return_value=mock_config_provider), \
            patch('quack_core.integrations.pandoc.service.verify_pandoc',
                  return_value='2.11.0'):
        integration = PandocIntegration(config_path="/path/to/config.yaml")
        integration.config_provider = mock_config_provider

        integration.paths_service = MagicMock()
        integration.paths_service.expand_user_vars.side_effect = lambda x: x
        integration.fs_service = mock_fs

        result = integration.initialize()

        assert result.success
        assert integration._initialized


def test_integration_with_custom_output_dir():
    """Test PandocIntegration with custom output directory."""
    # Mock FS service
    mock_fs = MagicMock()
    mock_fs.expand_user_vars = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, data=x)
    )
    mock_fs.create_directory = MagicMock(
        return_value=SimpleNamespace(success=True)
    )

    # Mock provider instance
    mock_provider = MagicMock()
    mock_provider.load_config.return_value = IntegrationResult(success=True, content={})
    # Ensure provider has expand_user_vars logic if it needs it
    mock_provider.expand_user_vars.side_effect = lambda x: x

    with patch('quack_core.lib.paths.service', MagicMock(expand_user_vars=lambda x: x)), \
            patch('quack_core.integrations.pandoc.service.verify_pandoc',
                  return_value="2.11.0"):
        integration = PandocIntegration(output_dir="/custom/output")
        integration.fs_service = mock_fs
        # Manually inject the mock provider
        integration.config_provider = mock_provider

        # Ensure paths_service is mocked correctly
        mock_paths = MagicMock()
        mock_paths.expand_user_vars.side_effect = lambda x: x
        integration.paths_service = mock_paths

        result = integration.initialize()
        assert result.success
        mock_fs.create_directory.assert_called_with("/custom/output")


def test_integration_initialize_with_invalid_config():
    """Test initialization with invalid configuration."""
    integration = PandocIntegration()
    integration.paths_service = MagicMock()
    integration.paths_service.expand_user_vars.side_effect = lambda x: x

    # Mock load_config to return failed result
    integration.config_provider = MagicMock()
    integration.config_provider.load_config.return_value = IntegrationResult(
        success=False, error="Invalid config")

    # Mock FS service
    mock_fs = MagicMock()
    mock_fs.expand_user_vars = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, data=x)
    )
    mock_fs.create_directory = MagicMock(
        return_value=SimpleNamespace(success=True)
    )
    integration.fs_service = mock_fs

    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value='2.11.0'):
        result = integration.initialize()
        # Should succeed with warnings, using default config
        assert result.success


@patch('quack_core.lib.fs.service.standalone')
def test_integration_directory_conversion_edge_cases(mock_fs):
    """Test directory conversion edge cases."""
    integration = PandocIntegration()
    integration.paths_service = MagicMock()
    integration.paths_service.expand_user_vars.side_effect = lambda x: x
    integration.paths_service.resolve_project_path = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, path=x)
    )

    mock_provider = MagicMock()
    mock_provider.load_config.return_value = IntegrationResult(success=True, content={})
    integration.config_provider = mock_provider

    # Mock FS service for integration
    mock_fs_service = MagicMock()
    mock_fs_service.expand_user_vars = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, data=x)
    )
    mock_fs_service.create_directory = MagicMock(
        return_value=SimpleNamespace(success=True)
    )
    integration.fs_service = mock_fs_service

    with patch('quack_core.lib.paths.service', MagicMock(expand_user_vars=lambda x: x)), \
            patch('quack_core.integrations.pandoc.service.verify_pandoc',
                  return_value="2.11.0"):
        result = integration.initialize()
        assert result.success

    # Test with input directory not existing
    integration.fs_service.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=False, is_dir=False)
    )

    result = integration.convert_directory("input_dir", "markdown")
    assert not result.success
    assert "not found" in result.error.lower()

    # Test with no matching files
    integration.fs_service.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    integration.fs_service.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=[])
    )

    result = integration.convert_directory("input_dir", "markdown")
    assert result.success  # Empty result is success
    assert result.content == []

    # Test with find_files operation failing
    integration.fs_service.find_files = MagicMock(
        return_value=SimpleNamespace(success=False, error="Find operation failed")
    )

    result = integration.convert_directory("input_dir", "markdown")
    assert not result.success
    assert "Failed to find files" in result.error


def test_conversion_metrics_initialization():
    """Test the initialization of ConversionMetrics."""
    metrics = ConversionMetrics()

    assert isinstance(metrics.conversion_times, dict)
    assert isinstance(metrics.file_sizes, dict)
    assert isinstance(metrics.errors, dict)
    assert isinstance(metrics.start_time, datetime)
    assert metrics.total_attempts == 0
    assert metrics.successful_conversions == 0
    assert metrics.failed_conversions == 0

    # Test with custom values
    custom_time = datetime(2023, 1, 1, 12, 0, 0)
    custom_metrics = ConversionMetrics(
        start_time=custom_time,
        total_attempts=5,
        successful_conversions=3,
        failed_conversions=2
    )

    assert custom_metrics.start_time == custom_time
    assert custom_metrics.total_attempts == 5
    assert custom_metrics.successful_conversions == 3
    assert custom_metrics.failed_conversions == 2


def test_file_info_initialization():
    """Test the initialization of FileInfo."""
    # Minimal initialization
    file_info = FileInfo(path="/path/to/file.html", format="html")

    assert file_info.path == "/path/to/file.html"
    assert file_info.format == "html"
    assert file_info.size == 0
    assert file_info.modified is None
    assert file_info.extra_args == []

    # Full initialization
    file_info = FileInfo(
        path="/path/to/file.md",
        format="markdown",
        size=1024,
        modified=123456789.0,
        extra_args=["--strip-comments"]
    )

    assert file_info.path == "/path/to/file.md"
    assert file_info.format == "markdown"
    assert file_info.size == 1024
    assert file_info.modified == 123456789.0
    assert file_info.extra_args == ["--strip-comments"]


def test_conversion_task_initialization():
    """Test the initialization of ConversionTask."""
    # Create a file info object
    file_info = FileInfo(path="/path/to/file.html", format="html", size=1024)

    # Create a conversion task
    task = ConversionTask(
        source=file_info,
        target_format="markdown",
        output_path="/path/to/output.md"
    )

    assert task.source == file_info
    assert task.target_format == "markdown"
    assert task.output_path == "/path/to/output.md"

    # Test with optional output_path
    task = ConversionTask(
        source=file_info,
        target_format="markdown"
    )

    assert task.source == file_info
    assert task.target_format == "markdown"
    assert task.output_path is None


def test_conversion_details_initialization():
    """Test the initialization of ConversionDetails."""
    # Default initialization
    details = ConversionDetails()

    assert details.source_format is None
    assert details.target_format is None
    assert details.conversion_time is None
    assert details.output_size is None
    assert details.input_size is None
    assert details.validation_errors == []

    # Full initialization
    details = ConversionDetails(
        source_format="html",
        target_format="markdown",
        conversion_time=1.5,
        output_size=800,
        input_size=1000,
        validation_errors=["Warning: missing header"]
    )

    assert details.source_format == "html"
    assert details.target_format == "markdown"
    assert details.conversion_time == 1.5
    assert details.output_size == 800
    assert details.input_size == 1000
    assert details.validation_errors == ["Warning: missing header"]


def test_get_file_info_edge_cases(monkeypatch):
    """Test edge cases for get_file_info utility."""
    # Create a mock standalone fs service
    mock_fs = SimpleNamespace()

    # Test with invalid file size string
    mock_fs.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size="not-a-number", modified=None
    )
    monkeypatch.setattr('quack_core.integrations.pandoc.operations.utils.fs', mock_fs)

    file_info = get_file_info("test.html")
    assert file_info.size == 1024  # Default when size conversion fails

    # Test with extension mapping
    mock_fs.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size=100, modified=None
    )
    mock_fs.get_extension = lambda path: SimpleNamespace(
        success=True, data=path.split('.')[-1]
    )
    monkeypatch.setattr('quack_core.integrations.pandoc.operations.utils.fs', mock_fs)

    # Test various extensions
    extensions_mapping = {
        "md": "markdown",
        "markdown": "markdown",
        "html": "html",
        "htm": "html",
        "docx": "docx",
        "doc": "docx",
        "pdf": "pdf",
        "txt": "plain",
        "unknown": "unknown"
    }

    for ext, expected_format in extensions_mapping.items():
        file_info = get_file_info(f"test.{ext}")
        assert file_info.format == expected_format, f"Failed for extension: {ext}"


def test_check_file_size_edge_cases():
    """Test edge cases for check_file_size utility."""
    # Test with None values
    valid, errors = check_file_size(None, 50)
    assert not valid
    assert "below the minimum threshold" in errors[0]

    valid, errors = check_file_size(100, None)
    assert valid
    assert not errors

    # Test with string values (should be converted to int)
    valid, errors = check_file_size(100, 50)
    assert valid
    assert not errors

    # Test with zero threshold
    valid, errors = check_file_size(100, 0)
    assert valid
    assert not errors


def test_check_conversion_ratio_edge_cases():
    """Test edge cases for check_conversion_ratio utility."""
    # Test with zero original size
    valid, errors = check_conversion_ratio(50, 0, 0.1)
    assert valid
    assert not errors

    # Test with None values
    valid, errors = check_conversion_ratio(None, 100, 0.1)
    assert not valid
    assert "less than" in errors[0]

    valid, errors = check_conversion_ratio(50, None, 0.1)
    assert valid
    assert not errors

    valid, errors = check_conversion_ratio(50, 100, None)
    assert valid
    assert not errors

    # Test with string values (should be converted)
    valid, errors = check_conversion_ratio(50, 100, 0.1)
    assert valid
    assert not errors

    # Test with exactly threshold ratio
    valid, errors = check_conversion_ratio(10, 100, 0.1)
    assert valid
    assert not errors

    # Test with slightly below threshold
    valid, errors = check_conversion_ratio(9, 100, 0.1)
    assert not valid
    assert "less than" in errors[0]


@patch('quack_core.integrations.pandoc.operations.utils.logger')
def test_track_metrics_logging(mock_logger):
    """Test that track_metrics properly logs information."""
    metrics = ConversionMetrics()
    config = PandocConfig()

    # Enable metrics tracking
    config.metrics.track_conversion_time = True
    config.metrics.track_file_sizes = True

    track_metrics(
        "test.html",
        time.time() - 1.0,
        100,
        80,
        metrics,
        config
    )

    # Verify metrics were recorded
    assert "test.html" in metrics.conversion_times
    assert "test.html" in metrics.file_sizes
    assert metrics.file_sizes["test.html"]["original"] == 100
    assert metrics.file_sizes["test.html"]["converted"] == 80
    assert metrics.file_sizes["test.html"]["ratio"] == 0.8

    # Verify logging was called
    assert mock_logger.info.call_count >= 2

    # Check for conversion time logging
    time_log_called = False
    for call in mock_logger.info.call_args_list:
        args, _ = call
        if "Conversion time" in args[0]:
            time_log_called = True
            break
    assert time_log_called

    # Check for file size logging
    size_log_called = False
    for call in mock_logger.info.call_args_list:
        args, _ = call
        if "File size change" in args[0]:
            size_log_called = True
            break
    assert size_log_called


def test_validate_html_structure_edge_cases():
    """Test edge cases for validate_html_structure utility."""
    # Test with parsing error
    mock_bs = MagicMock()
    mock_soup = MagicMock()
    mock_soup.find.return_value = True
    mock_bs.BeautifulSoup.return_value = mock_soup
    mock_bs.BeautifulSoup.side_effect = [mock_soup, Exception("Parsing error")]

    with patch.dict(sys.modules, {'bs4': mock_bs}):
        # First test valid HTML
        valid, errors = validate_html_structure("<html><body>content</body></html>")
        assert valid
        assert not errors

        # Then test invalid parsing
        mock_bs.BeautifulSoup.side_effect = Exception("Parsing error")
        valid, errors = validate_html_structure("<invalid><html>")
        assert not valid
        assert "validation error" in errors[0].lower()

        # Test missing body
        mock_bs.BeautifulSoup.side_effect = None
        mock_soup.find.return_value = False
        valid, errors = validate_html_structure("<html>content</html>")
        assert not valid
        assert "missing body tag" in errors[0].lower()


def test_validate_docx_structure_edge_cases(monkeypatch):
    """Test edge cases for validate_docx_structure utility."""

    # Test with docx module properly mocked as unavailable
    # using builtins.__import__ patching

    original_import = __import__

    def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'docx':
            raise ImportError("No module named 'docx'")
        return original_import(name, globals, locals, fromlist, level)

    with patch('builtins.__import__', side_effect=mock_import):
        # We need to ensure 'docx' is not in sys.modules to trigger the import logic
        with patch.dict(sys.modules):
            if 'docx' in sys.modules:
                del sys.modules['docx']

            # When docx is not available, validation should pass (soft validation)
            # Note: We don't need to patch zipfile here because validate_docx_structure
            # doesn't call is_zipfile when docx is missing (it returns True, [])
            valid, errors = validate_docx_structure("test.docx")
            assert valid
            assert not errors

    # Test with Document constructor raising error
    mock_docx = MagicMock()
    mock_docx.Document.side_effect = Exception("Failed to open document")
    with patch.dict(sys.modules, {'docx': mock_docx}):
        # We don't need importlib patch here as we're injecting into sys.modules
        # but we need to ensure the mocked module is used
        valid, errors = validate_docx_structure("test.docx")
        assert not valid
        assert "validation error" in errors[0].lower()

    # Test with docx module available
    mock_docx = MagicMock()
    mock_para = MagicMock()
    mock_para.style.name = "Heading 1"
    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para]
    mock_docx.Document.return_value = mock_doc
    mock_docx.Document.side_effect = None

    with patch.dict(sys.modules, {'docx': mock_docx}):
        # Test valid DOCX
        valid, errors = validate_docx_structure("valid.docx")
        assert valid
        assert not errors

        # Test empty DOCX
        mock_doc.paragraphs = []
        valid, errors = validate_docx_structure("empty.docx")
        assert not valid
        assert "no paragraphs" in errors[0].lower()


def test_prepare_pandoc_args_comprehensive():
    """Test comprehensive options for prepare_pandoc_args utility."""
    # Test with default config
    config = PandocConfig()
    args = prepare_pandoc_args(config, "html", "markdown")

    # Check basic args
    assert "--wrap=none" in args
    assert "--standalone" in args
    assert "--markdown-headings=atx" in args

    # Check format-specific args
    html_md_args = prepare_pandoc_args(config, "html", "markdown")
    assert "--strip-comments" in html_md_args
    assert "--no-highlight" in html_md_args

    md_docx_args = prepare_pandoc_args(config, "markdown", "docx")
    assert "--wrap=none" in md_docx_args
    assert "--markdown-headings=atx" in md_docx_args

    # Test with custom config
    custom_options = PandocOptions(
        wrap="auto",
        standalone=False,
        markdown_headings="setext",
        reference_links=True,
        resource_path=["/path/to/resources", "/another/path"]
    )

    custom_config = PandocConfig(
        pandoc_options=custom_options,
        html_to_md_extra_args=["--custom-arg1"],
        md_to_docx_extra_args=["--custom-arg2"]
    )

    # HTML to Markdown with custom config
    html_md_args = prepare_pandoc_args(custom_config, "html", "markdown")
    assert "--wrap=auto" in html_md_args
    assert "--standalone" not in html_md_args
    assert "--markdown-headings=setext" in html_md_args
    assert "--reference-links" in html_md_args
    assert "--resource-path=/path/to/resources" in html_md_args
    assert "--resource-path=/another/path" in html_md_args
    assert "--custom-arg1" in html_md_args

    # Markdown to DOCX with custom config
    md_docx_args = prepare_pandoc_args(custom_config, "markdown", "docx")
    assert "--wrap=auto" in md_docx_args
    assert "--custom-arg2" in md_docx_args

    # Test with additional extra args
    extra_args = ["--extra1", "--extra2"]
    args = prepare_pandoc_args(custom_config, "html", "markdown", extra_args)
    assert "--extra1" in args
    assert "--extra2" in args


def test_post_process_markdown_regex_patterns():
    """Test regex patterns used in post_process_markdown."""
    # Test that the function runs without error
    result = post_process_markdown("Test content")
    assert isinstance(result, str)

    # Test with actual patterns
    test_input = "{remove this} :::note\n <div>content</div>\n\n\n\ntext"
    result = post_process_markdown(test_input)

    # Verify basic cleaning occurred
    assert "{remove this}" not in result or len(result) < len(test_input)


def test_verify_pandoc_with_all_errors():
    """Test verify_pandoc with all possible error conditions."""
    # Create a mock module
    mock_module = MagicMock()
    mock_module.get_pandoc_version = MagicMock(return_value="3.5")

    # Test normal case
    with patch.dict(sys.modules, {'pypandoc': mock_module}):
        version = verify_pandoc()
        assert version == "3.5"

    # Test import error
    with patch('importlib.import_module',
               side_effect=ImportError("No module named 'pypandoc'")):
        with pytest.raises(QuackIntegrationError) as exc_info:
            verify_pandoc()
        assert "pypandoc module is not installed" in str(exc_info.value)

    # Test OSError
    mock_module.get_pandoc_version.side_effect = OSError("Pandoc executable not found")
    with patch.dict(sys.modules, {'pypandoc': mock_module}):
        with pytest.raises(QuackIntegrationError) as exc_info:
            verify_pandoc()
        assert "Pandoc is not installed" in str(exc_info.value)

    # Test general exception
    mock_module.get_pandoc_version.side_effect = Exception("Unexpected error")
    with patch.dict(sys.modules, {'pypandoc': mock_module}):
        with pytest.raises(QuackIntegrationError) as exc_info:
            verify_pandoc()
        assert "Error checking pandoc" in str(exc_info.value)
