"""
Tests for HTML to Markdown conversion _ops.

This module contains unit tests for the HTML to Markdown conversion
functions provided by the pandoc integration.
"""

import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.integrations.pandoc import (
    ConversionMetrics,
    PandocConfig,
)
from zeo_core.integrations.pandoc.operations.html_to_md import (
    convert_html_to_markdown,
    post_process_markdown,
    validate_html_conversion,
)

# Import patched utilities to avoid DataResult validation errors
from .test_utils_fix import (
    patched_track_metrics,
)

# --- Tests for HTML to Markdown _ops ---


def test_post_process_markdown() -> None:
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


@patch("zeo_core.integrations.pandoc.operations.html_to_md._validate_input")
@patch("zeo_core.integrations.pandoc.operations.html_to_md._attempt_conversion")
@patch(
    "zeo_core.integrations.pandoc.operations.html_to_md._write_and_validate_output"
)
@patch("zeo_core.integrations.pandoc.operations.html_to_md.validate_conversion")
def test_convert_html_to_markdown_success(
    mock_validate: MagicMock,
    mock_write: MagicMock,
    mock_convert: MagicMock,
    mock_validate_input: MagicMock,
) -> None:
    """Test successful HTML to Markdown conversion."""
    # Setup mocks
    mock_validate_input.return_value = 100  # Original size
    mock_convert.return_value = "# Converted Markdown"
    mock_write.return_value = (
        0.5,
        80,
        [],
    )  # conversion_time, output_size, validation_errors
    mock_validate.return_value = []  # No validation errors

    # Patch track_metrics to avoid DataResult validation issues
    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.track_metrics",
        patched_track_metrics,
    ):
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


@patch("zeo_core.integrations.pandoc.operations.html_to_md._validate_input")
@patch("zeo_core.integrations.pandoc.operations.html_to_md._attempt_conversion")
@patch(
    "zeo_core.integrations.pandoc.operations.html_to_md._write_and_validate_output"
)
def test_convert_html_to_markdown_split_path_raises_falls_back_to_html_path(
    mock_write: MagicMock,
    mock_convert: MagicMock,
    mock_validate_input: MagicMock,
) -> None:
    """When fs.split_path itself raises, convert_html_to_markdown's filename
    resolution falls all the way back to the raw html_path
    (html_to_md.py:299-301), and conversion still proceeds successfully."""
    mock_validate_input.return_value = 100
    mock_convert.return_value = "# Converted Markdown"
    mock_write.return_value = (0.5, 80, [])

    with (
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md.fs"
        ) as mock_fs,
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md.track_metrics",
            patched_track_metrics,
        ),
    ):
        mock_fs.split_path.side_effect = RuntimeError("split blew up")

        config = PandocConfig()
        metrics = ConversionMetrics()
        result = convert_html_to_markdown(
            "weird/input.html", "output.md", config, metrics
        )

        assert result.success


@patch("zeo_core.integrations.pandoc.operations.html_to_md._validate_input")
@patch("zeo_core.integrations.pandoc.operations.html_to_md._attempt_conversion")
@patch(
    "zeo_core.integrations.pandoc.operations.html_to_md._write_and_validate_output"
)
def test_convert_html_to_markdown_split_path_unsuccessful_uses_basename(
    mock_write: MagicMock,
    mock_convert: MagicMock,
    mock_validate_input: MagicMock,
) -> None:
    """When fs.split_path reports success=False (rather than raising),
    convert_html_to_markdown falls back to os.path.basename
    (html_to_md.py:296-298)."""
    mock_validate_input.return_value = 100
    mock_convert.return_value = "# Converted Markdown"
    mock_write.return_value = (0.5, 80, [])

    with (
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md.fs"
        ) as mock_fs,
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md.track_metrics",
            patched_track_metrics,
        ),
    ):
        mock_fs.split_path.return_value = SimpleNamespace(success=False)

        config = PandocConfig()
        metrics = ConversionMetrics()
        result = convert_html_to_markdown(
            "weird/dir/input.html", "output.md", config, metrics
        )

        assert result.success


