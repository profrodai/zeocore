# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/file_ops.py
# module: quack_core.core.fs.api.public.file_ops
# role: api
# neighbors: __init__.py, checksums.py, disk.py, file_info.py, path_ops.py, path_utils.py (+2 more)
# exports: atomic_write, ensure_directory, find_files_by_content, get_unique_filename
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/api/public/file_ops.py
"""
Public API for file _operations.

This module provides safe, result-oriented wrappers around low-level file _operations.
"""

from pathlib import Path

from quack_core.fs._helpers.file_ops import (
    _atomic_write,
    _ensure_directory,
    _find_files_by_content,
    _get_unique_filename,
)
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.fs.results import DataResult, OperationResult, WriteResult
from quack_core.logging import get_logger

logger = get_logger(__name__)


def atomic_write(path: str | Path | DataResult | OperationResult,
                 content: str | bytes) -> WriteResult:
    """
    Write content to a file atomically using a temporary file.

    Args:
        path: Destination path (string, Path, DataResult, or OperationResult)
        content: Content to write (string or bytes)

    Returns:
        WriteResult with operation status
    """
    try:
        normalized_path = _normalize_path_param(path)
        result_path = _atomic_write(normalized_path, content)
        bytes_written = len(content.encode() if isinstance(content, str) else content)

        return WriteResult(
            success=True,
            path=result_path,
            bytes_written=bytes_written,
            message=f"Successfully wrote {bytes_written} bytes to {result_path} atomically",
        )
    except Exception as e:
        logger.error(f"Failed to write file {path} atomically: {e}")
        normalized_path = _normalize_path_param(path)
        return WriteResult(
            success=False,
            path=normalized_path,
            error=str(e),
            message="Failed to write file atomically",
        )


def ensure_directory(path: str | Path | DataResult | OperationResult,
                     exist_ok: bool = True) -> OperationResult:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists (string, Path, DataResult, or OperationResult)
        exist_ok: If False, raise an error when directory exists

    Returns:
        OperationResult with operation status
    """
    try:
        normalized_path = _normalize_path_param(path)
        created_path = _ensure_directory(normalized_path, exist_ok)
        return OperationResult(
            success=True,
            path=created_path,
            message=f"Directory {created_path} {'exists' if created_path.exists() else 'created'}",
        )
    except Exception as e:
        logger.error(f"Failed to ensure directory {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return OperationResult(
            success=False,
            path=normalized_path,
            error=str(e),
            message="Failed to ensure directory exists",
        )


def find_files_by_content(
        directory: str | Path | DataResult | OperationResult, text_pattern: str,
        recursive: bool = True
) -> DataResult[list[str]]:
    """
    Find files containing the given text pattern.

    Args:
        directory: Directory to search in (string, Path, DataResult, or OperationResult)
        text_pattern: Text pattern to search for
        recursive: Whether to search recursively

    Returns:
        DataResult with list of matching file paths
    """
    try:
        normalized_dir = _normalize_path_param(directory)
        matches = _find_files_by_content(normalized_dir, text_pattern, recursive)
        str_matches = [str(p) for p in matches]

        return DataResult(
            success=True,
            path=normalized_dir,
            data=str_matches,
            format="file_list",
            message=f"Found {len(matches)} files matching pattern '{text_pattern}'",
        )
    except Exception as e:
        logger.error(f"Failed to find files by content in {directory}: {e}")
        normalized_dir = _normalize_path_param(directory)
        return DataResult(
            success=False,
            path=normalized_dir,
            data=[],
            format="file_list",
            error=str(e),
            message="Failed to search for files by content",
        )


def get_unique_filename(
        directory: str | Path | DataResult | OperationResult, filename: str,
        raise_if_exists: bool = False
) -> DataResult[str]:
    """
    Generate a unique filename in the given directory.

    Args:
        directory: Directory path (string, Path, DataResult, or OperationResult)
        filename: Base filename
        raise_if_exists: If True, raise an error when the file exists

    Returns:
        DataResult with the unique filename
    """
    try:
        normalized_dir = _normalize_path_param(directory)
        result_path = _get_unique_filename(normalized_dir, filename, raise_if_exists)

        return DataResult(
            success=True,
            path=normalized_dir,
            data=str(result_path),
            format="path",
            message=f"Generated unique filename: {result_path}",
        )
    except Exception as e:
        logger.error(f"Failed to get unique filename in {directory}: {e}")
        normalized_dir = _normalize_path_param(directory)
        return DataResult(
            success=False,
            path=normalized_dir,
            data="",
            format="path",
            error=str(e),
            message="Failed to generate unique filename",
        )
