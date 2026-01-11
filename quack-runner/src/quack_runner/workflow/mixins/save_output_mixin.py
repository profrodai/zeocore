# === QV-LLM:BEGIN ===
# path: quack-runner/src/quack_runner/workflow/mixins/save_output_mixin.py
# module: quack_runner.workflow.mixins.save_output_mixin
# role: module
# neighbors: __init__.py, output_writer.py
# exports: SaveOutputMixin
# git_branch: feat/9-make-setup-work
# git_commit: f85cce5a
# === QV-LLM:END ===



"""
⚠️ LEGACY - DEPRECATED - DO NOT USE ⚠️

LEGACY: Output saving mixin.

This mixin is for legacy FileWorkflowRunner only.
ToolRunner (v2.0+) handles output writing internally.

Deprecated: Will be removed in v4.0

For new code, use:
    from quack_runner.workflow import ToolRunner

DO NOT import from here - use quack_runner.workflow.legacy if needed.
"""

import warnings

# Issue loud deprecation warning (fix blocker #1)
warnings.warn(
    "quack_runner.workflow.mixins.save_output_mixin is LEGACY and deprecated. "
    "Use ToolRunner for new code. Import from quack_runner.workflow.legacy if you must use legacy. "
    "This module will be removed in v4.0.",
    DeprecationWarning,
    stacklevel=2
)

from collections.abc import Callable
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any, ClassVar
import csv

# Use new names
from quack_runner.workflow.output import (
    JsonOutputWriter,
    OutputWriter,
    YamlOutputWriter,
)


class SaveOutputMixin:
    """
    LEGACY: Mixin providing methods to save output in different formats.

    ⚠️ DEPRECATED - DO NOT USE IN NEW CODE ⚠️

    This is maintained for backward compatibility only.
    Performs I/O directly (doctrine violation - acceptable only because legacy).
    """

    _writers_cache: ClassVar[dict[str, OutputWriter]] = {}

    @property
    def _output_writers(self) -> dict[str, OutputWriter]:
        """Registry of available output writers."""
        if not hasattr(type(self), '_writers_cache'):
            type(self)._writers_cache = {
                "json": JsonOutputWriter(indent=2),
                "yaml": YamlOutputWriter(),
            }
        return type(self)._writers_cache

    def _get_csv_writer(self) -> Callable[[Any, Path], Path]:
        """Get a function that can write CSV output."""

        def write_csv(data: Any, path: Path) -> Path:
            from quack_core.core.fs.service import standalone
            if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                raise ValueError("CSV output requires a non-empty list of dictionaries")

            buffer = StringIO()
            writer = csv.DictWriter(buffer, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)

            csv_content = buffer.getvalue()
            fs = standalone
            result = fs.write_text(path, csv_content)

            if not result.success:
                raise RuntimeError(f"Failed to write CSV: {result.error}")

            return result.path

        return write_csv

    def _get_text_writer(self) -> Callable[[Any, Path], Path]:
        """Get a function that can write text output."""

        def write_text(data: Any, path: Path) -> Path:
            from quack_core.core.fs.service import standalone
            text_content = str(data)
            fs = standalone
            result = fs.write_text(path, text_content)

            if not result.success:
                raise RuntimeError(f"Failed to write text: {result.error}")

            return result.path

        return write_text

    @property
    def _format_handlers(self) -> dict[str, Callable[[Any, Path], Path]]:
        """Registry of all format handlers."""
        handlers: dict[str, Callable[[Any, Path], Path]] = {}

        for format_name, writer in self._output_writers.items():
            def make_handler(writer: OutputWriter) -> Callable[[Any, Path], Path]:
                return lambda data, path: Path(writer.write_output(data, path))

            handlers[format_name] = make_handler(writer)

        handlers["csv"] = self._get_csv_writer()
        handlers["txt"] = self._get_text_writer()

        return handlers

    def save_output(
            self,
            output: Any,
            output_path: str | Path,
            format: str | None = None
    ) -> Path:
        """Save the given output to a file."""
        output_path = Path(output_path)

        if format is None:
            format = output_path.suffix.lstrip(".")
            if not format:
                format = "json"
                output_path = output_path.with_suffix(".json")

        format = format.lower()
        handler = self._format_handlers.get(format)

        if handler is None:
            supported_formats = ", ".join(self._format_handlers.keys())
            raise ValueError(
                f"Unsupported save format: {format}. Supported formats: {supported_formats}"
            )

        return handler(output, output_path)

    def with_timestamp(
            self,
            path: str | Path,
            timestamp_format: str = "%Y%m%d%H%M%S"
    ) -> Path:
        """Add a timestamp to a path."""
        path = Path(path)
        timestamp = datetime.now(UTC).strftime(timestamp_format)
        return path.with_name(f"{path.stem}_{timestamp}{path.suffix}")

    def save_output_with_timestamp(
            self,
            output: Any,
            output_path: str | Path,
            format: str | None = None,
            timestamp_format: str = "%Y%m%d%H%M%S"
    ) -> Path:
        """Save output to a timestamped file."""
        timestamped_path = self.with_timestamp(output_path, timestamp_format)
        return self.save_output(output, timestamped_path, format)

    def register_output_writer(self, format_name: str, writer: OutputWriter) -> None:
        """Register a new output writer."""
        writers = self._output_writers
        writers_dict = dict(writers)
        writers_dict[format_name.lower()] = writer
        type(self)._writers_cache = writers_dict

    @property
    def supported_formats(self) -> list[str]:
        """Get list of supported output formats."""
        return list(self._format_handlers.keys())