@patch("zeo_core.integrations.pandoc.operations.html_to_md._validate_input")
def test_convert_html_to_markdown_zero_max_retries_falls_through_loop(
    mock_validate_input: MagicMock,
) -> None:
    """With max_conversion_retries configured to 0, `range(1, 1)` is empty so
    the retry loop's body never executes and control falls through to the
    trailing "Conversion failed after maximum retries" return
    (html_to_md.py:373). This line is otherwise unreachable in normal
    operation since every loop iteration returns before looping past
    attempt == max_retries -- only a misconfigured (non-positive) retry
    count exposes it."""
    mock_validate_input.return_value = 100

    config = PandocConfig()
    config.retry_mechanism.max_conversion_retries = 0
    metrics = ConversionMetrics()

    result = convert_html_to_markdown("input.html", "output.md", config, metrics)

    assert not result.success
    assert result.error == "Conversion failed after maximum retries"


def test_convert_html_to_markdown_default_metrics_created_when_none() -> None:
    """When no metrics tracker is passed, convert_html_to_markdown creates
    its own ConversionMetrics() instance internally (html_to_md.py:303-304)
    rather than raising an AttributeError on None.metrics access."""
    with (
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md._validate_input"
        ) as mock_validate_input,
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md._attempt_conversion"
        ) as mock_convert,
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md."
            "_write_and_validate_output"
        ) as mock_write,
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md.track_metrics",
            patched_track_metrics,
        ),
    ):
        mock_validate_input.return_value = 100
        mock_convert.return_value = "# Converted Markdown"
        mock_write.return_value = (0.5, 80, [])

        config = PandocConfig()
        # No metrics argument passed at all -- defaults to None internally.
        result = convert_html_to_markdown("input.html", "output.md", config)

        assert result.success


@patch("zeo_core.integrations.pandoc.operations.html_to_md._validate_input")
def test_convert_html_to_markdown_validation_error(mock_validate: MagicMock) -> None:
    """Test HTML to Markdown conversion with validation error."""
    # Setup mock to raise error
    mock_validate.side_effect = ZeoIntegrationError("Invalid HTML")

    # Run conversion
    config = PandocConfig()
    metrics = ConversionMetrics()
    result = convert_html_to_markdown("input.html", "output.md", config, metrics)

    # Verify
    assert not result.success
    assert result.error is not None
    assert "Invalid HTML" in result.error
    assert metrics.failed_conversions == 1
    assert "input.html" in metrics.errors


@patch("zeo_core.integrations.pandoc.operations.html_to_md._validate_input")
@patch("zeo_core.integrations.pandoc.operations.html_to_md._attempt_conversion")
@patch(
    "zeo_core.integrations.pandoc.operations.html_to_md._write_and_validate_output"
)
def test_convert_html_to_markdown_conversion_failure(
    mock_write: MagicMock, mock_convert: MagicMock, mock_validate: MagicMock
) -> None:
    """Test HTML to Markdown conversion with pandoc failure."""
    # Setup mocks
    mock_validate.return_value = 100
    mock_convert.side_effect = ZeoIntegrationError("Pandoc failed")

    # Run conversion
    config = PandocConfig()
    metrics = ConversionMetrics()
    result = convert_html_to_markdown("input.html", "output.md", config, metrics)

    # Verify
    assert not result.success
    assert result.error is not None
    assert "Pandoc failed" in result.error
    assert metrics.failed_conversions == 1


@patch("zeo_core.integrations.pandoc.operations.html_to_md._validate_input")
@patch("zeo_core.integrations.pandoc.operations.html_to_md._attempt_conversion")
@patch(
    "zeo_core.integrations.pandoc.operations.html_to_md._write_and_validate_output"
)
def test_convert_html_to_markdown_validation_failure(
    mock_write: MagicMock, mock_convert: MagicMock, mock_validate: MagicMock
) -> None:
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
    assert result.error is not None
    assert "validation failed" in result.error.lower()
    assert mock_convert.call_count == 2  # Called twice due to retry
    assert metrics.failed_conversions == 1


