"""
Jupyter notebook -> script/markdown conversion _ops.

The inverse of ``to_notebook.py``: reads an ``.ipynb`` file and writes it out
in a paired jupytext script/markdown format (e.g. percent-format ``.py``).
Not exercised by quackslides today (it only ever goes script -> notebook),
but jupytext is inherently a paired-format, round-trip tool and a real SDK
integration should expose both directions rather than hard-coding a single
consumer's current one-way usage.
"""

import importlib
import time
from typing import Any

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.core.logging import get_logger
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.jupytext.config import JupytextConfig
from zeo_core.integrations.jupytext.models import ConversionDetails

logger = get_logger(__name__)

fs: Any
try:
    from zeo_core.core.fs.service import standalone as fs
except ImportError:
    logger.error("Could not import zeo_core.core.fs.service")
    from types import SimpleNamespace

    fs = SimpleNamespace(
        get_file_info=lambda path: SimpleNamespace(
            success=False, exists=False, error="Module not available"
        ),
        create_directory=lambda path, exist_ok=True: SimpleNamespace(success=True),
        write_text=lambda path, content, encoding=None: SimpleNamespace(
            success=True, bytes_written=len(content) if isinstance(content, str) else 0
        ),
        read_text=lambda path, encoding=None: SimpleNamespace(success=True, content=""),
    )


def _read_notebook_source(input_path: str) -> tuple[str, int]:
    """
    Read the source ``.ipynb`` file's text content and size.

    Args:
        input_path: Path to the source notebook file.

    Returns:
        tuple: (text content, size in bytes).

    Raises:
        ZeoIntegrationError: If the file cannot be found or read.
    """
    file_info = fs.get_file_info(input_path)
    if not getattr(file_info, "success", False) or not getattr(
        file_info, "exists", False
    ):
        raise ZeoIntegrationError(f"Input file not found: {input_path}")

    try:
        size = int(getattr(file_info, "size", 0) or 0)
    except (TypeError, ValueError):
        size = 0

    read_result = fs.read_text(input_path, encoding="utf-8")
    if not getattr(read_result, "success", False):
        read_error = getattr(read_result, "error", "Unknown error")
        raise ZeoIntegrationError(f"Could not read notebook file: {read_error}")

    content = getattr(read_result, "content", "")
    if not isinstance(content, str):
        raise ZeoIntegrationError(f"Notebook file did not decode to text: {input_path}")
    return content, size


def _write_script_file(text: str, output_path: str) -> int:
    """
    Write serialized script/markdown text to disk.

    Args:
        text: Serialized script/markdown content.
        output_path: Destination path.

    Returns:
        int: Number of bytes written.

    Raises:
        ZeoIntegrationError: If writing fails.
    """
    import os as _os

    output_dir = _os.path.dirname(output_path)
    if output_dir:
        dir_result = fs.create_directory(output_dir, exist_ok=True)
        if not getattr(dir_result, "success", False):
            dir_error = getattr(dir_result, "error", "Unknown error")
            raise ZeoIntegrationError(f"Failed to create output directory: {dir_error}")

    write_result = fs.write_text(output_path, text, encoding="utf-8")
    if not getattr(write_result, "success", False):
        write_error = getattr(write_result, "error", "Unknown error")
        raise ZeoIntegrationError(f"Failed to write output file: {write_error}")

    bytes_written = getattr(write_result, "bytes_written", None)
    if bytes_written is not None:
        try:
            return int(bytes_written)
        except (TypeError, ValueError):
            pass
    return len(text.encode("utf-8"))


def convert_to_script(
    input_path: str,
    output_path: str,
    config: JupytextConfig,
    target_format: str | None = None,
) -> IntegrationResult[tuple[str, ConversionDetails]]:
    """
    Convert a Jupyter notebook (``.ipynb``) to a paired script/markdown file.

    Args:
        input_path: Path to the source ``.ipynb`` file, as a string.
        output_path: Path to write the script/markdown file, as a string.
        config: Conversion configuration.
        target_format: Optional jupytext format id override (e.g.
            "py:percent", "md"). Defaults to config.default_script_format.

    Returns:
        IntegrationResult containing a tuple of (output_path, ConversionDetails).
    """
    start = time.time()
    fmt = target_format or config.default_script_format
    try:
        text, input_size = _read_notebook_source(input_path)

        try:
            jupytext = importlib.import_module("jupytext")
        except ImportError as e:
            raise ZeoIntegrationError(
                f"jupytext module is not installed: {str(e)}"
            ) from e

        try:
            notebook = jupytext.reads(text, fmt="ipynb")
        except Exception as e:
            raise ZeoIntegrationError(
                f"jupytext failed to parse source notebook: {str(e)}"
            ) from e

        cell_count = len(getattr(notebook, "cells", []) or [])
        if config.validation.verify_structure and cell_count == 0:
            return IntegrationResult.error_result(
                f"Parsed notebook has no cells: {input_path}"
            )

        try:
            script_text = jupytext.writes(notebook, fmt=fmt)
        except Exception as e:
            raise ZeoIntegrationError(
                f"jupytext failed to serialize as '{fmt}': {str(e)}"
            ) from e

        output_size = _write_script_file(script_text, output_path)

        if output_size < config.validation.min_file_size:
            return IntegrationResult.error_result(
                f"Converted file size ({output_size}B) is below the minimum "
                f"threshold ({config.validation.min_file_size}B): {output_path}"
            )

        details = ConversionDetails(
            source_format="ipynb",
            target_format=fmt,
            conversion_time=time.time() - start,
            output_size=output_size,
            input_size=input_size,
            cell_count=cell_count,
        )
        return IntegrationResult.success_result(
            (output_path, details),
            message=f"Successfully converted {input_path} to '{fmt}'",
        )
    except Exception as e:
        error_msg = (
            f"Integration error: {str(e)}"
            if isinstance(e, ZeoIntegrationError)
            else f"Failed to convert notebook to script: {str(e)}"
        )
        logger.warning(f"Script conversion failed: {str(e)}")
        return IntegrationResult.error_result(error_msg)
