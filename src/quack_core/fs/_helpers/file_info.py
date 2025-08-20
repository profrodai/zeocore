# quack-core/src/quack-core/fs/_helpers/file_info.py
"""
Utility functions for getting file information.
"""

import platform
from typing import Any

from quackcore.errors import QuackFileNotFoundError, QuackIOError, wrap_io_errors

# Import path normalization helper
from quackcore.fs._helpers.path_utils import _normalize_path_param
from quackcore.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


def _get_file_size_str(size_bytes: int) -> str:
    """
    Convert file size in bytes to human-readable string.

    Args:
        size_bytes: File size in bytes

    Returns:
        Human-readable file size (e.g., "2.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024 or unit == "TB":
            if unit == "B":
                return f"{size_bytes} {unit}"
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024


@wrap_io_errors
def _get_file_timestamp(path: Any) -> float:
    """
    Get the latest timestamp (modification time) for a file.

    Args:
        path: Path to the file (can be str, Path, or any object with 'data' attribute)

    Returns:
        Timestamp as float

    Raises:
        QuackFileNotFoundError: If the file doesn't exist
        QuackIOError: For other IO related issues
    """
    # Normalize to Path object using the dedicated helper
    path_obj = _normalize_path_param(path)

    if not path_obj.exists():
        logger.error(f"File not found when getting timestamp: {path_obj}")
        raise QuackFileNotFoundError(str(path_obj))
    return path_obj.stat().st_mtime


def _get_mime_type(path: Any) -> str | None:
    """
    Get the MIME type of the file.

    Args:
        path: Path to the file (can be str, Path, or any object with 'data' attribute)

    Returns:
        MIME type string or None if not determinable
    """
    import mimetypes

    # Normalize using the dedicated helper
    path_obj = _normalize_path_param(path)

    mime_type, _ = mimetypes.guess_type(str(path_obj))
    if mime_type:
        logger.debug(f"Detected MIME type for {path_obj}: {mime_type}")
    else:
        logger.debug(f"Could not determine MIME type for {path_obj}")
    return mime_type


def _is_file_locked(path: Any) -> bool:
    """
    Check if a file is locked by another process.

    Args:
        path: Path to the file (can be str, Path, or any object with 'data' attribute)

    Returns:
        True if the file is locked
    """
    # Normalize using the dedicated helper
    path_obj = _normalize_path_param(path)

    if not path_obj.exists():
        return False
    try:
        with open(path_obj, "r+") as f:
            if platform.system() == "Windows":
                import msvcrt

                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return False
    except (OSError, QuackIOError):
        logger.debug(f"File {path_obj} is locked by another process")
        return True
    except ImportError:
        logger.warning(
            f"Cannot check lock status for {path_obj}: "
            f"platform-specific modules not available"
        )
        return False


def _get_file_type(path: Any) -> str:
    """
    Get the type of the file.

    Args:
        path: Path to the file (can be str, Path, or any object with 'data' attribute)

    Returns:
        File type string (e.g., "text", "binary", "directory", "symlink")
    """
    # Normalize using the dedicated helper
    path_obj = _normalize_path_param(path)

    if not path_obj.exists():
        return "nonexistent"
    if path_obj.is_dir():
        return "directory"
    if path_obj.is_symlink():
        return "symlink"
    try:
        with open(path_obj, errors="ignore") as f:
            chunk = f.read(1024)
            # If for some reason we get a str, encode it to bytes.
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            if b"\0" in chunk:
                return "binary"
            return "text"
    except (QuackIOError, OSError) as e:
        logger.error(f"Error determining file type for {path_obj}: {e}")
        return "unknown"