def test_validate_conversion_html_to_md() -> None:
    """Test validation of HTML to Markdown conversion results."""
    # Create a real mock for the fs module
    fs_mock = MagicMock()

    # Setup proper return values for file checks
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=80
    )
    fs_mock.read_text.return_value = SimpleNamespace(
        success=True,
        content="# Markdown content with enough content to pass validation",
    )
    fs_mock.split_path.return_value = SimpleNamespace(
        success=True, data=["path", "to", "input.html"]
    )

    # Configure check functions to return valid results
    def patched_file_size_check(
        *args: Any,  # noqa: ANN401 -- stand-in patch matching check_file_size's call signature
    ) -> tuple[bool, list[str]]:
        return (True, [])

    def patched_ratio_check(
        *args: Any,  # noqa: ANN401 -- stand-in patch matching check_conversion_ratio's call signature
    ) -> tuple[bool, list[str]]:
        return (True, [])

    # Configure PandocConfig for testing
    config = PandocConfig()
    config.validation.min_file_size = 10

    # Use patch context managers instead of decorators
    with (
        patch("zeo_core.integrations.pandoc.operations.html_to_md.fs", fs_mock),
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md.check_file_size",
            patched_file_size_check,
        ),
        patch(
            "zeo_core.integrations.pandoc.operations.html_to_md.check_conversion_ratio",
            patched_ratio_check,
        ),
    ):
        # Test successful validation
        errors = validate_html_conversion(
            "test_output.md", "test_input.html", 100, config
        )
        assert not errors, f"Expected no errors but got: {errors}"

        # Verify that file existence was checked properly
        fs_mock.get_file_info.assert_called()

        # Test file size too small - using test path should skip validation
        config.validation.min_file_size = 200
        errors = validate_html_conversion("test_output.md", "input.html", 100, config)
        assert not errors, "Size validation should be skipped for test paths"

        # Test with conversion ratio too small
        # Set up the right mocks for this specific test
        with patch(
            "zeo_core.integrations.pandoc.operations.html_to_md.check_conversion_ratio",
            lambda *args: (
                False,
                ["Conversion ratio (0.05) is less than the minimum threshold (0.10)"],
            ),
        ):
            # We still need file size check to pass
            errors = validate_html_conversion("output.md", "input.html", 100, config)
            assert errors
            assert any("ratio" in error.lower() for error in errors)

        # Test empty output file
        fs_mock.read_text.return_value = SimpleNamespace(success=True, content="")
        errors = validate_html_conversion("output.md", "input.html", 100, config)
        assert errors
        assert any("empty" in error for error in errors)


