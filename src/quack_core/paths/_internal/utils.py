# quack-core/src/quack-core/paths/_internal/utils.py
"""
Utility functions for path resolution.

This module provides utility functions for path resolution,
including functions for finding project roots and navigating directories.
All path values are handled as strings and filesystem operations are delegated
to quack-core.fs or built-in os.path utilities.
"""

import os
from typing import Any

from quack_core.errors import QuackFileNotFoundError, wrap_io_errors
from quack_core.fs.service import standalone
from quack_core.logging import get_logger
from quack_core.paths._internal.context import PathInfo

# Get module-specific logger
logger = get_logger(__name__)


@wrap_io_errors
def _normalize_path_with_info(path: Any) -> PathInfo:
    """
    Normalize a path and return detailed information about the result.

    Args:
        path: The path to normalize (string, Path, DataResult, or OperationResult).

    Returns:
        A PathInfo object containing the normalized absolute path (as a string)
        and a success flag.
    """
    # Convert input to string early
    if hasattr(path, "data"):
        path_content = path.data
    else:
        path_content = path
    if hasattr(path_content, "__fspath__"):
        path_str = str(path_content)
    else:
        path_str = str(path_content)

    try:
        # Delegate normalization to the fs layer; fs.normalize_path returns a Path,
        # so we convert it to string.
        normalized = str(standalone.normalize_path(path_str))
        return PathInfo(success=True, path=normalized, error=None)
    except Exception as e:
        # Fallback: use os.path.abspath as a backup
        try:
            fallback = os.path.abspath(path_str)
        except Exception:
            fallback = "/" + path_str
        return PathInfo(success=False, path=fallback, error=e)

@wrap_io_errors
def _find_project_root(
    start_dir: Any | None = None,
    marker_files: list[str] | None = None,
    marker_dirs: list[str] | None = None,
    max_levels: int = 5,
) -> str:
    """
    Find the project root directory by looking for marker files or directories.

    Args:
        start_dir: Directory to start searching from (string, Path, DataResult, or OperationResult; defaults to current working directory)
        marker_files: List of filenames that indicate a project root
        marker_dirs: List of directory names that indicate a project root
        max_levels: Maximum number of parent directories to check

    Returns:
        The project root directory as a string.

    Raises:
        QuackFileNotFoundError: If the project root cannot be found.
    """
    # Normalize input
    if start_dir is None:
        current_dir = os.getcwd()
    else:
        if hasattr(start_dir, "data"):
            sd = start_dir.data
        else:
            sd = start_dir
        current_dir = str(sd)

    # Set default marker values if not provided
    default_marker_files = [
        "pyproject.toml",
        "setup.py",
        ".git",
        ".quack",
        "quack_config.yaml",
    ]
    default_marker_dirs = ["src", "quack-core", "tests"]
    marker_files = marker_files or default_marker_files
    marker_dirs = marker_dirs or default_marker_dirs

    for _ in range(max_levels):
        # Check for marker files
        if any(
            os.path.exists(os.path.join(current_dir, marker)) for marker in marker_files
        ):
            return current_dir
        # Check for marker directories (require at least two)
        count = sum(
            1
            for marker in marker_dirs
            if os.path.isdir(os.path.join(current_dir, marker))
        )
        if count >= 2:
            return current_dir
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

    raise QuackFileNotFoundError(
        current_dir,
        "Could not find project root directory. Please specify it explicitly.",
    )


@wrap_io_errors
def _find_nearest_directory(
    name: str,
    start_dir: Any | None = None,
    max_levels: int = 5,
) -> str:
    """
    Find the nearest directory with the given name.

    Args:
        name: Name of the directory to find.
        start_dir: Directory to start searching from (string, Path, DataResult, or OperationResult; defaults to current working directory).
        max_levels: Maximum number of parent directories to check.

    Returns:
        The path to the nearest directory with the given name, as a string.

    Raises:
        QuackFileNotFoundError: If the directory cannot be found.
    """
    # Normalize input
    if start_dir is None:
        base_dir = os.getcwd()
    else:
        if hasattr(start_dir, "data"):
            sd = start_dir.data
        else:
            sd = start_dir
        base_dir = str(sd)

    # First, search in the directory tree below base_dir.
    for root, dirs, _ in os.walk(base_dir):
        if name in dirs:
            return os.path.join(root, name)

    # If not found, search upward.
    current_dir = base_dir
    for _ in range(max_levels):
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
        candidate = os.path.join(current_dir, name)
        if os.path.isdir(candidate):
            return candidate

    raise QuackFileNotFoundError(
        name, f"Could not find directory '{name}' in or near {base_dir}"
    )


