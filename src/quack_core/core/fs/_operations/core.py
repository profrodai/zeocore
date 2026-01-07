# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/core.py
# module: quack_core.core.fs._operations.core
# role: module
# neighbors: __init__.py, base.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_operations/core.py
"""
Core path resolution and utility functionality for filesystem _operations.

This module provides internal helper functions for path resolution and
initialization tasks. These functions are used by the FileSystemOperations
class and its mixins but are not meant to be consumed directly by external code.
"""

import mimetypes
import os
from pathlib import Path

from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


def _resolve_path(base_dir: str | Path, path: str | Path) -> Path:
    """
    Resolve a path relative to the base directory.

    This function takes a path (string or Path object) and resolves it relative
    to the provided base directory. If the path is absolute, it's returned as-is.
    Otherwise, it's joined with the base directory.

    Args:
        base_dir: Base directory for resolution
        path: Path to resolve (str or Path)

    Returns:
        Path: Resolved Path object

    Note:
        This is an internal helper function not meant for external consumption.
        It's used by the _resolve_path method in FileSystemOperations.
    """
    # If path is a Path object, use it directly, otherwise convert to Path
    try:
        path_obj = Path(path)
        if not path_obj.is_absolute():
            logger.debug(f"Resolved relative path: {path} -> {path_obj}")
            return Path(base_dir) / path
        return path_obj
    except TypeError:
        # Fallback to string conversion if Path fails
        path_str = str(path)
        if os.path.isabs(path_str):
            logger.debug(f"Using absolute path: {path_str}")
            return Path(path_str)
        return Path(base_dir) / path_str


def _initialize_mime_types() -> None:
    """
    Initialize MIME types database.

    This function ensures the MIME types database is properly initialized
    for file type detection.

    Note:
        This is an internal helper function not meant for external consumption.
        It's called during FileSystemOperations initialization.
    """
    mimetypes.init()
    logger.debug("MIME types database initialized")