# --- HTML to Markdown Operation Tests ---


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_html_to_md_validate_input_success(mock_fs: MagicMock) -> None:
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
        "zeo_core.integrations.pandoc.operations.html_to_md.validate_html_structure"
    ) as mock_validate:
        mock_validate.return_value = (True, [])

        # Import and test the function
        from zeo_core.integrations.pandoc.operations.html_to_md import _validate_input

        config = PandocConfig()
        result_size = _validate_input("test.html", config)

        assert result_size == 1000
        assert mock_validate.called


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_html_to_md_validate_input_file_not_found(mock_fs: MagicMock) -> None:
    """Test validation of HTML input when file is not found."""
    # Setup mock fs
    mock_fs.get_file_info.return_value = SimpleNamespace(success=True, exists=False)

    # Import and test the function
    from zeo_core.integrations.pandoc.operations.html_to_md import _validate_input

    config = PandocConfig()
    with pytest.raises(ZeoIntegrationError) as excinfo:
        _validate_input("missing.html", config)

    assert "Input file not found" in str(excinfo.value)


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_html_to_md_validate_input_invalid_structure(mock_fs: MagicMock) -> None:
    """Test validation of HTML input with invalid structure."""
    # Setup mock fs
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=1000
    )
    mock_fs.read_text.return_value = SimpleNamespace(
        success=True,
        content="<html><head></head></html>",  # Missing body
    )

    # Mock validate_html_structure
    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.validate_html_structure"
    ) as mock_validate:
        mock_validate.return_value = (False, ["Missing body tag"])

        # Import and test the function
        from zeo_core.integrations.pandoc.operations.html_to_md import _validate_input

        config = PandocConfig()
        config.validation.verify_structure = True

        with pytest.raises(ZeoIntegrationError) as excinfo:
            _validate_input("test.html", config)

        assert "Invalid HTML structure" in str(excinfo.value)


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.time")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.validate_conversion")
def test_html_to_md_write_and_validate_output_success(
    mock_validate: MagicMock, mock_time: MagicMock, mock_fs: MagicMock
) -> None:
    """Test successful write and validation of converted markdown."""
    # Setup mocks
    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(success=True, bytes_written=1000)
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=1000
    )
    mock_time.time.return_value = 1000.0
    mock_validate.return_value = []  # No validation errors

    # Import and test the function
    from zeo_core.integrations.pandoc.operations.html_to_md import (
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


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_html_to_md_write_and_validate_output_directory_error(
    mock_fs: MagicMock,
) -> None:
    """Test write with directory creation error."""
    # Setup mock to fail directory creation
    mock_fs.create_directory.return_value = SimpleNamespace(
        success=False, error="Permission denied"
    )

    # Import and test the function
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    config = PandocConfig()
    markdown_content = "# Converted Markdown"

    with pytest.raises(ZeoIntegrationError) as excinfo:
        _write_and_validate_output(
            markdown_content, "output.md", "input.html", 1200, config, time.time()
        )

    assert "Failed to create output directory" in str(excinfo.value)


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_html_to_md_write_and_validate_output_write_error(mock_fs: MagicMock) -> None:
    """Test write with file writing error."""
    # Setup mocks
    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(success=False, error="Disk full")

    # Import and test the function
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    config = PandocConfig()
    markdown_content = "# Converted Markdown"

    with pytest.raises(ZeoIntegrationError) as excinfo:
        _write_and_validate_output(
            markdown_content, "output.md", "input.html", 1200, config, time.time()
        )

    assert "Failed to write output file" in str(excinfo.value)


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.time")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.validate_conversion")
def test_html_to_md_write_and_validate_output_validation_errors(
    mock_validate: MagicMock, mock_time: MagicMock, mock_fs: MagicMock
) -> None:
    """Test write and validation with validation errors."""
    # Setup mocks
    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(success=True, bytes_written=1000)
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=1000
    )
    mock_time.time.return_value = 1000.0
    mock_validate.return_value = ["Validation error 1", "Validation error 2"]

    # Import and test the function
    from zeo_core.integrations.pandoc.operations.html_to_md import (
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


def test_html_to_md_attempt_conversion_success() -> None:
    """Test successful attempt to convert HTML to Markdown."""
    # Mock pypandoc
    mock_pypandoc = MagicMock()
    mock_pypandoc.convert_file.return_value = "# Converted Markdown\n\nContent"

    with patch.dict("sys.modules", {"pypandoc": mock_pypandoc}):
        # Import and test the function
        from zeo_core.integrations.pandoc.operations.html_to_md import (
            _attempt_conversion,
        )

        config = PandocConfig()
        result = _attempt_conversion("input.html", config)

        assert result == "# Converted Markdown\n\nContent"
        assert mock_pypandoc.convert_file.called


def test_html_to_md_attempt_conversion_pandoc_error() -> None:
    """Test conversion attempt with pandoc error."""
    # Mock pypandoc to raise error
    mock_pypandoc = MagicMock()
    mock_pypandoc.convert_file.side_effect = Exception("Pandoc conversion failed")

    with patch.dict("sys.modules", {"pypandoc": mock_pypandoc}):
        # Import and test the function
        from zeo_core.integrations.pandoc.operations.html_to_md import (
            _attempt_conversion,
        )

        config = PandocConfig()
        with pytest.raises(ZeoIntegrationError) as excinfo:
            _attempt_conversion("input.html", config)

        assert "Pandoc conversion failed" in str(excinfo.value)


def test_html_to_md_attempt_conversion_pypandoc_not_installed() -> None:
    """When the pypandoc module itself cannot be imported, _attempt_conversion
    raises a ZeoIntegrationError naming the missing module
    (html_to_md.py:178-183)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _attempt_conversion,
    )

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.importlib.import_module"
    ) as mock_import:
        mock_import.side_effect = ImportError("No module named 'pypandoc'")

        config = PandocConfig()
        with pytest.raises(ZeoIntegrationError) as excinfo:
            _attempt_conversion("input.html", config)

        assert "pypandoc module is not installed" in str(excinfo.value)


# --- Additional coverage: _safe_file_size ---


def test_safe_file_size_int_convertible_via_dunder_int() -> None:
    """A size object exposing __int__ is coerced directly (html_to_md.py:80-81)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import _safe_file_size

    class IntLike:
        def __int__(self) -> int:
            return 42

    assert _safe_file_size(SimpleNamespace(size=IntLike())) == 42


def test_safe_file_size_str_convertible_without_dunder_int() -> None:
    """A size value without __int__ but not None falls through to str()
    coercion (html_to_md.py:82-83)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import _safe_file_size

    assert _safe_file_size(SimpleNamespace(size="512")) == 512


def test_safe_file_size_none_returns_zero() -> None:
    """A None size attribute returns 0 (html_to_md.py:84-85)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import _safe_file_size

    assert _safe_file_size(SimpleNamespace(size=None)) == 0


def test_safe_file_size_no_size_attribute_returns_zero() -> None:
    """An object with no "size" attribute at all returns 0 (html_to_md.py:86-87)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import _safe_file_size

    assert _safe_file_size(SimpleNamespace()) == 0


def test_safe_file_size_unconvertible_value_falls_back_to_default() -> None:
    """A size that raises ValueError/TypeError on conversion falls back to the
    1024-byte default and logs a warning (html_to_md.py:88-93)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import _safe_file_size

    class Unconvertible:
        def __str__(self) -> str:
            return "not-a-number"

    # No __int__, so falls to str(); "not-a-number" -> int() raises ValueError
    assert _safe_file_size(SimpleNamespace(size=Unconvertible())) == 1024


# --- Additional coverage: _verify_html_structure ---


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_verify_html_structure_read_fails_raises(mock_fs: MagicMock) -> None:
    """A failing fs.read_text raises ZeoIntegrationError naming the read
    error (html_to_md.py:109-112)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _verify_html_structure,
    )

    mock_fs.read_text.return_value = SimpleNamespace(
        success=False, error="Permission denied"
    )

    config = PandocConfig()
    with pytest.raises(ZeoIntegrationError) as excinfo:
        _verify_html_structure("test.html", config)

    assert "Could not read HTML file" in str(excinfo.value)
    assert "Permission denied" in str(excinfo.value)


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_verify_html_structure_non_string_content_skips_validation(
    mock_fs: MagicMock,
) -> None:
    """Non-string HTML content logs a warning and returns without raising
    (html_to_md.py:113-119)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _verify_html_structure,
    )

    mock_fs.read_text.return_value = SimpleNamespace(success=True, content=b"bytes")

    config = PandocConfig()
    # Should not raise despite content being non-str
    _verify_html_structure("test.html", config)


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_verify_html_structure_unexpected_exception_logged_not_raised(
    mock_fs: MagicMock,
) -> None:
    """A generic (non-ZeoIntegrationError) exception during structure
    validation is caught, logged as a warning, and swallowed
    (html_to_md.py:128-131)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _verify_html_structure,
    )

    mock_fs.read_text.return_value = SimpleNamespace(
        success=True, content="<html><body>ok</body></html>"
    )

    config = PandocConfig()
    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.validate_html_structure"
    ) as mock_validate:
        mock_validate.side_effect = RuntimeError("validator exploded")

        # Should not raise -- the generic exception is swallowed
        _verify_html_structure("test.html", config)


# --- Additional coverage: _validate_input skip-structure-check branch ---


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
def test_validate_input_skips_structure_check_when_disabled(
    mock_fs: MagicMock,
) -> None:
    """When config.validation.verify_structure is False, _validate_input
    returns the size immediately without calling _verify_html_structure
    (html_to_md.py:156-157)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import _validate_input

    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=500
    )

    config = PandocConfig()
    config.validation.verify_structure = False

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md._verify_html_structure"
    ) as mock_verify:
        result_size = _validate_input("test.html", config)

        assert result_size == 500
        assert not mock_verify.called


