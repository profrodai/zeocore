# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/pandoc/test_models.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test-pandoc-integration-full.py, test_config.py, test_converter.py (+4 more)
# exports: test_file_info_initialization, test_conversion_task_initialization, test_conversion_metrics_initialization, test_conversion_details_initialization
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Tests for data models used in the pandoc integration.

This module contains unit tests for the data model classes used
by the pandoc integration module, such as FileInfo, ConversionTask,
ConversionMetrics, and ConversionDetails.
"""

from datetime import datetime

from quack_core.integrations.pandoc.models import (
    ConversionDetails,
    ConversionMetrics,
    ConversionTask,
    FileInfo,
)


def test_file_info_initialization():
    """Test initialization of FileInfo model."""
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
    """Test initialization of ConversionTask model."""
    file_info = FileInfo(path="/path/to/file.html", format="html")

    # With output path
    task = ConversionTask(
        source=file_info,
        target_format="markdown",
        output_path="/path/to/output.md"
    )
    assert task.source == file_info
    assert task.target_format == "markdown"
    assert task.output_path == "/path/to/output.md"

    # Without output path
    task = ConversionTask(
        source=file_info,
        target_format="markdown"
    )
    assert task.source == file_info
    assert task.target_format == "markdown"
    assert task.output_path is None


def test_conversion_metrics_initialization():
    """Test initialization of ConversionMetrics model."""
    # Default initialization
    metrics = ConversionMetrics()
    assert isinstance(metrics.conversion_times, dict)
    assert isinstance(metrics.file_sizes, dict)
    assert isinstance(metrics.errors, dict)
    assert isinstance(metrics.start_time, datetime)
    assert metrics.total_attempts == 0
    assert metrics.successful_conversions == 0
    assert metrics.failed_conversions == 0

    # With custom values
    custom_time = datetime(2023, 1, 1, 12, 0, 0)
    metrics = ConversionMetrics(
        start_time=custom_time,
        total_attempts=5,
        successful_conversions=3,
        failed_conversions=2
    )
    assert metrics.start_time == custom_time
    assert metrics.total_attempts == 5
    assert metrics.successful_conversions == 3
    assert metrics.failed_conversions == 2


def test_conversion_details_initialization():
    """Test initialization of ConversionDetails model."""
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
