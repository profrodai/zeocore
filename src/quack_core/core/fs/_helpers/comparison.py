# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_helpers/comparison.py
# module: quack_core.core.fs._helpers.comparison
# role: module
# neighbors: __init__.py, checksums.py, common.py, disk.py, file_info.py, file_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_helpers/comparison.py
"""
Utility functions for comparing files and paths.
"""

import os
from typing import Any

# Import from within package
from quack_core.fs._helpers.common import _normalize_path
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


def _is_same_file(path1: Any, path2: Any) -> bool:
    """
    Check if two paths refer to the same file.

    Args:
        path1: First path (can be str, Path, or any object with 'data' attribute)
        path2: Second path (can be str, Path, or any object with 'data' attribute)

    Returns:
        True if paths refer to the same file
    """
    # Normalize inputs using the dedicated helper
    path1_obj = _normalize_path_param(path1)
    path2_obj = _normalize_path_param(path2)

    try:
        return os.path.samefile(str(path1_obj), str(path2_obj))
    except OSError:
        # If one or both files don't exist, compare normalized paths.
        return _normalize_path(path1_obj) == _normalize_path(path2_obj)


def _is_subdirectory(child: Any, parent: Any) -> bool:
    """
    Check if a path is a subdirectory of another path.

    Args:
        child: Potential child path (can be str, Path, or any object with 'data' attribute)
        parent: Potential parent path (can be str, Path, or any object with 'data' attribute)

    Returns:
        True if child is a subdirectory of parent
    """
    # Normalize inputs using the dedicated helper
    child_path = _normalize_path(_normalize_path_param(child))
    parent_path = _normalize_path(_normalize_path_param(parent))

    # A directory cannot be a subdirectory of itself
    if child_path == parent_path:
        return False

    try:
        child_path.relative_to(parent_path)
        return True
    except ValueError:
        return False