# --- Additional coverage: _write_and_validate_output branches ---


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.time")
def test_write_and_validate_output_get_file_info_fails_raises(
    mock_time: MagicMock, mock_fs: MagicMock
) -> None:
    """A failing fs.get_file_info on the freshly-written output file raises
    ZeoIntegrationError (html_to_md.py:234-238)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(success=True, bytes_written=100)
    mock_fs.get_file_info.return_value = SimpleNamespace(success=False)
    mock_time.time.return_value = 1000.0

    config = PandocConfig()
    with pytest.raises(ZeoIntegrationError) as excinfo:
        _write_and_validate_output(
            "# content", "output.md", "input.html", 100, config, 999.5
        )

    assert "Failed to get info for converted file" in str(excinfo.value)


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.time")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.validate_conversion")
def test_write_and_validate_output_bytes_written_unconvertible_falls_back(
    mock_validate: MagicMock, mock_time: MagicMock, mock_fs: MagicMock
) -> None:
    """When write_result.bytes_written cannot be converted to int, the
    ValueError/TypeError is caught and output_size falls through to the
    output_info.size branch instead (html_to_md.py:245-262)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(
        success=True, bytes_written="not-a-number"
    )
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size=777
    )
    mock_time.time.return_value = 1000.0
    mock_validate.return_value = []

    result = _write_and_validate_output(
        "# content", "output.md", "input.html", 100, PandocConfig(), 999.5
    )

    # bytes_written was unconvertible -> falls back to output_info.size (777)
    assert result[1] == 777


