# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/file_info.py
# module: quack_core.core.fs.api.public.file_info
# role: api
# neighbors: __init__.py, checksums.py, disk.py, file_ops.py, path_ops.py, path_utils.py (+2 more)
# exports: get_file_type, get_file_size_str, get_file_timestamp, get_mime_type, is_file_locked
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/api/public/file_info.py
"""
Public API for file information _operations.

This module provides safe, result-oriented wrappers around low-level file info _operations.
"""

from pathlib import Path

from quack_core.fs._helpers.file_info import (
    _get_file_size_str,
    _get_file_timestamp,
    _get_file_type,
    _get_mime_type,
    _is_file_locked,
)
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.fs.results import DataResult, OperationResult
from quack_core.logging import get_logger

logger = get_logger(__name__)


def get_file_type(path: str | Path | DataResult | OperationResult) -> DataResult[str]:
    """
    Get the type of a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with file type string (e.g., "text", "binary", "directory", "symlink")
    """
    try:
        normalized_path = _normalize_path_param(path)
        file_type = _get_file_type(normalized_path)

        return DataResult(
            success=True,
            path=normalized_path,
            data=file_type,
            format="file_type",
            message=f"File {normalized_path} is of type: {file_type}",
        )
    except Exception as e:
        logger.error(f"Failed to get file type for {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return DataResult(
            success=False,
            path=normalized_path,
            data="unknown",
            format="file_type",
            error=str(e),
            message="Failed to determine file type",
        )


def get_file_size_str(size_bytes: int) -> DataResult[str]:
    """
    Convert file size in bytes to a human-readable string.

    Args:
        size_bytes: File size in bytes

    Returns:
        DataResult with human-readable file size (e.g., "2.5 MB")
    """
    try:
        size_str = _get_file_size_str(size_bytes)

        return DataResult(
            success=True,
            path=None,  # Not applicable for this function
            data=size_str,
            format="file_size",
            message=f"Converted {size_bytes} bytes to human-readable format: {size_str}",
        )
    except Exception as e:
        logger.error(f"Failed to convert size {size_bytes} to string: {e}")
        return DataResult(
            success=False,
            path=None,
            data=f"{size_bytes} B",
            format="file_size",
            error=str(e),
            message="Failed to format file size",
        )


def get_file_timestamp(path: str | Path | DataResult | OperationResult) -> DataResult[
    float]:
    """
    Get the latest timestamp (modification time) for a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with timestamp as float
    """
    try:
        normalized_path = _normalize_path_param(path)
        timestamp = _get_file_timestamp(normalized_path)

        return DataResult(
            success=True,
            path=normalized_path,
            data=timestamp,
            format="timestamp",
            message=f"Retrieved file timestamp: {timestamp}",
        )
    except Exception as e:
        logger.error(f"Failed to get file timestamp for {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return DataResult(
            success=False,
            path=normalized_path,
            data=0.0,
            format="timestamp",
            error=str(e),
            message="Failed to get file timestamp",
        )


def get_mime_type(path: str | Path | DataResult | OperationResult) -> DataResult[str | None]:
    """
    Get the MIME type of a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with MIME type string or None if not determinable
    """
    try:
        normalized_path = _normalize_path_param(path)
        mime_type = _get_mime_type(normalized_path)

        message = (
            f"MIME type for {normalized_path}: {mime_type}"
            if mime_type
            else f"Could not determine MIME type for {normalized_path}"
        )

        return DataResult(
            success=True,
            path=normalized_path,
            data=mime_type,
            format="mime_type",
            message=message,
        )
    except Exception as e:
        logger.error(f"Failed to get MIME type for {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return DataResult(
            success=False,
            path=normalized_path,
            data=None,
            format="mime_type",
            error=str(e),
            message="Failed to determine MIME type",
        )


def is_file_locked(path: str | Path | DataResult | OperationResult) -> DataResult[bool]:
    """
    Check if a file is locked by another process.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with boolean indicating if file is locked
    """
    try:
        normalized_path = _normalize_path_param(path)
        is_locked = _is_file_locked(normalized_path)

        return DataResult(
            success=True,
            path=normalized_path,
            data=is_locked,
            format="boolean",
            message=f"File {normalized_path} is {'locked' if is_locked else 'not locked'}",
        )
    except Exception as e:
        logger.error(f"Failed to check if file is locked {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return DataResult(
            success=False,
            path=normalized_path,
            data=False,
            format="boolean",
            error=str(e),
            message="Failed to check if file is locked",
        )
