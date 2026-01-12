# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/comparison.py
# module: quack_core.core.fs._internal.comparison
# role: module
# neighbors: __init__.py, checksums.py, common.py, directory_ops.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: d5eb52c8
# === QV-LLM:END ===

import os
from pathlib import Path


def _is_same_file(path1: Path, path2: Path) -> bool:
    """
    Check if two paths refer to the same file.
    Falls back to resolved path comparison on OSError.
    """
    try:
        return os.path.samefile(str(path1), str(path2))
    except OSError:
        # Fallback for non-existent paths or permission issues
        try:
            return path1.resolve() == path2.resolve()
        except (OSError, RuntimeError):
            # If resolve fails (permissions, symlink loops, etc), paths are not the same
            return False


def _is_subdirectory(child: Path, parent: Path) -> bool:
    """
    Check if child is a subdirectory of parent.
    Returns False if child == parent (not a subdirectory, but the same directory).
    """
    try:
        child_path = child.resolve()
        parent_path = parent.resolve()
    except (OSError, RuntimeError) as e:
        # If we can't resolve paths, we can't determine subdirectory relationship
        raise OSError(f"Failed to resolve paths for subdirectory check: {e}") from e

    if child_path == parent_path:
        return False

    try:
        child_path.relative_to(parent_path)
        return True
    except ValueError:
        return False