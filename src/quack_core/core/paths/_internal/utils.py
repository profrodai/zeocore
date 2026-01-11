# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/_internal/utils.py
# module: quack_core.core.paths._internal.utils
# role: utils
# neighbors: __init__.py, context.py, resolver.py
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Utility functions for path resolution logic.

This module provides semantic utilities (finding roots, inferring modules).
Low-level path manipulations (join, split, normalize) are delegated to
`quack_core.core.fs`.
"""

import os
from typing import Any

from quack_core.core.errors import QuackFileNotFoundError, wrap_io_errors
from quack_core.core.fs.service import standalone
from quack_core.core.logging import get_logger
from quack_core.core.paths.models import PathInfo

logger = get_logger(__name__)


def _normalize_path_param(path_param: Any) -> str:
    """
    Helper to consistently convert any path-like object to a string.
    """
    if hasattr(path_param, "path") and path_param.path is not None:
        return str(path_param.path)
    if hasattr(path_param, "data") and path_param.data is not None:
        return str(path_param.data)
    if hasattr(path_param, "__fspath__"):
        return str(path_param)
    return str(path_param)


@wrap_io_errors
def _normalize_path_with_info(path: Any) -> PathInfo:
    """
    Normalize a path using core.fs and return detailed information.
    """
    path_str = _normalize_path_param(path)

    res = standalone.normalize_path(path_str)
    # Check success AND data
    if res.success and res.data:
        return PathInfo(success=True, path=str(res.data), error=None)

    # Fallback
    try:
        fallback = os.path.abspath(path_str)
        return PathInfo(success=True, path=fallback, error=None)
    except Exception as e:
        return PathInfo(success=False, path=path_str, error=e)


@wrap_io_errors
def _find_project_root(
        start_dir: Any | None = None,
        marker_files: list[str] | None = None,
        marker_dirs: list[str] | None = None,
        max_levels: int = 5,
) -> str:
    """
    Find project root by looking for markers in parent directories.
    """
    if start_dir is None:
        current_dir = os.getcwd()
    else:
        current_dir = _normalize_path_param(start_dir)

    # Normalize via FS and ensure string
    norm_res = standalone.normalize_path(current_dir)
    if norm_res.success and norm_res.data:
        current_dir = str(norm_res.data)
    else:
        current_dir = os.path.abspath(current_dir)

    markers = marker_files or [
        "pyproject.toml", "setup.py", ".git", ".quack", "quack_config.yaml"
    ]
    dir_markers = marker_dirs or ["src", "quack-core", "tests"]

    for _ in range(max_levels):
        # Check files
        for m in markers:
            res = standalone.join_path(current_dir, m)
            if res.success and res.data:
                check_path = str(res.data)
                if os.path.exists(check_path) and os.path.isfile(check_path):
                    return current_dir

        # Check dirs (need at least 2)
        found_dirs = 0
        for d in dir_markers:
            res = standalone.join_path(current_dir, d)
            if res.success and res.data:
                check_path = str(res.data)
                if os.path.exists(check_path) and os.path.isdir(check_path):
                    found_dirs += 1

        if found_dirs >= 2:
            return current_dir

        # Move up
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

    raise QuackFileNotFoundError(
        current_dir,
        "Could not find project root directory."
    )


@wrap_io_errors
def _find_nearest_directory(
        name: str,
        start_dir: Any | None = None,
        max_levels: int = 5,
) -> str:
    """
    Find the nearest directory with the given name by searching UPWARDS.
    """
    if start_dir is None:
        current_dir = os.getcwd()
    else:
        current_dir = _normalize_path_param(start_dir)

    norm_res = standalone.normalize_path(current_dir)
    if norm_res.success and norm_res.data:
        current_dir = str(norm_res.data)
    else:
        current_dir = os.path.abspath(current_dir)

    for _ in range(max_levels):
        res = standalone.join_path(current_dir, name)
        if res.success and res.data:
            candidate = str(res.data)
            if os.path.exists(candidate) and os.path.isdir(candidate):
                return candidate

        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

    raise QuackFileNotFoundError(
        name, f"Could not find directory '{name}' in or above {start_dir}"
    )


@wrap_io_errors
def _infer_module_from_path(
        path: Any,
        project_root: Any | None = None,
) -> str:
    """
    Infer a Python module name from a file path.
    """
    path_str = _normalize_path_param(path)

    # Determine root
    if project_root:
        root_str = _normalize_path_param(project_root)
    else:
        root_str = _find_project_root(os.path.dirname(path_str))

    # Absolute paths
    abs_path_res = standalone.normalize_path(path_str)
    abs_root_res = standalone.normalize_path(root_str)

    abs_path = str(
        abs_path_res.data) if abs_path_res.success and abs_path_res.data else os.path.abspath(
        path_str)
    abs_root = str(
        abs_root_res.data) if abs_root_res.success and abs_root_res.data else os.path.abspath(
        root_str)

    # Anchor to src
    try:
        src_dir = _find_nearest_directory("src", abs_root)
    except QuackFileNotFoundError:
        src_dir = abs_root

    # Relative path calculation
    try:
        rel_path = os.path.relpath(abs_path, src_dir)
    except ValueError:
        try:
            rel_path = os.path.relpath(abs_path, abs_root)
        except ValueError:
            return os.path.splitext(os.path.basename(abs_path))[0]

    if rel_path.startswith(".."):
        return os.path.splitext(os.path.basename(abs_path))[0]

    parts = rel_path.split(os.sep)

    if parts:
        parts[-1] = os.path.splitext(parts[-1])[0]
        if parts[-1] == "__init__":
            parts = parts[:-1]

    return ".".join(parts)


@wrap_io_errors
def _resolve_relative_to_project(
        path: Any,
        project_root: Any | None = None,
) -> str:
    """
    Resolve a path relative to the project root.
    """
    path_str = _normalize_path_param(path)

    if os.path.isabs(path_str):
        return path_str

    if project_root:
        root = _normalize_path_param(project_root)
    else:
        root = _find_project_root()

    res = standalone.join_path(root, path_str)
    if res.success and res.data:
        return str(res.data)

    return os.path.join(root, path_str)