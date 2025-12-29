# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/pandoc/models.py
# module: quack_core.integrations.pandoc.models
# role: models
# neighbors: __init__.py, service.py, protocols.py, config.py, converter.py
# exports: ConversionMetrics, FileInfo, ConversionTask, ConversionDetails
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===

"""
Data models for Pandoc integration.

This module provides Pydantic models for representing conversion _operations,
metrics, and results for document format conversions using Pandoc.
In this refactored version, file paths are represented as strings rather than
Path objects. All path resolution and normalization is delegated to quack_core.lib.fs.
"""

from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")  # Generic type for flexible typing


class ConversionMetrics(BaseModel):
    """Metrics for document conversion _operations."""

    conversion_times: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Dictionary mapping filenames to conversion time details",
    )
    file_sizes: dict[str, dict[str, int | float]] = Field(
        default_factory=dict,
        description="Dictionary mapping filenames to file size details",
    )
    errors: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary mapping filenames to error messages",
    )
    start_time: datetime = Field(
        default_factory=datetime.now,
        description="Time when metrics collection started",
    )
    total_attempts: int = Field(
        default=0, description="Total number of conversion attempts"
    )
    successful_conversions: int = Field(
        default=0, description="Number of successful conversions"
    )
    failed_conversions: int = Field(
        default=0, description="Number of failed conversions"
    )


class FileInfo(BaseModel):
    """Information about a file for conversion.

    The 'path' field is now a string representing the file path.
    """

    path: str = Field(..., description="Path to the file, as a string")
    format: str = Field(..., description="File format")
    size: int = Field(default=0, description="File size in bytes")
    modified: float | None = Field(default=None, description="Last modified timestamp")
    extra_args: list[str] = Field(
        default_factory=list, description="Extra arguments for pandoc"
    )


class ConversionTask(BaseModel):
    """Represents a document conversion task.

    The source file information uses a string for its path, and if provided,
    the output_path is also a string.
    """

    source: FileInfo = Field(..., description="Source file information")
    target_format: str = Field(..., description="Target conversion format")
    output_path: str | None = Field(
        default=None, description="Output file path (if provided), as a string"
    )


class ConversionDetails(BaseModel):
    """Detailed information about a conversion operation."""

    source_format: str | None = Field(default=None, description="Source file format")
    target_format: str | None = Field(default=None, description="Target file format")
    conversion_time: float | None = Field(
        default=None, description="Conversion time in seconds"
    )
    output_size: int | None = Field(
        default=None, description="Output file size in bytes"
    )
    input_size: int | None = Field(default=None, description="Input file size in bytes")
    validation_errors: list[str] = Field(
        default_factory=list, description="Document validation errors"
    )
