"""
Script/markdown -> Jupyter notebook conversion _ops.

This module provides the conversion this integration exists for: parsing a
paired jupytext-format source (percent-format .py, markdown, etc.) into an
``.ipynb`` file. This is the exact operation the org's own quackslides app
hand-rolls today (``quackslides/notebook/converter.py``: ``jupytext.reads(text,
fmt="py:percent")`` then ``jupytext.writes(notebook, fmt="ipynb")``), lifted
into zeocore with the same two calls at its core plus zeocore's error-handling
and result-envelope conventions (matching the pandoc integration's operations
modules).
"""

import importlib
import time
from typing import Any

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.core.logging import get_logger
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.jupytext.config import JupytextConfig
from zeo_core.integrations.jupytext.models import ConversionDetails
from zeo_core.integrations.jupytext.operations.utils import detect_format

logger = get_logger(__name__)

# Import fs module with error handling, matching pandoc/operations/*.py's own
# fs-stub precedent -- `Any`-typed so it works against either the real
# zeo_core.core.fs.service.standalone module or the SimpleNamespace fallback.
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


def _read_source(input_path: str) -> tuple[str, int]:
    """
    Read the source file's text content and size.

    Args:
        input_path: Path to the source script/markdown file.

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
    except TypeError, ValueError:
        size = 0

    read_result = fs.read_text(input_path, encoding="utf-8")
    if not getattr(read_result, "success", False):
        read_error = getattr(read_result, "error", "Unknown error")
        raise ZeoIntegrationError(f"Could not read source file: {read_error}")

    content = getattr(read_result, "content", "")
    if not isinstance(content, str):
        raise ZeoIntegrationError(f"Source file did not decode to text: {input_path}")
    return content, size


def _parse_notebook(text: str, source_format: str) -> Any:  # noqa: ANN401 -- returns nbformat.NotebookNode, a third-party type this module deliberately does not hard-depend on at the type-annotation level (jupytext is lazily imported, matching pandoc's pypandoc precedent)
    """
    Parse source text into an nbformat notebook via jupytext.

    Args:
        text: Source file content.
        source_format: jupytext format id (e.g. "py:percent", "md").

    Returns:
        nbformat.NotebookNode: The parsed notebook.

    Raises:
        ZeoIntegrationError: If jupytext is not installed or parsing fails.
    """
    try:
        jupytext = importlib.import_module("jupytext")
    except ImportError as e:
        raise ZeoIntegrationError(f"jupytext module is not installed: {str(e)}") from e

    try:
        return jupytext.reads(text, fmt=source_format)
    except Exception as e:
        raise ZeoIntegrationError(
            f"jupytext failed to parse source as '{source_format}': {str(e)}"
        ) from e


def _apply_default_metadata(notebook: Any, config: JupytextConfig) -> None:  # noqa: ANN401 -- nbformat.NotebookNode, see _parse_notebook
    """
    Ensure the parsed notebook carries a kernelspec/language_info, matching
    quackslides' own ``_py_to_notebook`` convention of filling in sane
    defaults when the source format carries none.

    Args:
        notebook: The parsed nbformat notebook (mutated in place).
        config: Conversion configuration.
    """
    notebook.setdefault("metadata", {})
    notebook["metadata"].setdefault(
        "kernelspec", dict(config.metadata.default_kernelspec)
    )


def _write_notebook_file(notebook: Any, output_path: str) -> int:  # noqa: ANN401 -- nbformat.NotebookNode, see _parse_notebook
    """
    Serialize a notebook to ``.ipynb`` JSON and write it to disk.

    Args:
        notebook: The notebook to serialize.
        output_path: Destination path for the ``.ipynb`` file.

    Returns:
        int: Number of bytes written.

    Raises:
        ZeoIntegrationError: If serialization or writing fails.
    """
    try:
        jupytext = importlib.import_module("jupytext")
        ipynb_text = jupytext.writes(notebook, fmt="ipynb")
    except Exception as e:
        raise ZeoIntegrationError(
            f"jupytext failed to serialize notebook: {str(e)}"
        ) from e

    import os as _os

    output_dir = _os.path.dirname(output_path)
    if output_dir:
        dir_result = fs.create_directory(output_dir, exist_ok=True)
        if not getattr(dir_result, "success", False):
            dir_error = getattr(dir_result, "error", "Unknown error")
            raise ZeoIntegrationError(f"Failed to create output directory: {dir_error}")

    write_result = fs.write_text(output_path, ipynb_text, encoding="utf-8")
    if not getattr(write_result, "success", False):
        write_error = getattr(write_result, "error", "Unknown error")
        raise ZeoIntegrationError(f"Failed to write output file: {write_error}")

    bytes_written = getattr(write_result, "bytes_written", None)
    if bytes_written is not None:
        try:
            return int(bytes_written)
        except TypeError, ValueError:
            pass
    return len(ipynb_text.encode("utf-8"))


def convert_to_notebook(
    input_path: str,
    output_path: str,
    config: JupytextConfig,
    source_format: str | None = None,
) -> IntegrationResult[tuple[str, ConversionDetails]]:
    """
    Convert a paired script/markdown source file to a Jupyter notebook.

    This is the operation quackslides needs: percent-format ``.py`` (or any
    other jupytext-supported paired format) in, ``.ipynb`` out. Never mutates
    the source file.

    Args:
        input_path: Path to the source file, as a string.
        output_path: Path to write the ``.ipynb`` file, as a string.
        config: Conversion configuration.
        source_format: Optional jupytext format id override. Detected from
            the source content/extension when omitted.

    Returns:
        IntegrationResult containing a tuple of (output_path, ConversionDetails).
    """
    start = time.time()
    try:
        text, input_size = _read_source(input_path)
        fmt = source_format or detect_format(text, input_path)

        notebook = _parse_notebook(text, fmt)
        if config.metadata.inject_provenance:
            _apply_default_metadata(notebook, config)

        cell_count = len(getattr(notebook, "cells", []) or [])
        if config.validation.verify_structure and cell_count == 0:
            return IntegrationResult.error_result(
                f"Parsed notebook has no cells: {input_path}"
            )

        output_size = _write_notebook_file(notebook, output_path)

        if output_size < config.validation.min_file_size:
            return IntegrationResult.error_result(
                f"Converted file size ({output_size}B) is below the minimum "
                f"threshold ({config.validation.min_file_size}B): {output_path}"
            )

        details = ConversionDetails(
            source_format=fmt,
            target_format="ipynb",
            conversion_time=time.time() - start,
            output_size=output_size,
            input_size=input_size,
            cell_count=cell_count,
        )
        return IntegrationResult.success_result(
            (output_path, details),
            message=f"Successfully converted {input_path} to notebook",
        )
    except Exception as e:
        error_msg = (
            f"Integration error: {str(e)}"
            if isinstance(e, ZeoIntegrationError)
            else f"Failed to convert to notebook: {str(e)}"
        )
        logger.warning(f"Notebook conversion failed: {str(e)}")
        return IntegrationResult.error_result(error_msg)
