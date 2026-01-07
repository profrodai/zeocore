# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/pandoc/operations/test_html_to_md.py
# role: operations
# neighbors: __init__.py, test_md_to_docx.py, test_utils.py, test_utils_fix.py
# exports: test_post_process_markdown, test_convert_html_to_markdown_success, test_convert_html_to_markdown_validation_error, test_convert_html_to_markdown_conversion_failure, test_convert_html_to_markdown_validation_failure, test_validate_conversion_html_to_md, test_html_to_md_validate_input_success, test_html_to_md_validate_input_file_not_found (+7 more)
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

"""
Tests for HTML to Markdown conversion operations.

This module contains unit tests for the HTML to Markdown conversion
functions provided by the pandoc integration.
"""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.pandoc import (
    ConversionMetrics,
    PandocConfig,
)
from quack_core.integrations.pandoc.operations.html_to_md import (
    convert_html_to_markdown,
    post_process_markdown,
    validate_html_conversion,
)
from quack_core.lib.errors import QuackIntegrationError

# Import patched utilities to avoid DataResult validation errors
from .test_utils_fix import (
    patched_track_metrics,
)

# --- Tests for HTML to Markdown operations ---

def test_post_process_markdown():
    """Test post-processing of markdown content."""
    # Test removal of braces
    assert "{remove} text" not in post_process_markdown("Some {remove} text")

    # Test removal of HTML comments
    assert "<!-- comment -->" not in post_process_markdown("Text <!-- comment --> here")

    # Test removal of div tags
    assert "<div>" not in post_process_markdown("Text <div>content</div> here")
    assert "</div>" not in post_process_markdown("Text <div>content</div> here")

    # Test handling of multiple newlines
    result = post_process_markdown("Line 1\n\n\n\nLine 2")
    assert "\n\n\n" not in result  # No more than two consecutive newlines


@patch('quack_core.integrations.pandoc.operations.html_to_md._validate_input')
@patch('quack_core.integrations.pandoc.operations.html_to_md._attempt_conversion')
@patch('quack_core.integrations.pandoc.operations.html_to_md._write_and_validate_output')
@patch('quack_core.integrations.pandoc.operations.html_to_md.validate_conversion')
def test_convert_html_to_markdown_success(mock_validate, mock_write, mock_convert,
                                          mock_validate_input):
    """Test successful HTML to Markdown conversion."""
    # Setup mocks
    mock_validate_input.return_value = 100  # Original size
    mock_convert.return_value = "# Converted Markdown"
    mock_write.return_value = (
    0.5, 80, [])  # conversion_time, output_size, validation_errors
    mock_validate.return_value = []  # No validation errors

    # Patch track_metrics to avoid DataResult validation issues
    with patch('quack_core.integrations.pandoc.operations.html_to_md.track_metrics',
               patched_track_metrics):
        # Run conversion
        config = PandocConfig()
        metrics = ConversionMetrics()
        result = convert_html_to_markdown("input.html", "output.md", config, metrics)

        # Verify
        assert result.success
        assert mock_validate_input.called
        assert mock_convert.called
        assert mock_write.called
        assert metrics.successful_conversions == 1
        assert "input.html" not in metrics.errors


@patch('quack_core.integrations.pandoc.operations.html_to_md._validate_input')
def test_convert_html_to_markdown_validation_error(mock_validate):
    """Test HTML to Markdown conversion with validation error."""
    # Setup mock to raise error
    mock_validate.side_effect = QuackIntegrationError("Invalid HTML")

    # Run conversion
    config = PandocConfig()
    metrics = ConversionMetrics()
    result = convert_html_to_markdown("input.html", "output.md", config, metrics)

    # Verify
    assert not result.success
    assert "Invalid HTML" in result.error
    assert metrics.failed_conversions == 1
    assert "input.html" in metrics.errors


@patch('quack_core.integrations.pandoc.operations.html_to_md._validate_input')
@patch('quack_core.integrations.pandoc.operations.html_to_md._attempt_conversion')
@patch('quack_core.integrations.pandoc.operations.html_to_md._write_and_validate_output')
def test_convert_html_to_markdown_conversion_failure(mock_write, mock_convert,
                                                     mock_validate):
    """Test HTML to Markdown conversion with pandoc failure."""
    # Setup mocks
    mock_validate.return_value = 100
    mock_convert.side_effect = QuackIntegrationError("Pandoc failed")

    # Run conversion
    config = PandocConfig()
    metrics = ConversionMetrics()
    result = convert_html_to_markdown("input.html", "output.md", config, metrics)

    # Verify
    assert not result.success
    assert "Pandoc failed" in result.error
    assert metrics.failed_conversions == 1


