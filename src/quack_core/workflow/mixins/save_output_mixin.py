# quack-core/src/quack_core/workflow/mixins/save_output_mixin.py
"""
Mixin providing output saving capabilities.

This mixin leverages QuackCore's output writers and filesystem
services to save workflow outputs in various formats.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any, ClassVar

from quack_core.workflow.output import (
    DefaultOutputWriter,
    OutputWriter,
    YAMLOutputWriter,
)


class SaveOutputMixin:
    """
    Mixin providing methods to save output in different formats.

    This mixin leverages QuackCore's filesystem services and output
    writers to provide a consistent interface for saving data in
    different formats.
    """

    _writers_cache: ClassVar[dict[str, OutputWriter]] = {}

    @property
    def _output_writers(self) -> dict[str, OutputWriter]:
        """
        Registry of available output writers.

        Returns:
            Mapping of format names to OutputWriter instances.
        """
        # Check if we already have a cached version
        if not hasattr(type(self), '_writers_cache'):
            type(self)._writers_cache = {
                "json": DefaultOutputWriter(indent=2),
                "yaml": YAMLOutputWriter(),
            }

        return type(self)._writers_cache

    def _get_csv_writer(self) -> Callable[[Any, Path], Path]:
        """
        Get a function that can write CSV output.

        This is separated to keep the registry clean and handle
        the special case of CSV which doesn't use an OutputWriter.

        Returns:
            Function that writes data to a CSV file.
        """

        def write_csv(data: Any, path: Path) -> Path:
            from quack_core.fs.service import standalone
            if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                raise ValueError("CSV output requires a non-empty list of dictionaries")

            # Write to string buffer first to handle any serialization errors
            buffer = StringIO()
            writer = csv.DictWriter(buffer, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)

            # Write the buffer contents to the file
            csv_content = buffer.getvalue()
            fs = standalone
            result = fs.write_text(path, csv_content)

            if not result.success:
                raise RuntimeError(f"Failed to write CSV: {result.error}")

            return result.path

        return write_csv

    def _get_text_writer(self) -> Callable[[Any, Path], Path]:
        """
        Get a function that can write text output.

        This is separated to keep the registry clean and handle
        the special case of plain text which doesn't use an OutputWriter.

        Returns:
            Function that writes data to a text file.
        """

        def write_text(data: Any, path: Path) -> Path:
            from quack_core.fs.service import standalone
            # Convert output to string
            text_content = str(data)
            fs = standalone
            result = fs.write_text(path, text_content)

            if not result.success:
                raise RuntimeError(f"Failed to write text: {result.error}")

            return result.path

        return write_text

    @property
    def _format_handlers(self) -> dict[str, Callable[[Any, Path], Path]]:
        """
        Registry of all format handlers, including both OutputWriters and custom handlers.

        Returns:
            Mapping of format names to handler functions.
        """
        # First get all OutputWriter-based handlers
        handlers: dict[str, Callable[[Any, Path], Path]] = {}

        # Add writer-based handlers
        for format_name, writer in self._output_writers.items():
            # Create a closure over the writer instance
            def make_handler(writer: OutputWriter) -> Callable[[Any, Path], Path]:
                return lambda data, path: Path(writer.write_output(data, path))

            handlers[format_name] = make_handler(writer)

        # Add special handlers
        handlers["csv"] = self._get_csv_writer()
        handlers["txt"] = self._get_text_writer()

        return handlers

    def save_output(
            self,
            output: Any,
            output_path: str | Path,
            format: str | None = None
    ) -> Path:
        """
        Save the given output to a file using the appropriate format.

        Args:
            output: The data to save
            output_path: Path where to save the output
            format: Output format (json, yaml, csv, txt)
                   If None, inferred from output_path suffix

        Returns:
            Path to the saved file

        Raises:
            ValueError: If an unsupported format is specified
            RuntimeError: If the save operation fails
        """
        # Normalize path to Path object
        output_path = Path(output_path)

        # If format is not specified, try to infer from file extension
        if format is None:
            format = output_path.suffix.lstrip(".")
            if not format:
                # Default to json if no extension is provided
                format = "json"
                output_path = output_path.with_suffix(".json")

        # Get the handler for the specified format
        format = format.lower()
        handler = self._format_handlers.get(format)

        if handler is None:
            supported_formats = ", ".join(self._format_handlers.keys())
            raise ValueError(
                f"Unsupported save format: {format}. Supported formats: {supported_formats}"
            )

        # Use the handler to save the output
        return handler(output, output_path)

    def with_timestamp(
            self,
            path: str | Path,
            timestamp_format: str = "%Y%m%d%H%M%S"
    ) -> Path:
        """
        Add a timestamp to a path.

        Args:
            path: Original path
            timestamp_format: strftime format string (default: %Y%m%d%H%M%S)

        Returns:
            Path with timestamp added before the extension
        """
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
        """
        Save output to a timestamped file.

        This is a convenience method that combines save_output and with_timestamp.

        Args:
            output: The data to save
            output_path: Path where to save the output
            format: Output format (json, yaml, csv, txt)
                   If None, inferred from output_path suffix
            timestamp_format: strftime format string (default: %Y%m%d%H%M%S)

        Returns:
            Path to the saved file with timestamp
        """
        timestamped_path = self.with_timestamp(output_path, timestamp_format)
        return self.save_output(output, timestamped_path, format)

    def register_output_writer(self, format_name: str, writer: OutputWriter) -> None:
        """
        Register a new output writer.

        This method allows extending the mixin with additional output formats
        at runtime. It's particularly useful for plugins or extensions.

        Args:
            format_name: The name of the format (e.g., "json", "yaml")
            writer: An instance of OutputWriter for the format

        Note:
            This will override any existing writer for the same format.
        """
        # Since properties are read-only, we need to update the class's dictionary
        writers = self._output_writers
        writers_dict = dict(writers)
        writers_dict[format_name.lower()] = writer

        # Update the class attribute
        type(self)._writers_cache = writers_dict

    @property
    def supported_formats(self) -> list[str]:
        """
        Get a list of supported output formats.

        Returns:
            List of format names supported by this mixin
        """
        return list(self._format_handlers.keys())