@wrap_io_errors
def _resolve_relative_to_project(
    path: Any,
    project_root: Any | None = None,
) -> str:
    """
    Resolve a path relative to the project root.

    Args:
        path: The path to resolve (string, Path, DataResult, or OperationResult).
        project_root: The project root directory (string, Path, DataResult, or OperationResult; if not provided, auto-detect).

    Returns:
        The resolved absolute path as a string.

    Raises:
        QuackFileNotFoundError: If the project root cannot be determined.
    """
    # Normalize input
    if hasattr(path, "data"):
        p = path.data
    else:
        p = path
    path_str = str(p)

    if project_root is None:
        root = None
    else:
        if hasattr(project_root, "data"):
            pr = project_root.data
        else:
            pr = project_root
        root = str(pr)

    if os.path.isabs(path_str):
        return path_str

    if root is None:
        try:
            root = _find_project_root()
        except QuackFileNotFoundError:
            root = os.getcwd()

    return os.path.join(root, path_str)


@wrap_io_errors
def _normalize_path(path: Any) -> str:
    """
    Normalize a path for cross-platform compatibility.

    This function uses normalize_path_with_info to provide detailed normalization information.

    Args:
        path: The path to normalize (string, Path, DataResult, or OperationResult).

    Returns:
        The normalized absolute path as a string.
    """
    # Normalize input
    if hasattr(path, "data"):
        p = path.data
    else:
        p = path
    path_str = str(p)

    info = _normalize_path_with_info(path_str)
    return info.path


@wrap_io_errors
def _join_path(*parts: Any) -> str:
    """
    Join path components.

    Args:
        *parts: Path parts as strings, bytes, Path, DataResult, or OperationResult. Bytes parts are decoded using UTF-8.

    Returns:
        The joined path as a string.
    """
    converted_parts: list[str] = []
    for part in parts:
        # Extract underlying data for result types
        if hasattr(part, "data"):
            part = part.data
        # Decode or stringify
        if isinstance(part, bytes):
            converted_parts.append(part.decode("utf-8"))
        elif hasattr(part, "__fspath__"):
            converted_parts.append(str(part))
        else:
            converted_parts.append(str(part))

    if not converted_parts:
        return ""

    result = converted_parts[0]
    if len(converted_parts) > 1:
        result = os.path.join(result, *converted_parts[1:])
    return result


@wrap_io_errors
def _split_path(path: Any) -> list[str]:
    """
    Split a path into its components.

    Args:
        path: The path (string, Path, DataResult, or OperationResult) to split.

    Returns:
        A list of path components as strings.
    """
    # Normalize input
    if hasattr(path, "data"):
        p = path.data
    else:
        p = path
    path_str = str(p)

    norm = os.path.normpath(path_str)
    return norm.split(os.sep)


def _get_extension(path: Any) -> str:
    """
    Get the file extension from a path.

    Args:
        path: The file path (string, Path, DataResult, or OperationResult).

    Returns:
        The file extension without the leading dot.
        For dotfiles, returns the filename without the leading dot.
    """
    # Normalize input
    if hasattr(path, "data"):
        p = path.data
    else:
        p = path
    path_str = str(p)

    filename = os.path.basename(path_str)
    if filename.startswith(".") and "." not in filename[1:]:
        return filename[1:]
    _, ext = os.path.splitext(filename)
    return ext[1:] if ext.startswith('.') else ext


# Helper functions used internally