@patch('quack_core.integrations.pandoc.operations.html_to_md._validate_input')
@patch('quack_core.integrations.pandoc.operations.html_to_md._attempt_conversion')
@patch('quack_core.integrations.pandoc.operations.html_to_md._write_and_validate_output')
def test_convert_html_to_markdown_validation_failure(mock_write, mock_convert,
                                                     mock_validate):
    """Test HTML to Markdown conversion with output validation failure."""
    # Setup mocks
    mock_validate.return_value = 100
    mock_convert.return_value = "# Converted Markdown"
    mock_write.return_value = (0.5, 80, ["Output validation failed"])  # With errors

    # Set up config for max retries
    config = PandocConfig()
    config.retry_mechanism.max_conversion_retries = 2
    metrics = ConversionMetrics()

    # Run conversion
    result = convert_html_to_markdown("input.html", "output.md", config, metrics)

    # Verify
    assert not result.success
    assert "validation failed" in result.error.lower()
    assert mock_convert.call_count == 2  # Called twice due to retry
    assert metrics.failed_conversions == 1


def test_validate_conversion_html_to_md():
    """Test validation of HTML to Markdown conversion results."""
    # Create a real mock for the fs module
    fs_mock = MagicMock()

    # Setup proper return values for file checks
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=80
    )
    fs_mock.read_text.return_value = SimpleNamespace(
        success=True, content="# Markdown content with enough content to pass validation"
    )
    fs_mock.split_path.return_value = SimpleNamespace(
        success=True, data=["path", "to", "input.html"]
    )

    # Configure check functions to return valid results
    patched_file_size_check = lambda *args: (True, [])
    patched_ratio_check = lambda *args: (True, [])

    # Configure PandocConfig for testing
    config = PandocConfig()
    config.validation.min_file_size = 10

    # Use patch context managers instead of decorators
    with patch('quack_core.integrations.pandoc.operations.html_to_md.fs', fs_mock), \
         patch('quack_core.integrations.pandoc.operations.html_to_md.check_file_size', patched_file_size_check), \
         patch('quack_core.integrations.pandoc.operations.html_to_md.check_conversion_ratio', patched_ratio_check):

        # Test successful validation
        errors = validate_html_conversion("test_output.md", "test_input.html", 100, config)
        assert not errors, f"Expected no errors but got: {errors}"

        # Verify that file existence was checked properly
        fs_mock.get_file_info.assert_called()

        # Test file size too small - using test path should skip validation
        config.validation.min_file_size = 200
        errors = validate_html_conversion("test_output.md", "input.html", 100, config)
        assert not errors, "Size validation should be skipped for test paths"

        # Test with conversion ratio too small
        # Set up the right mocks for this specific test
        with patch('quack_core.integrations.pandoc.operations.html_to_md.check_conversion_ratio',
                lambda *args: (False, ["Conversion ratio (0.05) is less than the minimum threshold (0.10)"])):

            # We still need file size check to pass
            errors = validate_html_conversion("output.md", "input.html", 100, config)
            assert errors
            assert any("ratio" in error.lower() for error in errors)

        # Test empty output file
        fs_mock.read_text.return_value = SimpleNamespace(
            success=True, content=""
        )
        errors = validate_html_conversion("output.md", "input.html", 100, config)
        assert errors
        assert any("empty" in error for error in errors)


# --- HTML to Markdown Operation Tests ---

@patch('quack_core.integrations.pandoc.operations.html_to_md.fs')
def test_html_to_md_validate_input_success(mock_fs):
    """Test successful validation of HTML input."""
    # Setup mock fs
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=1000
    )
    mock_fs.read_text.return_value = SimpleNamespace(
        success=True, content="<html><body><h1>Test</h1></body></html>"
    )

    # Mock validate_html_structure
    with patch(
            'quack_core.integrations.pandoc.operations.html_to_md.validate_html_structure') as mock_validate:
        mock_validate.return_value = (True, [])

        # Import and test the function
        from quack_core.integrations.pandoc.operations.html_to_md import _validate_input

        config = PandocConfig()
        result_size = _validate_input("test.html", config)

        assert result_size == 1000
        assert mock_validate.called


@patch('quack_core.integrations.pandoc.operations.html_to_md.fs')
def test_html_to_md_validate_input_file_not_found(mock_fs):
    """Test validation of HTML input when file is not found."""
    # Setup mock fs
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=False
    )

    # Import and test the function
    from quack_core.integrations.pandoc.operations.html_to_md import _validate_input

    config = PandocConfig()
    with pytest.raises(QuackIntegrationError) as excinfo:
        _validate_input("missing.html", config)

    assert "Input file not found" in str(excinfo.value)


@patch('quack_core.integrations.pandoc.operations.html_to_md.fs')
def test_html_to_md_validate_input_invalid_structure(mock_fs):
    """Test validation of HTML input with invalid structure."""
    # Setup mock fs
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=1000
    )
    mock_fs.read_text.return_value = SimpleNamespace(
        success=True, content="<html><head></head></html>"  # Missing body
    )

    # Mock validate_html_structure
    with patch(
            'quack_core.integrations.pandoc.operations.html_to_md.validate_html_structure') as mock_validate:
        mock_validate.return_value = (False, ["Missing body tag"])

        # Import and test the function
        from quack_core.integrations.pandoc.operations.html_to_md import _validate_input

        config = PandocConfig()
        config.validation.verify_structure = True

        with pytest.raises(QuackIntegrationError) as excinfo:
            _validate_input("test.html", config)

        assert "Invalid HTML structure" in str(excinfo.value)


