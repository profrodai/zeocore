"""
Markdown to DOCX conversion _ops.

This module provides functions for converting Markdown documents to DOCX
using pandoc with optimized settings and error handling.
"""

import importlib
import os
import time
from typing import Any

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.core.logging import get_logger
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.pandoc.config import PandocConfig
from zeo_core.integrations.pandoc.models import ConversionDetails, ConversionMetrics
from zeo_core.integrations.pandoc.operations.utils import (
    check_conversion_ratio,
    check_file_size,
    prepare_pandoc_args,
    safe_convert_to_int,
    track_metrics,
)

logger = get_logger(__name__)

# Import fs module with error handling. `fs` is deliberately duck-typed here: the
# except branch swaps in a SimpleNamespace mimicking the real module's callable
# surface, not its precise per-function return types -- annotated `Any` at the
# declaration site, matching operations/utils.py's own fs-stub precedent.
fs: Any
try:
    from zeo_core.core.fs.service import standalone as fs
except ImportError:
    logger.error("Could not import zeo_core.core.fs.service")
    from types import SimpleNamespace

    # Create a safer join_path implementation
    def safe_join_path(*parts: str) -> str:
        """Safe implementation of path joining that handles type issues."""
        try:
            # Filter None values and convert to strings
            filtered_parts = [str(part) for part in parts if part is not None]
            if not filtered_parts:
                return ""

            # Handle joining manually to avoid type issues
            result = filtered_parts[0]
            for part in filtered_parts[1:]:
                result = os.path.join(result, part)
            return result
        except Exception as e:
            logger.error(f"Error joining path parts: {e}")
            return ""

    # Create a minimal fs stub if the module isn't available (for tests)
    fs = SimpleNamespace(
        get_file_info=lambda path: SimpleNamespace(
            success=False, exists=False, error="Module not available"
        ),
        create_directory=lambda path, exist_ok=True: SimpleNamespace(success=True),
        join_path=lambda *parts: SimpleNamespace(
            success=True, data=safe_join_path(*parts)
        ),
        split_path=lambda path: SimpleNamespace(
            success=True, data=path.split(os.sep) if isinstance(path, str) else []
        ),
        read_text=lambda path, encoding=None: SimpleNamespace(
            success=True, content="# Test Content"
        ),
    )


def _validate_markdown_input(markdown_path: str) -> int:
    """
    Validate the input Markdown file and return its size.

    Args:
        markdown_path: Path to the Markdown file as a string.

    Returns:
        int: Size of the input Markdown file.

    Raises:
        ZeoIntegrationError: If the input file is missing or empty.
    """
    # Standard validation for normal code paths
    file_info = fs.get_file_info(markdown_path)

    if not getattr(file_info, "success", False) or not getattr(
        file_info, "exists", False
    ):
        raise ZeoIntegrationError(
            f"Input file not found: {markdown_path}",
            {"path": markdown_path, "format": "markdown"},
        )

    # Convert file size to integer safely
    original_size = safe_convert_to_int(getattr(file_info, "size", 0), 0)

    try:
        read_result = fs.read_text(markdown_path, encoding="utf-8")
        if not getattr(read_result, "success", False):
            read_error = getattr(read_result, "error", "Unknown error")
            raise ZeoIntegrationError(
                f"Could not read Markdown file: {read_error}",
                {"path": markdown_path},
            )
        markdown_content = getattr(read_result, "content", "")
        if not markdown_content.strip():
            raise ZeoIntegrationError(
                f"Markdown file is empty: {markdown_path}",
                {"path": markdown_path},
            )
    except Exception as e:
        if isinstance(e, ZeoIntegrationError):
            raise
        raise ZeoIntegrationError(
            f"Could not read Markdown file: {str(e)}",
            {"path": markdown_path},
        ) from e

    return original_size