def _resolve_project_root(path_str: Any, project_root: Any | None) -> str:
    """
    Resolve the project root for a given path.

    Args:
        path_str: The path being processed (string, Path, DataResult, or OperationResult).
        project_root: Provided project root or None.

    Returns:
        A valid project root as a string.
    """
    # Normalize input
    if hasattr(path_str, "data"):
        ps = path_str.data
    else:
        ps = path_str
    pstr = str(ps)

    if project_root is not None:
        if hasattr(project_root, "data"):
            pr = project_root.data
        else:
            pr = project_root
        return str(pr)
    try:
        return _find_project_root()
    except QuackFileNotFoundError as e:
        logger.error(f"Project root not found: {e}")
        try:
            return os.getcwd()
        except Exception as ex:
            logger.error(f"Error obtaining current working directory: {ex}")
            return os.path.dirname(pstr) if not os.path.isabs(pstr) else "/"


def _get_relative_parts(path_str: Any, base: Any) -> list[str] | None:
    """
    Get relative path parts of a path with respect to a base directory.

    Args:
        path_str: The absolute path (string, Path, DataResult, or OperationResult).
        base: The base directory (string, Path, DataResult, or OperationResult).

    Returns:
        A list of parts if the relative path can be computed, otherwise None.
    """
    # Normalize inputs
    if hasattr(path_str, "data"):
        ps = path_str.data
    else:
        ps = path_str
    if hasattr(base, "data"):
        bs = base.data
    else:
        bs = base
    pstr = str(ps)
    bstr = str(bs)

    try:
        rel = os.path.relpath(pstr, bstr)
        return rel.split(os.sep)
    except ValueError:
        return None


@wrap_io_errors
def _infer_module_from_path(
    path: Any,
    project_root: Any | None = None,
) -> str:
    """
    Infer a Python module name from a file path.

    Args:
        path: The path to the Python file (string, Path, DataResult, or OperationResult).
        project_root: Project root directory (string, Path, DataResult, or OperationResult; if not provided, auto-detect).

    Returns:
        The inferred Python module name as a string.
    """
    # Normalize inputs
    if hasattr(path, "data"):
        p = path.data
    else:
        p = path
    path_str = str(p)

    if project_root is None:
        root = None
    else:
        if hasattr(project_root, "data"):
            pr = project_root.data
        else:
            pr = project_root
        root = str(pr)

    resolved_root = _resolve_project_root(path_str, root)
    abs_path = path_str if os.path.isabs(path_str) else os.path.join(resolved_root, path_str)
    try:
        src_dir = _find_nearest_directory("src", resolved_root)
        logger.debug(f"Found source directory: {src_dir}")
    except Exception:
        src_dir = resolved_root
        logger.debug(f"Source directory not found, using project root: {src_dir}")
    parts = _get_relative_parts(abs_path, src_dir)
    if parts is None:
        parts = _get_relative_parts(abs_path, resolved_root)
    if parts is None:
        logger.debug("Could not compute relative path, using file stem.")
        return os.path.splitext(os.path.basename(abs_path))[0]
    if parts and "." in parts[-1]:
        parts[-1] = parts[-1].split(".", 1)[0]
    parts = [p for p in parts if p and not p.startswith("__")]
    if "/outside/project/" in abs_path:
        result = parts[-1] if parts else os.path.splitext(os.path.basename(abs_path))[0]
        logger.debug(f"Path is outside project, using: {result}")
        return result
    result = ".".join(parts)
    logger.debug(f"Inferred module name: {result}")
    return result


def _normalize_path_param(path_param: Any) -> str:
    """
    Normalize a path parameter to a string.

    Helper function to consistently handle different path input types.

    Args:
        path_param: Path parameter (string, Path, DataResult, OperationResult)

    Returns:
        Normalized path string
    """
    # Handle different result types
    if hasattr(path_param, "path") and path_param.path is not None:
        # If it has a path attribute (like PathResult), use that
        return str(path_param.path)
    elif hasattr(path_param, "data") and path_param.data is not None:
        # If it has a data attribute (like DataResult), use that
        path_content = path_param.data
    else:
        path_content = path_param

    # Handle Path objects
    if hasattr(path_content, "__fspath__"):
        return str(path_content)

    # Convert other types to string
    return str(path_content)
