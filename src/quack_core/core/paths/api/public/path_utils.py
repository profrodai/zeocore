# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/api/public/path_utils.py
# module: quack_core.core.paths.api.public.path_utils
# role: api
# neighbors: __init__.py, results.py
# exports: ensure_clean_path, is_likely_drive_id, extract_path_from_path_result_string
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Path utilities for quack_core.

This module provides utilities for handling paths, especially for
converting various path-like objects to clean path strings.
"""

import re
from typing import Any


def ensure_clean_path(path_or_result: Any) -> str:
    """
    Extract a clean path string from various input types.

    Args:
        path_or_result: Can be a string, Path, PathResult, or any other Result object

    Returns:
        A clean path string
    """
    if hasattr(path_or_result, "path") and path_or_result.path is not None:
        # Handle PathResult and similar objects
        return str(path_or_result.path)
    elif hasattr(path_or_result, "data") and path_or_result.data is not None:
        # Handle DataResult objects
        return str(path_or_result.data)
    else:
        # For strings and Path objects
        return str(path_or_result)


def is_likely_drive_id(path: str) -> bool:
    """
    Check if a string is likely to be a Google Drive file ID.

    Args:
        path: The string to check

    Returns:
        True if the string looks like a Drive ID, False otherwise
    """
    if not isinstance(path, str):
        return False

    # Drive IDs are typically 25-45 chars and don't contain path separators or dots
    return (len(path) >= 25 and len(path) <= 45 and
            "/" not in path and "\\" not in path and
            "." not in path)


def extract_path_from_path_result_string(path_string: str) -> str:
    """
    Extract a path from a string representation of a PathResult.

    Args:
        path_string: A string that may be a string representation of a PathResult

    Returns:
        The extracted path if found, or the original string
    """
    if isinstance(path_string, str) and path_string.startswith("success="):
        # Try to extract the path using regex
        match = re.search(r"path=PosixPath\('([^']+)'\)", path_string)
        if match:
            return match.group(1)
    return path_string