def _convert_markdown_to_docx_once(
    markdown_path: str, output_path: str, config: PandocConfig
) -> None:
    """
    Perform a single conversion attempt from Markdown to DOCX using pandoc.

    Args:
        markdown_path: Path to the Markdown file as a string.
        output_path: Path to save the DOCX file as a string.
        config: Conversion configuration.

    Raises:
        ZeoIntegrationError: If pandoc conversion fails.
    """
    # Standard code path for normal operation
    # Prepare pandoc arguments
    extra_args: list[str] = prepare_pandoc_args(
        config, "markdown", "docx", config.md_to_docx_extra_args
    )

    try:
        # Get the parent directory of the output file
        split_result = fs.split_path(output_path)
        if not getattr(split_result, "success", False):
            split_error = getattr(split_result, "error", "Unknown error")
            raise ZeoIntegrationError(
                f"Failed to split output path: {split_error}",
                {"path": output_path, "operation": "split_path"},
            )

        # Extract all path components except the last one (filename)
        path_components = split_result.data[:-1]

        # Join the path components to get the parent directory
        if not path_components:
            parent_dir = "."  # Default to current directory if no parent path
        else:
            join_result = fs.join_path(*path_components)
            if not getattr(join_result, "success", False):
                join_error = getattr(join_result, "error", "Unknown error")
                raise ZeoIntegrationError(
                    f"Failed to join path components: {join_error}",
                    {"components": path_components, "operation": "join_path"},
                )
            parent_dir = join_result.data

        # Create the parent directory
        # Ensure we call this even if we think it exists, for test verification
        dir_result = fs.create_directory(parent_dir, exist_ok=True)
        if not getattr(dir_result, "success", True):
            dir_error = getattr(dir_result, "error", "Unknown error")
            raise ZeoIntegrationError(
                f"Failed to create output directory: {dir_error}",
                {"path": parent_dir, "operation": "create_directory"},
            )

        logger.debug(f"Converting {markdown_path} to DOCX with args: {extra_args}")

        # Import pypandoc dynamically
        pypandoc = importlib.import_module("pypandoc")

        # Execute the conversion
        pypandoc.convert_file(
            markdown_path,
            "docx",
            format="markdown",
            outputfile=output_path,
            extra_args=extra_args,
        )

    except ImportError:
        raise ZeoIntegrationError(
            "pypandoc module is not installed",
            {"module": "pypandoc", "path": markdown_path},
        ) from None
    except Exception as e:
        if isinstance(e, ZeoIntegrationError):
            raise
        raise ZeoIntegrationError(
            f"Pandoc conversion failed: {str(e)}",
            {"path": markdown_path, "format": "markdown"},
        ) from e


def _get_conversion_output(output_path: str, start_time: float) -> tuple[float, int]:
    """
    Retrieve conversion timing and output file size.

    Args:
        output_path: Path to the output DOCX file as a string.
        start_time: Timestamp when conversion attempt started.

    Returns:
        tuple: (conversion_time, output_size)

    Raises:
        ZeoIntegrationError: If output file info cannot be retrieved.
    """
    conversion_time: float = time.time() - start_time

    # Standard code path for normal operation
    output_info = fs.get_file_info(output_path)

    if not getattr(output_info, "success", False):
        logger.warning(f"Failed to get info for converted file: {output_path}")
        output_error = getattr(output_info, "error", "Unknown error")
        raise ZeoIntegrationError(
            f"Failed to get info for converted file: {output_error}",
            {"path": output_path},
        )

    # Convert output size to integer safely
    output_size = safe_convert_to_int(getattr(output_info, "size", 0), 0)
    return conversion_time, output_size


def convert_markdown_to_docx(
    markdown_path: str,
    output_path: str,
    config: PandocConfig,
    metrics: ConversionMetrics | None = None,
) -> IntegrationResult[tuple[str, ConversionDetails]]:
    """
    Convert a Markdown file to DOCX.

    Args:
        markdown_path: Path to the Markdown file as a string.
        output_path: Path to save the DOCX file as a string.
        config: Conversion configuration.
        metrics: Optional metrics tracker.

    Returns:
        IntegrationResult[tuple[str, ConversionDetails]]: Result of the conversion.
    """
    # Get file name from the input path
    try:
        split_result = fs.split_path(markdown_path)
        if getattr(split_result, "success", False):
            filename = split_result.data[-1]
        else:
            # Fallback if split_path fails
            filename = os.path.basename(markdown_path)
    except Exception:
        # Simple fallback
        filename = markdown_path

    if metrics is None:
        metrics = ConversionMetrics()

    try:
        # Track attempt
        metrics.total_attempts += 1

        # Validate input file
        original_size: int = _validate_markdown_input(markdown_path)
        max_retries: int = config.retry_mechanism.max_conversion_retries
        retry_count: int = 0

        while retry_count < max_retries:
            start_time: float = time.time()
            try:
                _convert_markdown_to_docx_once(markdown_path, output_path, config)
                conversion_time, output_size = _get_conversion_output(
                    output_path, start_time
                )

                validation_errors: list[str] = validate_conversion(
                    output_path, markdown_path, original_size, config
                )
                if validation_errors:
                    error_str: str = "; ".join(validation_errors)
                    logger.error(f"Conversion validation failed: {error_str}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        metrics.failed_conversions += 1
                        metrics.errors[markdown_path] = error_str
                        return IntegrationResult.error_result(
                            f"Conversion failed after maximum retries: {error_str}"
                        )

                    logger.warning(
                        f"Markdown to DOCX conversion attempt {retry_count} "
                        f"failed: {error_str}"
                    )
                    time.sleep(config.retry_mechanism.conversion_retry_delay)
                    continue

                track_metrics(
                    filename, start_time, original_size, output_size, metrics, config
                )
                metrics.successful_conversions += 1

                details = ConversionDetails(
                    source_format="markdown",
                    target_format="docx",
                    conversion_time=conversion_time,
                    output_size=output_size,
                    input_size=original_size,
                )

                return IntegrationResult.success_result(
                    (output_path, details),
                    message=f"Successfully converted {markdown_path} to DOCX",
                )

            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Markdown to DOCX conversion attempt {retry_count} "
                    f"failed: {str(e)}"
                )
                if retry_count >= max_retries:
                    metrics.failed_conversions += 1
                    metrics.errors[markdown_path] = str(e)
                    error_msg = (
                        f"Integration error: {str(e)}"
                        if isinstance(e, ZeoIntegrationError)
                        else f"Failed to convert Markdown to DOCX: {str(e)}"
                    )
                    return IntegrationResult.error_result(error_msg)
                time.sleep(config.retry_mechanism.conversion_retry_delay)

        return IntegrationResult.error_result("Conversion failed after maximum retries")

    except Exception as e:
        metrics.failed_conversions += 1
        metrics.errors[markdown_path] = str(e)
        return IntegrationResult.error_result(
            f"Failed to convert Markdown to DOCX: {str(e)}"
        )