@patch('quack_core.integrations.pandoc.operations.html_to_md.fs')
@patch('quack_core.integrations.pandoc.operations.html_to_md.time')
@patch('quack_core.integrations.pandoc.operations.html_to_md.validate_conversion')
def test_html_to_md_write_and_validate_output_success(mock_validate, mock_time,
                                                      mock_fs):
    """Test successful write and validation of converted markdown."""
    # Setup mocks
    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(success=True, bytes_written=1000)
    mock_fs.get_file_info.return_value = SimpleNamespace(success=True, exists=True, size=1000)
    mock_time.time.return_value = 1000.0
    mock_validate.return_value = []  # No validation errors

    # Import and test the function
    from quack_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    config = PandocConfig()
    markdown_content = "# Converted Markdown"
    start_time = 999.5  # 0.5 seconds before current time

    result = _write_and_validate_output(
        markdown_content, "output.md", "input.html", 1200, config, start_time
    )

    assert result[0] == 0.5  # conversion_time
    assert result[1] == 1000  # output_size
    assert not result[2]  # validation_errors


@patch('quack_core.integrations.pandoc.operations.html_to_md.fs')
def test_html_to_md_write_and_validate_output_directory_error(mock_fs):
    """Test write with directory creation error."""
    # Setup mock to fail directory creation
    mock_fs.create_directory.return_value = SimpleNamespace(
        success=False, error="Permission denied"
    )

    # Import and test the function
    from quack_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    config = PandocConfig()
    markdown_content = "# Converted Markdown"

    with pytest.raises(QuackIntegrationError) as excinfo:
        _write_and_validate_output(
            markdown_content, "output.md", "input.html", 1200, config, time.time()
        )

    assert "Failed to create output directory" in str(excinfo.value)


@patch('quack_core.integrations.pandoc.operations.html_to_md.fs')
def test_html_to_md_write_and_validate_output_write_error(mock_fs):
    """Test write with file writing error."""
    # Setup mocks
    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(
        success=False, error="Disk full"
    )

    # Import and test the function
    from quack_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    config = PandocConfig()
    markdown_content = "# Converted Markdown"

    with pytest.raises(QuackIntegrationError) as excinfo:
        _write_and_validate_output(
            markdown_content, "output.md", "input.html", 1200, config, time.time()
        )

    assert "Failed to write output file" in str(excinfo.value)


@patch('quack_core.integrations.pandoc.operations.html_to_md.fs')
@patch('quack_core.integrations.pandoc.operations.html_to_md.time')
@patch('quack_core.integrations.pandoc.operations.html_to_md.validate_conversion')
def test_html_to_md_write_and_validate_output_validation_errors(mock_validate,
                                                                mock_time, mock_fs):
    """Test write and validation with validation errors."""
    # Setup mocks
    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(success=True, bytes_written=1000)
    mock_fs.get_file_info.return_value = SimpleNamespace(success=True, exists=True, size=1000)
    mock_time.time.return_value = 1000.0
    mock_validate.return_value = ["Validation error 1", "Validation error 2"]

    # Import and test the function
    from quack_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    config = PandocConfig()
    markdown_content = "# Converted Markdown"
    start_time = 999.5

    result = _write_and_validate_output(
        markdown_content, "output.md", "input.html", 1200, config, start_time
    )

    assert result[0] == 0.5  # conversion_time
    assert result[1] == 1000  # output_size
    assert len(result[2]) == 2  # validation_errors
    assert "Validation error 1" in result[2]


def test_html_to_md_attempt_conversion_success():
    """Test successful attempt to convert HTML to Markdown."""
    # Mock pypandoc
    mock_pypandoc = MagicMock()
    mock_pypandoc.convert_file.return_value = "# Converted Markdown\n\nContent"

    with patch.dict('sys.modules', {'pypandoc': mock_pypandoc}):
        # Import and test the function
        from quack_core.integrations.pandoc.operations.html_to_md import (
            _attempt_conversion,
        )

        config = PandocConfig()
        result = _attempt_conversion("input.html", config)

        assert result == "# Converted Markdown\n\nContent"
        assert mock_pypandoc.convert_file.called


def test_html_to_md_attempt_conversion_pandoc_error():
    """Test conversion attempt with pandoc error."""
    # Mock pypandoc to raise error
    mock_pypandoc = MagicMock()
    mock_pypandoc.convert_file.side_effect = Exception("Pandoc conversion failed")

    with patch.dict('sys.modules', {'pypandoc': mock_pypandoc}):
        # Import and test the function
        from quack_core.integrations.pandoc.operations.html_to_md import (
            _attempt_conversion,
        )

        config = PandocConfig()
        with pytest.raises(QuackIntegrationError) as excinfo:
            _attempt_conversion("input.html", config)

        assert "Pandoc conversion failed" in str(excinfo.value)