@patch("zeo_core.integrations.pandoc.operations.html_to_md.fs")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.time")
@patch("zeo_core.integrations.pandoc.operations.html_to_md.validate_conversion")
def test_write_and_validate_output_size_also_unconvertible_stays_zero(
    mock_validate: MagicMock, mock_time: MagicMock, mock_fs: MagicMock
) -> None:
    """When both bytes_written and output_info.size are unconvertible,
    output_size remains 0 and both warning branches are exercised
    (html_to_md.py:245-262)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _write_and_validate_output,
    )

    mock_fs.create_directory.return_value = SimpleNamespace(success=True)
    mock_fs.write_text.return_value = SimpleNamespace(
        success=True, bytes_written="nope"
    )
    mock_fs.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, size="also-nope"
    )
    mock_time.time.return_value = 1000.0
    mock_validate.return_value = []

    result = _write_and_validate_output(
        "# content", "output.md", "input.html", 100, PandocConfig(), 999.5
    )

    assert result[1] == 0


# --- Additional coverage: _resolve_output_size ---


def test_resolve_output_size_uses_reported_size_when_larger_content_absent() -> None:
    """_resolve_output_size prefers the reported size when the re-read
    content is not longer than it (html_to_md.py:433-439, happy path)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _resolve_output_size,
    )

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.return_value = SimpleNamespace(success=True, content="hi")
        output_info = SimpleNamespace(size=500)

        assert _resolve_output_size(output_info, "output.md") == 500


def test_resolve_output_size_unconvertible_size_falls_back_to_zero() -> None:
    """When output_info.size cannot be converted to int, _resolve_output_size
    logs a warning and treats the size as 0 before trying the content-length
    fallback (html_to_md.py:440-445)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _resolve_output_size,
    )

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.return_value = SimpleNamespace(success=True, content="")
        output_info = SimpleNamespace(size="not-a-number")

        assert _resolve_output_size(output_info, "output.md") == 0


def test_resolve_output_size_prefers_longer_read_back_content() -> None:
    """When re-reading the output file yields content longer than the
    reported size, the content length wins (html_to_md.py:447-455)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _resolve_output_size,
    )

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.return_value = SimpleNamespace(
            success=True, content="x" * 5000
        )
        output_info = SimpleNamespace(size=10)

        assert _resolve_output_size(output_info, "output.md") == 5000


def test_resolve_output_size_read_text_raises_keeps_reported_size() -> None:
    """An exception raised while re-reading the output file for size
    estimation is caught and logged, leaving the previously-resolved size
    intact (html_to_md.py:456-459)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _resolve_output_size,
    )

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.side_effect = OSError("cannot read back")
        output_info = SimpleNamespace(size=250)

        assert _resolve_output_size(output_info, "output.md") == 250


# --- Additional coverage: _validate_output_size_and_ratio ---


def test_validate_output_size_and_ratio_extends_size_errors_when_invalid() -> None:
    """When check_file_size reports invalid (outside test-env leniency), its
    error messages are appended to validation_errors (html_to_md.py:494-495)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _validate_output_size_and_ratio,
    )

    config = PandocConfig()
    config.validation.min_file_size = 1_000_000
    config.validation.conversion_ratio_threshold = 0.0  # ratio check passes trivially

    errors = _validate_output_size_and_ratio(
        output_size=10,
        original_size=100,
        config=config,
        is_test_environment=False,
    )

    assert errors
    assert any("below the minimum threshold" in e for e in errors)


# --- Additional coverage: _validate_output_content ---


def test_validate_output_content_read_fails_returns_error() -> None:
    """A failing fs.read_text on the output markdown short-circuits with a
    single "Error reading output file" message (html_to_md.py:522-527)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _validate_output_content,
    )

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.return_value = SimpleNamespace(
            success=False, error="disk error"
        )

        config = PandocConfig()
        errors = _validate_output_content("output.md", "input.html", config)

        assert len(errors) == 1
        assert "Error reading output file" in errors[0]
        assert "disk error" in errors[0]


def test_validate_output_content_minimal_content_flagged() -> None:
    """Very short content without a heading marker is flagged as minimal
    (html_to_md.py:531-533)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _validate_output_content,
    )

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.return_value = SimpleNamespace(success=True, content="hi")
        mock_fs.split_path.return_value = SimpleNamespace(
            success=True, data=["input.html"]
        )

        config = PandocConfig()
        errors = _validate_output_content("output.md", "input.html", config)

        assert any("minimal content" in e for e in errors)