def validate_conversion(
    output_path: str, input_path: str, original_size: int, config: PandocConfig
) -> list[str]:
    """
    Validate the converted DOCX document.

    Args:
        output_path: Path to the output DOCX file as a string.
        input_path: Path to the input Markdown file as a string.
        original_size: Size of the original file.
        config: Conversion configuration.

    Returns:
        list[str]: List of validation error messages (empty if valid).
    """
    from zeo_core.integrations.pandoc.operations.utils import validate_docx_structure

    validation_errors: list[str] = []
    validation = config.validation

    output_info = fs.get_file_info(output_path)
    success = getattr(output_info, "success", False)
    exists = getattr(output_info, "exists", False)

    if not (success and exists):
        validation_errors.append(f"Output file does not exist: {output_path}")
        return validation_errors

    # Get output size safely
    output_size = safe_convert_to_int(getattr(output_info, "size", 0), 0)

    valid_size, size_errors = check_file_size(output_size, validation.min_file_size)
    if not valid_size:
        validation_errors.extend(size_errors)

    valid_ratio, ratio_errors = check_conversion_ratio(
        output_size, original_size, validation.conversion_ratio_threshold
    )
    if not valid_ratio:
        validation_errors.extend(ratio_errors)

    if validation.verify_structure and exists:
        is_valid, structure_errors = validate_docx_structure(
            output_path, validation.check_links
        )
        if not is_valid:
            validation_errors.extend(structure_errors)
        _check_docx_metadata(output_path, input_path, validation.check_links)

    return validation_errors


def _check_docx_metadata(docx_path: str, source_path: str, check_links: bool) -> None:
    """
    Check DOCX metadata for references to the source file.
    This function is separated to handle import errors cleanly.

    Args:
        docx_path: Path to the DOCX file as a string.
        source_path: Path to the source file as a string.
        check_links: Whether to check for links/references.
    """
    # Standard code path for normal operation
    split_result = fs.split_path(source_path)
    if not getattr(split_result, "success", False):
        split_error = getattr(split_result, "error", "Unknown error")
        logger.debug(f"Failed to split source path: {split_error}")
        return

    source_filename = split_result.data[-1]
    source_found = False

    try:
        # For actual document validation
        docx = importlib.import_module("docx")
        document = docx.Document
        doc = document(docx_path)

        if hasattr(doc, "core_properties"):
            core_props = doc.core_properties

            if (
                hasattr(core_props, "title")
                and core_props.title
                and source_filename in str(core_props.title)
            ):
                source_found = True
            elif (
                hasattr(core_props, "comments")
                and core_props.comments
                and source_filename in str(core_props.comments)
            ):
                source_found = True
            elif (
                hasattr(core_props, "subject")
                and core_props.subject
                and source_filename in str(core_props.subject)
            ):
                source_found = True

        if not source_found and check_links:
            logger.debug(
                f"Source file reference missing in document metadata: {source_filename}"
            )

    except Exception as e:
        logger.debug(f"Could not check document metadata: {str(e)}")


# Add an alias for the test function with the same name used in the test
validate_docx_conversion = validate_conversion
