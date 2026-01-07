# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_helpers/temp.py
# module: quack_core.core.fs._helpers.temp
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_helpers/temp.py
"""
Utility functions for temporary files and directories.
"""

import os
import tempfile
from pathlib import Path
from typing import Any

from quack_core.errors import QuackIOError, wrap_io_errors

# Import from within package
from quack_core.fs._helpers.file_ops import _ensure_directory
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


@wrap_io_errors
def _create_temp_directory(prefix: str = "quackcore_", suffix: str = "") -> Path:
    """
    Create a temporary directory.

    Args:
        prefix: Directory name prefix
        suffix: Directory name suffix

    Returns:
        Path to the created temporary directory

    Raises:
        QuackIOError: For IO related issues
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix)
        logger.debug(f"Created temporary directory: {temp_dir}")
        return Path(temp_dir)
    except Exception as e:
        logger.error(f"Failed to create temporary directory: {e}")
        raise QuackIOError(f"Failed to create temporary directory: {e}") from e


@wrap_io_errors
def _create_temp_file(
        suffix: str = ".txt",
        prefix: str = "quackcore_",
        directory: Any = None,
) -> Path:
    """
    Create a temporary file.

    Args:
        suffix: File suffix (e.g., ".txt")
        prefix: File prefix
        directory: Directory to create the file in (can be str, Path, or any object with 'data' attribute, or None for system temp dir)

    Returns:
        Path to the created temporary file

    Raises:
        QuackIOError: For IO related issues
    """
    # Normalize directory to Path if provided
    dir_path = _normalize_path_param(directory) if directory is not None else None

    if dir_path:
        _ensure_directory(dir_path)

    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir_path)
        os.close(fd)  # Close the file descriptor
        logger.debug(f"Created temporary file: {path}")
        return Path(path)
    except Exception as e:
        logger.error(f"Failed to create temporary file: {e}")
        raise QuackIOError(f"Failed to create temporary file: {e}") from e
