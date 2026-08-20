"""
Utility functions for jupytext _ops.

This module provides helper functions for jupytext conversion _ops, such as
format detection and jupytext installation verification. All file path
values are handled as strings. Filesystem _ops are delegated to the
zeo_core.core.fs service, matching the pandoc integration's convention.
"""

import os
from typing import Any

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.core.logging import get_logger
from zeo_core.integrations.jupytext.models import NotebookInfo

logger = get_logger(__name__)

# Import fs service. `fs` is deliberately duck-typed here: the except branch below
# swaps in a SimpleNamespace whose lambda attributes mimic the real module's callable
# surface (same success/data/content shape) but not its precise per-function return
# types -- annotated `Any` at the declaration site rather than per-call-site ignores,
# matching pandoc/operations/utils.py's own fs-stub precedent.
fs: Any
try:
    from zeo_core.core.fs.service import standalone as fs
except ImportError:
    import types

    fs = types.SimpleNamespace()
    fs.get_file_info = lambda path: types.SimpleNamespace(
        success=True, exists=True, size=1024
    )
    fs.create_directory = lambda path, exist_ok=True: types.SimpleNamespace(
        success=True
    )
    fs.get_extension = lambda path: types.SimpleNamespace(
        success=True, data=path.split(".")[-1] if "." in path else ""
    )
    fs.read_text = lambda path, encoding=None: types.SimpleNamespace(
        success=True, content=""
    )
    logger.warning("Using fs service stub")

# Extensions jupytext recognizes as paired script/markdown/notebook formats.
# Kept as a local constant (rather than importing jupytext.formats.NOTEBOOK_EXTENSIONS
# at module import time) so this module still imports cleanly when jupytext itself
# is not installed -- verify_jupytext() is the single required import boundary.
_SCRIPT_EXTENSION_TO_FORMAT: dict[str, str] = {
    ".py": "py:percent",
    ".md": "md",
    ".markdown": "md",
    ".r": "R:percent",
    ".jl": "julia:percent",
}


def verify_jupytext() -> str:
    """
    Verify jupytext installation and return its version.

    Returns:
        str: jupytext version string.

    Raises:
        ZeoIntegrationError: If jupytext is not installed.
    """
    try:
        import importlib

        jupytext = importlib.import_module("jupytext")
        version = str(getattr(jupytext, "__version__", "unknown"))
        logger.info(f"Found jupytext version: {version}")
        return version
    except ImportError as err:
        msg = "jupytext module is not installed"
        logger.error(msg)
        raise ZeoIntegrationError(msg, {"module": "jupytext"}) from err
    except Exception as e:
        msg = f"Error checking jupytext: {str(e)}"
        logger.error(msg)
        raise ZeoIntegrationError(msg, {"original_error": str(e)}) from e


def guess_format_from_path(path: str, default: str = "py:percent") -> str:
    """
    Guess a jupytext format id from a file path's extension.

    Args:
        path: File path (as a string).
        default: Format id to fall back to when the extension is unrecognized
            (e.g. for a plain ``.py`` source, this is the script pairing
            format quackslides itself uses).

    Returns:
        str: A jupytext format id -- "ipynb" for notebook files, otherwise a
        script/markdown format id such as "py:percent" or "md".
    """
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext == ".ipynb":
        return "ipynb"
    return _SCRIPT_EXTENSION_TO_FORMAT.get(ext, default)


def detect_format(text: str, path: str) -> str:
    """
    Detect the jupytext format of a text blob, using jupytext's own format
    guesser with the path's extension as a hint, falling back to
    extension-based detection if jupytext cannot decide.

    Args:
        text: File content.
        path: File path (used for its extension).

    Returns:
        str: A jupytext format id.
    """
    _, ext = os.path.splitext(path)
    if ext.lower() == ".ipynb":
        return "ipynb"

    try:
        import importlib

        jupytext_formats = importlib.import_module("jupytext.formats")
        guessed, _options = jupytext_formats.guess_format(text, ext or ".py")
        if guessed:
            return f"{ext.lstrip('.') or 'py'}:{guessed}" if ext else guessed
    except Exception as e:
        logger.debug(f"jupytext format guess failed, falling back to extension: {e}")

    return guess_format_from_path(path)


def get_file_info(path: str, format_hint: str | None = None) -> NotebookInfo:
    """
    Get file information for a conversion source.

    Args:
        path: Path to the file (as a string).
        format_hint: Optional jupytext format id override.

    Returns:
        NotebookInfo: File information.

    Raises:
        ZeoIntegrationError: If the file does not exist.
    """
    file_info = fs.get_file_info(path)

    exists = getattr(file_info, "exists", False)
    if not getattr(file_info, "success", True) or not exists:
        raise ZeoIntegrationError(f"File not found: {path}")

    try:
        size = int(getattr(file_info, "size", 0) or 0)
    except (TypeError, ValueError):
        size = 0

    fmt = format_hint or guess_format_from_path(path)

    return NotebookInfo(path=path, format=fmt, size=size)
