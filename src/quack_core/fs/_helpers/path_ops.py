# quack-core/src/quack-core/fs/_helpers/path_ops.py
"""
Utility functions for path _operations.
"""

import os
from pathlib import Path
from typing import Any

# Import our dedicated helper
from quackcore.fs._helpers.path_utils import _normalize_path_param
from quackcore.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


def _split_path(path: Any) -> list[str]:
    """
    Split a path into its components.

    Args:
        path: Path to split (can be str, Path, or any object with 'data' attribute)

    Returns:
        List of path components
    """
    # Normalize to Path object using our dedicated helper
    path_obj = _normalize_path_param(path)

    parts = list(path_obj.parts)
    # Preserve relative path notation with ./
    if str(path).startswith("./"):
        parts.insert(0, ".")
    logger.debug(f"Split path {path_obj} into {parts}")
    return parts


def _join_path(*parts: Any) -> Path:
    """
    Join path components.

    Args:
        *parts: Path parts to join (can be str, Path, or any object with 'data' attribute)

    Returns:
        Joined Path object
    """
    # Normalize all parts to strings before joining
    normalized_parts = [str(_normalize_path_param(part)) for part in parts]
    result = Path(*normalized_parts)
    logger.debug(f"Joined path parts {parts} to {result}")
    return result


def _expand_user_vars(path: Any) -> Path:
    """
    Expand user variables and environment variables in a path.

    Args:
        path: Path with variables (can be str, Path, or any object with 'data' attribute)

    Returns:
        Expanded Path object
    """
    # Normalize to Path and then to string for expanduser
    path_obj = _normalize_path_param(path)
    path_str = str(path_obj)

    # Expand user and environment variables
    path_str = os.path.expanduser(path_str)
    path_str = os.path.expandvars(path_str)

    # Convert back to Path object
    result = Path(path_str)

    if str(result) != str(path_obj):
        logger.debug(f"Expanded path variables: {path_obj} -> {result}")

    return result
