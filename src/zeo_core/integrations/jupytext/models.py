"""
Data models for the jupytext integration.

This module provides Pydantic models describing notebook conversion _ops
and results. File paths are represented as strings throughout, matching the
pandoc integration's convention -- path resolution and normalization are
delegated to zeo_core.core.fs.
"""

from pydantic import BaseModel, Field


class NotebookInfo(BaseModel):
    """Information about a notebook or paired-format source file."""

    path: str = Field(..., description="Path to the file, as a string")
    format: str = Field(
        ..., description="Jupytext format id, e.g. 'py:percent', 'ipynb', 'md'"
    )
    size: int = Field(default=0, description="File size in bytes")
    cell_count: int | None = Field(
        default=None, description="Number of cells in the parsed notebook"
    )


class ConversionDetails(BaseModel):
    """Detailed information about a notebook conversion operation."""

    source_format: str | None = Field(default=None, description="Source format id")
    target_format: str | None = Field(default=None, description="Target format id")
    conversion_time: float | None = Field(
        default=None, description="Conversion time in seconds"
    )
    output_size: int | None = Field(
        default=None, description="Output file size in bytes"
    )
    input_size: int | None = Field(default=None, description="Input file size in bytes")
    cell_count: int | None = Field(
        default=None, description="Number of cells in the converted notebook"
    )
    validation_errors: list[str] = Field(
        default_factory=list, description="Document validation errors"
    )


class ConversionTask(BaseModel):
    """Represents a single notebook conversion task, for batch conversion."""

    source: NotebookInfo = Field(..., description="Source file information")
    target_format: str = Field(
        ..., description="Target jupytext format id, e.g. 'ipynb' or 'py:percent'"
    )
    output_path: str | None = Field(
        default=None, description="Output file path (if provided), as a string"
    )
