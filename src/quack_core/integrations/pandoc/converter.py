"""
Core converter implementation for Pandoc integration.

This module provides the main DocumentConverter class that implements
the document conversion functionality using Pandoc. In this refactored
version, all file paths are represented as strings. Filesystem _ops
such as reading file info, creating directories, writing output files, etc.,
are delegated to the quack_core.core.fs service functions.
"""

import os
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from quack_core.core.errors import QuackIntegrationError
from quack_core.core.logging import get_logger
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc import PandocConfig
from quack_core.integrations.pandoc.models import ConversionMetrics, ConversionTask
from quack_core.integrations.pandoc.operations import (
    get_file_info,
    verify_pandoc,
)
from quack_core.integrations.pandoc.operations.utils import (
    safe_convert_to_int,
    validate_docx_structure,
)
from quack_core.integrations.pandoc.protocols import (
    BatchConverterProtocol,
    DocumentConverterProtocol,
)

logger = get_logger(__name__)

# Import fs module with error handling. `fs` is deliberately duck-typed here: the
# except branch swaps in a SimpleNamespace mimicking the real module's callable
# surface, not its precise per-function return types -- annotated `Any` at the
# declaration site, matching operations/utils.py's own fs-stub precedent.
fs: Any
try:
    from quack_core.core.fs.service import standalone as fs
except ImportError:
    logger.error("Could not import quack_core.core.fs.service")
    from types import SimpleNamespace

    # Create a minimal fs stub if the module isn't available (for tests)
    fs = SimpleNamespace(
        get_file_info=lambda path: SimpleNamespace(success=True, exists=True, size=100),
        create_directory=lambda path, exist_ok=True: SimpleNamespace(success=True),
        join_path=lambda *parts: SimpleNamespace(
            success=True, data=os.path.join(*parts)
        ),
        split_path=lambda path: SimpleNamespace(
            success=True, data=path.split(os.sep) if isinstance(path, str) else []
        ),
        get_extension=lambda path: SimpleNamespace(
            success=True,
            data=path.split(".")[-1] if isinstance(path, str) and "." in path else "",
        ),
        read_text=lambda path, encoding=None: SimpleNamespace(success=True, content=""),
    )


