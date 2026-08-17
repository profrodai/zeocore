"""
Utility functions for path resolution logic.

This module provides semantic utilities (finding roots, inferring modules).
Low-level path manipulations (join, split, normalize) are delegated to
`zeo_core.core.fs`.
"""

import os

from zeo_core.core.errors import ZeoFileNotFoundError, wrap_io_errors
from zeo_core.core.fs.protocols import FsPathLike
from zeo_core.core.fs.service import standalone
from zeo_core.core.logging import get_logger
from zeo_core.core.paths.models import PathInfo

logger = get_logger(__name__)


def _normalize_path_param(path_param: FsPathLike) -> str:
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
def _normalize_path_with_info(path: FsPathLike) -> PathInfo:
    """
    Normalize a path using core.fs and return detailed information.
    """
    path_str = _normalize_path_param(path)

    res = standalone.normalize_path(path_str)
    # Check success AND data
    if res.ok and res.path:
        return PathInfo(success=True, path=str(res.path), error=None)

    # Fallback
    try:
        fallback = os.path.abspath(path_str)
        return PathInfo(success=True, path=fallback, error=None)
    except Exception as e:
        return PathInfo(success=False, path=path_str, error=e)


def _has_marker_file(current_dir: str, markers: list[str]) -> bool:
    """
    True if any marker filename in `markers` exists as a FILE directly under
    `current_dir`. Extracted from _find_project_root to keep its own branch
    count under the C901 threshold; behavior/order unchanged from the
    original inline loop.
    """
    for m in markers:
        res = standalone.join_path(current_dir, m)
        if res.ok and res.data:
            check_path = str(res.data)
            if os.path.exists(check_path) and os.path.isfile(check_path):
                return True
    return False


def _has_root_marker(current_dir: str) -> bool:
    """
    True if `current_dir` looks like a project root by the standard Python-
    project convention: it directly contains a `pyproject.toml` FILE, or a
    `.git` entry (a DIRECTORY in a normal clone; a FILE in a git worktree/
    submodule, where it holds a `gitdir:` pointer -- both count).

    This replaces the old package-name-specific heuristic (a hardcoded
    "quack-core" directory name plus a marker_dirs>=2 count) with a
    convention that carries no assumption about this package's own name or
    directory layout, so it stays correct if the repo is ever renamed or
    restructured again.
    """
    pyproject_res = standalone.join_path(current_dir, "pyproject.toml")
    if pyproject_res.ok and pyproject_res.data:
        pyproject_path = str(pyproject_res.data)
        if os.path.isfile(pyproject_path):
            return True

    git_res = standalone.join_path(current_dir, ".git")
    if git_res.ok and git_res.data:
        git_path = str(git_res.data)
        if os.path.exists(git_path):
            return True

    return False


def _count_marker_dirs(current_dir: str, dir_markers: list[str]) -> int:
    """
    Count how many marker directory names in `dir_markers` exist as a
    DIRECTORY directly under `current_dir`. Extracted from _find_project_root
    for the same C901 reason as _has_marker_file.
    """
    found_dirs = 0
    for d in dir_markers:
        res = standalone.join_path(current_dir, d)
        if res.ok and res.data:
            check_path = str(res.data)
            if os.path.exists(check_path) and os.path.isdir(check_path):
                found_dirs += 1
    return found_dirs


@wrap_io_errors
def _find_project_root(
    start_dir: FsPathLike | None = None,
    marker_files: list[str] | None = None,
    marker_dirs: list[str] | None = None,
    max_levels: int = 5,
) -> str:
    """
    Find project root by walking up from `start_dir` (default: CWD) looking
    for the standard Python-project markers: a `pyproject.toml` file, or a
    `.git` entry -- see `_has_root_marker`. Stops at the first directory
    (walking upward, `max_levels` levels max) that qualifies.

    This is a convention-based check with NO hardcoded package or directory
    name -- it does not know or care what this project (or any caller's
    project) happens to be named. A prior version of this function looked
    for a directory literally named "quack-core" (this package's own former
    name) among its markers, which broke the moment the package was
    renamed; walking up for pyproject.toml/.git has no such coupling and
    survives a future rename for free.

    `marker_files` / `marker_dirs`, if given, are additional CALLER-SUPPLIED
    checks layered on top of (not instead of) the pyproject.toml/.git check:
    a directory also qualifies if it directly contains any file named in
    `marker_files`, or contains at least 2 of the directories named in
    `marker_dirs`. This preserves the existing opt-in override contract
    (callers that pass their own markers keep working exactly as before)
    without hardcoding any default package/directory name when no override
    is given.
    """
    if start_dir is None:
        current_dir = os.getcwd()
    else:
        current_dir = _normalize_path_param(start_dir)

    # Normalize via FS and ensure string
    norm_res = standalone.normalize_path(current_dir)
    if norm_res.ok and norm_res.path:
        current_dir = str(norm_res.path)
    else:
        current_dir = os.path.abspath(current_dir)

    for _ in range(max_levels):
        if _has_root_marker(current_dir):
            return current_dir

        if marker_files and _has_marker_file(current_dir, marker_files):
            return current_dir

        if marker_dirs and _count_marker_dirs(current_dir, marker_dirs) >= 2:
            return current_dir

        # Move up
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

    raise ZeoFileNotFoundError(current_dir, "Could not find project root directory.")


@wrap_io_errors
def _find_nearest_directory(
    name: str,
    start_dir: FsPathLike | None = None,
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
    if norm_res.ok and norm_res.path:
        current_dir = str(norm_res.path)
    else:
        current_dir = os.path.abspath(current_dir)

    for _ in range(max_levels):
        res = standalone.join_path(current_dir, name)
        if res.ok and res.data:
            candidate = str(res.data)
            if os.path.exists(candidate) and os.path.isdir(candidate):
                return candidate

        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

    raise ZeoFileNotFoundError(
        name, f"Could not find directory '{name}' in or above {start_dir}"
    )


@wrap_io_errors
def _infer_module_from_path(
    path: FsPathLike,
    project_root: FsPathLike | None = None,
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

    abs_path = (
        str(abs_path_res.path)
        if abs_path_res.ok and abs_path_res.path
        else os.path.abspath(path_str)
    )
    abs_root = (
        str(abs_root_res.path)
        if abs_root_res.ok and abs_root_res.path
        else os.path.abspath(root_str)
    )

    # Anchor to src
    try:
        src_dir = _find_nearest_directory("src", abs_root)
    except ZeoFileNotFoundError:
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
    path: FsPathLike,
    project_root: FsPathLike | None = None,
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
    if res.ok and res.data:
        return str(res.data)

    return os.path.join(root, path_str)
