# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_helpers/file_ops.py
# module: quack_core.core.fs._helpers.file_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_helpers/file_ops.py
"""
Utility functions for file _operations.
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from quack_core.errors import (
    QuackFileExistsError,
    QuackFileNotFoundError,
    QuackIOError,
    QuackPermissionError,
    wrap_io_errors,
)

# Import the path normalization helper
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


@wrap_io_errors
def _get_unique_filename(
        directory: Any, filename: str, raise_if_exists: bool = False
) -> Path:
    """
    Generate a unique filename in the given directory.

    If the directory does not exist, raises QuackFileNotFoundError.
    If the provided filename is empty, raises QuackIOError.
    If raise_if_exists is True and the file exists, raises QuackFileExistsError.
    Otherwise, if the filename exists, adds a numeric suffix.

    Args:
        directory: Directory path (can be str, Path, or any object with 'data' attribute)
        filename: Base filename
        raise_if_exists: If True, raise an error when the file exists

    Returns:
        Unique Path object
    """
    # Normalize directory to Path object using the dedicated helper
    dir_path = _normalize_path_param(directory)

    if not dir_path.exists():
        logger.error(f"Directory does not exist: {directory}")
        raise QuackFileNotFoundError(str(directory), message="Directory does not exist")
    if not filename or not filename.strip():
        logger.error(f"Empty filename provided for directory: {directory}")
        raise QuackIOError("Filename cannot be empty", str(directory))

    # Create the full file path
    base_name = Path(filename).stem
    extension = Path(filename).suffix
    path = dir_path / filename

    if path.exists():
        if raise_if_exists:
            logger.error(f"File already exists: {path}")
            raise QuackFileExistsError(str(path), message="File already exists")
    else:
        logger.debug(f"Using original filename: {path}")
        return path

    counter = 1
    while True:
        new_name = f"{base_name}_{counter}{extension}"
        path = dir_path / new_name
        if not path.exists():
            logger.debug(f"Generated unique filename: {path}")
            return path
        counter += 1


@wrap_io_errors
def _ensure_directory(path: Any, exist_ok: bool = True) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists (can be str, Path, or any object with 'data' attribute)
        exist_ok: If False, raise an error when directory exists

    Returns:
        Path object for the directory

    Raises:
        QuackFileExistsError: If directory exists and exist_ok is False
        QuackPermissionError: If permission is denied
        QuackIOError: For other IO related issues
    """
    # Normalize to Path object using the dedicated helper
    path_obj = _normalize_path_param(path)

    try:
        path_obj.mkdir(parents=True, exist_ok=exist_ok)
        logger.debug(f"Ensured directory exists: {path_obj}")
        return path_obj
    except FileExistsError as e:
        logger.error(f"Directory already exists and exist_ok is False: {path_obj}")
        raise QuackFileExistsError(str(path_obj), original_error=e) from e
    except PermissionError as e:
        logger.error(f"Permission denied when creating directory: {path_obj}")
        raise QuackPermissionError(
            str(path_obj), "create directory", original_error=e
        ) from e
    except Exception as e:
        logger.error(f"Failed to create directory: {path_obj}, error: {e}")
        raise QuackIOError(
            f"Failed to create directory: {str(e)}", str(path_obj), original_error=e
        ) from e


@wrap_io_errors
def _atomic_write(path: Any, content: str | bytes) -> Path:
    """
    Write content to a file atomically using a temporary file.

    Args:
        path: Destination path (can be str, Path, or any object with 'data' attribute)
        content: Content to write (string or bytes)

    Returns:
        Path object for the written file

    Raises:
        QuackPermissionError: If permission is denied
        QuackIOError: For other IO related issues
    """
    # Normalize to Path object using the dedicated helper
    path_obj = _normalize_path_param(path)

    _ensure_directory(path_obj.parent)

    temp_dir = path_obj.parent
    temp_file = None

    try:
        fd, temp_path = tempfile.mkstemp(dir=temp_dir)
        temp_file = Path(temp_path)
        logger.debug(f"Created temporary file for atomic write: {temp_path}")

        with os.fdopen(fd, "wb" if isinstance(content, bytes) else "w") as f:
            f.write(content)

        # On Unix-like systems, rename is atomic
        os.replace(temp_path, path_obj)
        logger.debug(f"Successfully wrote content to {path_obj} atomically")
        return path_obj
    except Exception as e:
        logger.error(f"Failed to write file {path_obj} atomically: {e}")
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
                logger.debug(f"Cleaned up temporary file after error: {temp_file}")
            except Exception as unlink_error:
                logger.debug(
                    f"Failed to unlink temporary file {temp_file}: {unlink_error}"
                )
        raise QuackIOError(
            f"Failed to write file {path_obj}: {str(e)}", str(path_obj),
            original_error=e
        ) from e


@wrap_io_errors
def _find_files_by_content(
        directory: Any, text_pattern: str, recursive: bool = True
) -> list[Path]:
    """
    Find files containing the given text pattern.

    Args:
        directory: Directory to search in (can be str, Path, or any object with 'data' attribute)
        text_pattern: Text pattern to search for
        recursive: Whether to search recursively

    Returns:
        List of paths to files containing the pattern

    Raises:
        QuackIOError: If the provided regex pattern is invalid.
    """
    try:
        pattern = re.compile(text_pattern)
        logger.debug(f"Searching for pattern '{text_pattern}' in {directory}")
    except re.error as e:
        logger.error(f"Invalid regex pattern: {e}")
        raise QuackIOError(
            f"Invalid regex pattern: {e}", str(directory), original_error=e
        ) from e

    # Normalize directory to Path object using the dedicated helper
    directory_path = _normalize_path_param(directory)

    if not directory_path.exists() or not directory_path.is_dir():
        logger.warning(
            f"Directory does not exist or is not a directory: {directory_path}")
        return []

    matching_files = []
    all_files = (
        list(directory_path.glob("**/*"))
        if recursive
        else list(directory_path.glob("*"))
    )

    logger.debug(f"Found {len(all_files)} files to search through")

    for path in all_files:
        if not path.is_file():
            continue
        try:
            # Remove explicit "r" mode as it is the default for text files.
            with open(path, errors="ignore") as file_obj:
                content = file_obj.read()
                if pattern.search(content):
                    matching_files.append(path)
                    logger.debug(f"Found matching file: {path}")
        except (QuackIOError, OSError):
            # Skip files that raise an error (e.g. permission issues)
            logger.debug(f"Skipping file due to access error: {path}")
            continue

    logger.info(f"Found {len(matching_files)} files matching pattern '{text_pattern}'")
    return matching_files