class DocumentConverter(DocumentConverterProtocol, BatchConverterProtocol):
    """
    Handles document conversion using Pandoc with retry and validation.

    All file paths throughout this class are handled as strings.
    """

    def __init__(self, config: PandocConfig) -> None:
        """
        Initialize the document converter.

        Args:
            config: The Pandoc conversion configuration.

        Raises:
            QuackIntegrationError: If Pandoc is not available.
        """
        self.config: PandocConfig = config
        self.metrics: ConversionMetrics = ConversionMetrics(start_time=datetime.now())
        try:
            self._pandoc_version: str = verify_pandoc()
        except Exception as e:
            logger.warning(f"Failed to verify pandoc version: {e}")
            self._pandoc_version = "unknown"

    @property
    def pandoc_version(self) -> str:
        """Get the Pandoc version."""
        return self._pandoc_version

    def _create_output_directory_for_file(
        self, output_path: str
    ) -> IntegrationResult[str] | None:
        """
        Create the parent directory for a single output file.

        Args:
            output_path: Output file path whose parent directory is created.

        Returns:
            IntegrationResult error on failure, None on success.
        """
        try:
            output_dir = os.path.dirname(output_path)
            if not output_dir:
                output_dir = "."  # Default to current directory

            dir_result = fs.create_directory(output_dir, exist_ok=True)
            if not getattr(dir_result, "success", False):
                dir_error = getattr(dir_result, "error", "Unknown error")
                return IntegrationResult.error_result(
                    f"Failed to create output directory: {dir_error}"
                )
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")
            return IntegrationResult.error_result(
                f"Failed to create output directory: {str(e)}"
            )
        return None

    def _run_format_conversion(
        self,
        input_path: str,
        output_path: str,
        input_format: str,
        output_format: str,
    ) -> IntegrationResult[str]:
        """
        Dispatch to the appropriate Pandoc operation for a format pair.

        Args:
            input_path: Input file path.
            output_path: Output file path.
            input_format: Detected format of the input file.
            output_format: Target format requested by the caller.

        Returns:
            IntegrationResult containing the output file path on success.
        """
        if input_format == "html" and output_format == "markdown":
            from quack_core.integrations.pandoc.operations import (
                convert_html_to_markdown,
            )

            result = convert_html_to_markdown(
                input_path, output_path, self.config, self.metrics
            )
            return self._wrap_conversion_result(result, input_path, "Markdown")

        elif input_format == "markdown" and output_format == "docx":
            from quack_core.integrations.pandoc.operations import (
                convert_markdown_to_docx,
            )

            result = convert_markdown_to_docx(
                input_path, output_path, self.config, self.metrics
            )
            return self._wrap_conversion_result(result, input_path, "DOCX")

        else:
            return IntegrationResult.error_result(
                f"Unsupported conversion: {input_format} to {output_format}"
            )

    def _wrap_conversion_result(
        self, result: IntegrationResult, input_path: str, format_label: str
    ) -> IntegrationResult[str]:
        """
        Unpack a Pandoc operation result into the public convert_file result.

        Args:
            result: Result returned by the underlying conversion operation.
            input_path: Input file path, used only for the success message.
            format_label: Human readable target format for the success
                message, e.g. "Markdown" or "DOCX".

        Returns:
            IntegrationResult containing the output file path on success.
        """
        if result.success and result.content:
            # Unpack the returned tuple to get the output path string
            output_path_str = (
                result.content[0]
                if isinstance(result.content, tuple)
                else result.content
            )
            return IntegrationResult.success_result(
                output_path_str,
                message=f"Successfully converted {input_path} to {format_label}",
            )
        return IntegrationResult.error_result(result.error or "Conversion failed")

    def convert_file(
        self, input_path: str, output_path: str, output_format: str
    ) -> IntegrationResult[str]:
        """
        Convert a file from one format to another.

        Args:
            input_path: Input file path (as a string).
            output_path: Output file path (as a string).
            output_format: Target format (e.g. "markdown" or "docx").

        Returns:
            IntegrationResult containing the output file path (string).
        """
        try:
            # Get file info
            try:
                input_info = get_file_info(input_path)
            except QuackIntegrationError as e:
                logger.error(f"Integration error during conversion: {str(e)}")
                return IntegrationResult.error_result(str(e))

            # Create output directory
            dir_error = self._create_output_directory_for_file(output_path)
            if dir_error is not None:
                return dir_error

            # Perform conversion based on file format
            return self._run_format_conversion(
                input_path, output_path, input_info.format, output_format
            )

        except QuackIntegrationError as e:
            logger.error(f"Integration error during conversion: {str(e)}")
            return IntegrationResult.error_result(str(e))
        except Exception as e:
            logger.error(f"Unexpected error during conversion: {str(e)}")
            return IntegrationResult.error_result(f"Conversion error: {str(e)}")

    def _resolve_batch_output_path(
        self, task: ConversionTask, batch_output_dir: str
    ) -> str | None:
        """
        Determine the output path for a batch conversion task.

        Args:
            task: The conversion task, may already specify an output path.
            batch_output_dir: Directory to place derived output files in.

        Returns:
            The resolved output path, or None if it could not be
            determined, in which case the failure has already been logged.
        """
        if task.output_path is not None:
            return task.output_path

        # Extract filename from source path
        try:
            split_result = fs.split_path(task.source.path)
            if not getattr(split_result, "success", False):
                split_error = getattr(split_result, "error", "Unknown error")
                logger.error(f"Failed to split path: {split_error}")
                return None

            # Get the filename and extension
            filename = split_result.data[-1]
            name, _ = os.path.splitext(filename)

            # Determine the new extension based on target format
            ext = (
                ".md" if task.target_format == "markdown" else f".{task.target_format}"
            )
            return os.path.join(batch_output_dir, name + ext)
        except Exception as e:
            logger.error(f"Failed to determine output path: {e}")
            return None

    def _process_batch_task(
        self,
        task: ConversionTask,
        batch_output_dir: str,
        successful_files: list[str],
        failed_files: list[str],
    ) -> None:
        """
        Convert a single batch task, recording the outcome.

        Args:
            task: The conversion task to process.
            batch_output_dir: Directory to place derived output files in.
            successful_files: List to append the output path to on success.
            failed_files: List to append the source path to on failure.
        """
        try:
            output_path = self._resolve_batch_output_path(task, batch_output_dir)
            if output_path is None:
                failed_files.append(task.source.path)
                return

            # Perform the conversion
            result = self.convert_file(
                task.source.path, output_path, task.target_format
            )

            if result.success and result.content:
                successful_files.append(result.content)
                self.metrics.successful_conversions += 1
            else:
                failed_files.append(task.source.path)
                logger.error(
                    f"Failed to convert {task.source.path} to "
                    f"{task.target_format}: {result.error}"
                )
                self.metrics.failed_conversions += 1
                self.metrics.errors[task.source.path] = result.error or "Unknown error"
        except Exception as e:
            failed_files.append(task.source.path)
            logger.error(f"Error processing task for {task.source.path}: {str(e)}")
            self.metrics.errors[task.source.path] = str(e)
            self.metrics.failed_conversions += 1

    def convert_batch(
        self, tasks: Sequence[ConversionTask], output_dir: str | None = None
    ) -> IntegrationResult[list[str]]:
        """
        Convert a batch of files.

        Args:
            tasks: Sequence of conversion tasks.
            output_dir: Directory to save converted files (as a string).
                        If not provided, the value from the configuration is used.

        Returns:
            IntegrationResult containing a list of successfully converted file
            paths (as strings).
        """
        # Use the provided output_dir, or fallback to the config value
        batch_output_dir: str = (
            output_dir if output_dir is not None else self.config.output_dir
        )

        # Create the output directory
        try:
            dir_result = fs.create_directory(batch_output_dir, exist_ok=True)
            if not getattr(dir_result, "success", False):
                dir_error = getattr(dir_result, "error", "Unknown error")
                return IntegrationResult.error_result(
                    f"Failed to create output directory: {dir_error}"
                )
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")
            return IntegrationResult.error_result(
                f"Failed to create output directory: {str(e)}"
            )

        # Initialize tracking variables
        successful_files: list[str] = []
        failed_files: list[str] = []
        self.metrics.total_attempts += len(tasks)

        # Process each task
        for task in tasks:
            self._process_batch_task(
                task, batch_output_dir, successful_files, failed_files
            )

        # Return appropriate result based on success/failure
        if not failed_files:
            return IntegrationResult.success_result(
                successful_files,
                message=f"Successfully converted {len(successful_files)} files",
            )
        elif successful_files:
            return IntegrationResult.success_result(
                successful_files,
                message=(
                    f"Partially successful: converted {len(successful_files)} "
                    f"files, failed to convert {len(failed_files)} files"
                ),
            )
        else:
            failed_files_str: str = ", ".join(failed_files[:5])
            if len(failed_files) > 5:
                failed_files_str += f" and {len(failed_files) - 5} more"
            error_msg: str = (
                f"Failed to convert any files. Failed files: {failed_files_str}"
            )
            return IntegrationResult.error_result(
                error=error_msg,
                message=(
                    f"All {len(failed_files)} conversion tasks failed. "
                    "See logs for details."
                ),
            )

    def validate_conversion(self, output_path: str, input_path: str) -> bool:
        """
        Validate the converted document.

        Args:
            output_path: Output file path (as a string).
            input_path: Input file path (as a string).

        Returns:
            True if validation passes, otherwise False.
        """
        try:
            # Get file info for input and output files
            output_info = fs.get_file_info(output_path)
            input_info = fs.get_file_info(input_path)

            # Check if files exist
            if not getattr(output_info, "success", False) or not getattr(
                output_info, "exists", False
            ):
                logger.error(f"Output file does not exist: {output_path}")
                return False

            if not getattr(input_info, "success", False) or not getattr(
                input_info, "exists", False
            ):
                logger.error(f"Input file does not exist: {input_path}")
                return False

            # Get file sizes
            input_size = safe_convert_to_int(getattr(input_info, "size", 0), 0)
            output_size = safe_convert_to_int(getattr(output_info, "size", 0), 0)

            # Calculate size change
            size_change_percentage = (
                (output_size / input_size * 100) if input_size > 0 else 0
            )
            logger.debug(
                f"Conversion size change: {input_size} → {output_size} bytes "
                f"({size_change_percentage:.1f}%)"
            )

            # Get file extension
            try:
                ext_result = fs.get_extension(output_path)
                ext = (
                    getattr(ext_result, "data", "")
                    if getattr(ext_result, "success", False)
                    else ""
                )
            except Exception as e:
                logger.error(f"Failed to get extension: {e}")
                ext = output_path.split(".")[-1] if "." in output_path else ""

            # Validate based on file type
            if ext in ("md", "markdown"):
                try:
                    read_result = fs.read_text(output_path, encoding="utf-8")
                    if not getattr(read_result, "success", False):
                        read_error = getattr(read_result, "error", "Unknown error")
                        logger.error(f"Failed to read markdown file: {read_error}")
                        return False
                    return len(getattr(read_result, "content", "").strip()) > 0
                except Exception as e:
                    logger.error(f"Failed to read markdown file: {e}")
                    return False
            elif ext == "docx":
                try:
                    is_valid, _ = validate_docx_structure(
                        output_path, self.config.validation.check_links
                    )
                    return is_valid
                except Exception as e:
                    logger.error(f"Failed to validate DOCX structure: {e}")
                    return False
            else:
                # For unknown extensions, just check file size
                return output_size > self.config.validation.min_file_size

        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return False