def test_validate_output_content_missing_headers_flagged_when_verify_structure() -> (
    None
):
    """Large content lacking any '#'/'##' header is flagged only when
    config.validation.verify_structure is True (html_to_md.py:534-540)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _validate_output_content,
    )

    long_no_header_content = "word " * 50  # > 100 chars, no "# " or "## "

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.return_value = SimpleNamespace(
            success=True, content=long_no_header_content
        )
        mock_fs.split_path.return_value = SimpleNamespace(
            success=True, data=["input.html"]
        )

        config = PandocConfig()
        config.validation.verify_structure = True
        errors = _validate_output_content("output.md", "input.html", config)

        assert any("No headers found" in e for e in errors)

        # With verify_structure disabled, the same content only logs (no error)
        config.validation.verify_structure = False
        errors_lenient = _validate_output_content("output.md", "input.html", config)
        assert not any("No headers found" in e for e in errors_lenient)


def test_validate_output_content_check_links_missing_source_reference_logged() -> (
    None
):
    """When check_links is enabled and the source filename is absent from the
    converted content, a debug log fires but no validation error is added
    (html_to_md.py:542-550) -- content otherwise passes."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _validate_output_content,
    )

    content_with_header = "# Title\n\n" + ("word " * 30)

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.return_value = SimpleNamespace(
            success=True, content=content_with_header
        )
        mock_fs.split_path.return_value = SimpleNamespace(
            success=True, data=["source_input.html"]
        )

        config = PandocConfig()
        config.validation.check_links = True
        errors = _validate_output_content("output.md", "input.html", config)

        # No headers-missing error (has header) and no explicit "not found"
        # error is raised for the missing source reference -- it is logged only.
        assert not any("No headers found" in e for e in errors)


def test_validate_output_content_exception_appends_error() -> None:
    """An unexpected exception while validating output content is caught and
    turned into a validation error message (html_to_md.py:551-552)."""
    from zeo_core.integrations.pandoc.operations.html_to_md import (
        _validate_output_content,
    )

    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.read_text.side_effect = RuntimeError("content read exploded")

        config = PandocConfig()
        errors = _validate_output_content("output.md", "input.html", config)

        assert len(errors) == 1
        assert "content read exploded" in errors[0]


# --- Additional coverage: validate_conversion (module-level function) ---


def test_validate_conversion_test_env_debug_logged_when_file_missing() -> None:
    """In a detected test environment, a missing/failed get_file_info result
    is tolerated (logged, not failed) -- (html_to_md.py:582-586)."""
    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.get_file_info.return_value = SimpleNamespace(
            success=False, exists=False
        )
        mock_fs.read_text.return_value = SimpleNamespace(
            success=True, content="# Title\n\nSome test content here."
        )
        mock_fs.split_path.return_value = SimpleNamespace(
            success=True, data=["input.html"]
        )

        config = PandocConfig()
        config.validation.min_file_size = 5

        # "test" appears in both paths, so _is_test_environment is True and
        # the missing-file report from fs.get_file_info is tolerated rather
        # than causing an immediate failure.
        errors = validate_html_conversion(
            "test_output.md", "test_input.html", 100, config
        )

        # No "does not exist" error, since test-env leniency applies.
        assert not any("does not exist" in e for e in errors)


def test_validate_conversion_non_test_env_missing_file_returns_error() -> None:
    """Outside a detected test environment, a missing output file causes an
    immediate, single-item error list (html_to_md.py:590-592)."""
    with patch(
        "zeo_core.integrations.pandoc.operations.html_to_md.fs"
    ) as mock_fs:
        mock_fs.get_file_info.return_value = SimpleNamespace(
            success=True, exists=False
        )

        config = PandocConfig()
        config.validation.min_file_size = 1000  # keep >= 20 so not test-like

        errors = validate_html_conversion(
            "/real/path/output.md", "/real/path/input.html", 100, config
        )

        assert errors == ["Output file does not exist: /real/path/output.md"]
