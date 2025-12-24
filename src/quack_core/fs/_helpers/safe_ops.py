# quack-core/src/quack_core/fs/_helpers/safe_ops.py
"""
Utility functions for safe file _operations (copy, move, delete).
"""

import shutil
from pathlib import Path
from typing import Any

from quack_core.errors import (
    QuackFileExistsError,
    QuackFileNotFoundError,
    QuackIOError,
    QuackPermissionError,
    wrap_io_errors,
)

# Import path normalization helper
from quack_core.fs._helpers.path_utils import _normalize_path_param

# Import from within package
from quack_core.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


@wrap_io_errors
def _safe_copy(src: Any, dst: Any, overwrite: bool = False) -> Path:
    """
    Safely copy a file or directory.

    Args:
        src: Source path (can be str, Path, or any object with 'data' attribute)
        dst: Destination path (can be str, Path, or any object with 'data' attribute)
        overwrite: If True, overwrite destination if it exists

    Returns:
        Path object for the destination

    Raises:
        QuackFileNotFoundError: If source doesn't exist
        QuackFileExistsError: If destination exists and overwrite is False
        QuackPermissionError: If permission is denied
        QuackIOError: For other IO related issues
    """
    # Normalize inputs using the dedicated helper
    src_path = _normalize_path_param(src)
    dst_path = _normalize_path_param(dst)

    if not src_path.exists():
        logger.error(f"Source does not exist: {src_path}")
        raise QuackFileNotFoundError(str(src_path))

    if dst_path.exists() and not overwrite:
        logger.error(f"Destination exists and overwrite is False: {dst_path}")
        raise QuackFileExistsError(str(dst_path))

    try:
        if src_path.is_dir():
            logger.info(f"Copying directory {src_path} to {dst_path}")
            if dst_path.exists() and overwrite:
                logger.debug(f"Removing existing destination directory: {dst_path}")
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
        else:
            logger.info(f"Copying file {src_path} to {dst_path}")
            # Use a locally imported ensure_directory to avoid circular imports
            from quack_core.fs._helpers.file_ops import _ensure_directory
            _ensure_directory(dst_path.parent)
            shutil.copy2(src_path, dst_path)
        return dst_path
    except PermissionError as e:
        logger.error(f"Permission denied when copying {src_path} to {dst_path}: {e}")
        message = f"Permission denied when copying {src_path} to {dst_path}: {str(e)}"
        raise QuackPermissionError(str(dst_path), "copy", message=message, original_error=e) from e
    except Exception as e:
        logger.error(f"Failed to copy {src_path} to {dst_path}: {e}")
        message = f"Failed to copy {src_path} to {dst_path}: {str(e)}"
        raise QuackIOError(message, str(dst_path), original_error=e) from e


@wrap_io_errors
def _safe_move(src: Any, dst: Any, overwrite: bool = False) -> Path:
    """
    Safely move a file or directory.

    Args:
        src: Source path (can be str, Path, or any object with 'data' attribute)
        dst: Destination path (can be str, Path, or any object with 'data' attribute)
        overwrite: If True, overwrite destination if it exists

    Returns:
        Path object for the destination

    Raises:
        QuackFileNotFoundError: If source doesn't exist
        QuackFileExistsError: If destination exists and overwrite is False
        QuackPermissionError: If permission is denied
        QuackIOError: For other IO related issues
    """
    # Normalize inputs using the dedicated helper
    src_path = _normalize_path_param(src)
    dst_path = _normalize_path_param(dst)

    if not src_path.exists():
        logger.error(f"Source does not exist: {src_path}")
        raise QuackFileNotFoundError(str(src_path))

    if dst_path.exists() and not overwrite:
        logger.error(f"Destination exists and overwrite is False: {dst_path}")
        raise QuackFileExistsError(str(dst_path))

    try:
        logger.info(f"Moving {src_path} to {dst_path}")
        # Use a locally imported ensure_directory to avoid circular imports
        from quack_core.fs._helpers.file_ops import _ensure_directory
        _ensure_directory(dst_path.parent)

        if dst_path.exists() and overwrite:
            if dst_path.is_dir():
                logger.debug(f"Removing existing destination directory: {dst_path}")
                shutil.rmtree(dst_path)
            else:
                logger.debug(f"Removing existing destination file: {dst_path}")
                dst_path.unlink()
        shutil.move(str(src_path), str(dst_path))
        return dst_path
    except PermissionError as e:
        logger.error(f"Permission denied when moving {src_path} to {dst_path}: {e}")
        message = f"Permission denied when moving {src_path} to {dst_path}: {str(e)}"
        raise QuackPermissionError(str(dst_path), "move", message=message, original_error=e) from e
    except Exception as e:
        logger.error(f"Failed to move {src_path} to {dst_path}: {e}")
        message = f"Failed to move {src_path} to {dst_path}: {str(e)}"
        raise QuackIOError(message, str(dst_path), original_error=e) from e


@wrap_io_errors
def _safe_delete(path: Any, missing_ok: bool = True) -> bool:
    """
    Safely delete a file or directory.

    Args:
        path: Path to delete (can be str, Path, or any object with 'data' attribute)
        missing_ok: If True, don't raise error if path doesn't exist

    Returns:
        True if deletion was successful,
        False if path didn't exist and missing_ok is True

    Raises:
        QuackFileNotFoundError: If path doesn't exist and missing_ok is False
        QuackPermissionError: If permission is denied
        QuackIOError: For other IO related issues
    """
    # Normalize using the dedicated helper
    path_obj = _normalize_path_param(path)

    if not path_obj.exists():
        if missing_ok:
            logger.debug(f"Path does not exist but missing_ok is True: {path_obj}")
            return False
        logger.error(f"Path does not exist and missing_ok is False: {path_obj}")
        raise QuackFileNotFoundError(str(path_obj))

    try:
        if path_obj.is_dir():
            logger.info(f"Deleting directory: {path_obj}")
            shutil.rmtree(path_obj)
        else:
            logger.info(f"Deleting file: {path_obj}")
            path_obj.unlink()
        return True
    except PermissionError as e:
        logger.error(f"Permission denied when deleting {path_obj}: {e}")
        message = f"Permission denied when deleting {path_obj}: {str(e)}"
        raise QuackPermissionError(str(path_obj), "delete", message=message, original_error=e) from e
    except Exception as e:
        logger.error(f"Failed to delete {path_obj}: {e}")
        message = f"Failed to delete {path_obj}: {str(e)}"
        raise QuackIOError(message, str(path_obj), original_error=e) from e
