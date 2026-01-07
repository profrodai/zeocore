# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/safe_ops.py
# module: quack_core.core.fs.api.public.safe_ops
# role: api
# neighbors: __init__.py, checksums.py, disk.py, file_info.py, file_ops.py, path_ops.py (+2 more)
# exports: copy_safely, move_safely, delete_safely
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/api/public/safe_ops.py
"""
Public API for safe file _operations (copy, move, delete).

This module provides safe, result-oriented wrappers around low-level
safe file _operations.
"""

from pathlib import Path

from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.fs._helpers.safe_ops import _safe_copy, _safe_delete, _safe_move
from quack_core.fs.results import DataResult, OperationResult, WriteResult
from quack_core.logging import get_logger

logger = get_logger(__name__)


def copy_safely(
        src: str | Path | DataResult | OperationResult,
        dst: str | Path | DataResult | OperationResult, overwrite: bool = False
) -> WriteResult:
    """
    Safely copy a file or directory.

    Args:
        src: Source path (string, Path, DataResult, or OperationResult)
        dst: Destination path (string, Path, DataResult, or OperationResult)
        overwrite: If True, overwrite destination if it exists

    Returns:
        WriteResult with operation status
    """
    try:
        normalized_src = _normalize_path_param(src)
        normalized_dst = _normalize_path_param(dst)
        result_path = _safe_copy(normalized_src, normalized_dst, overwrite)

        # Get size if it's a file
        bytes_copied = 0
        if result_path.is_file():
            bytes_copied = result_path.stat().st_size

        return WriteResult(
            success=True,
            path=result_path,
            original_path=normalized_src,
            bytes_written=bytes_copied,
            message=f"Successfully copied {normalized_src} to {normalized_dst}",
        )
    except Exception as e:
        logger.error(f"Failed to copy {src} to {dst}: {e}")
        normalized_src = _normalize_path_param(src)
        normalized_dst = _normalize_path_param(dst)
        return WriteResult(
            success=False,
            path=normalized_dst,
            original_path=normalized_src,
            error=str(e),
            message="Failed to copy file or directory",
        )


def move_safely(
        src: str | Path | DataResult | OperationResult,
        dst: str | Path | DataResult | OperationResult, overwrite: bool = False
) -> WriteResult:
    """
    Safely move a file or directory.

    Args:
        src: Source path (string, Path, DataResult, or OperationResult)
        dst: Destination path (string, Path, DataResult, or OperationResult)
        overwrite: If True, overwrite destination if it exists

    Returns:
        WriteResult with operation status
    """
    try:
        normalized_src = _normalize_path_param(src)
        normalized_dst = _normalize_path_param(dst)

        # Get size before moving if it's a file
        bytes_moved = 0
        if normalized_src.is_file():
            bytes_moved = normalized_src.stat().st_size

        result_path = _safe_move(normalized_src, normalized_dst, overwrite)

        return WriteResult(
            success=True,
            path=result_path,
            original_path=normalized_src,
            bytes_written=bytes_moved,
            message=f"Successfully moved {normalized_src} to {normalized_dst}",
        )
    except Exception as e:
        logger.error(f"Failed to move {src} to {dst}: {e}")
        normalized_src = _normalize_path_param(src)
        normalized_dst = _normalize_path_param(dst)
        return WriteResult(
            success=False,
            path=normalized_dst,
            original_path=normalized_src,
            error=str(e),
            message="Failed to move file or directory",
        )


def delete_safely(path: str | Path | DataResult | OperationResult,
                  missing_ok: bool = True) -> OperationResult:
    """
    Safely delete a file or directory.

    Args:
        path: Path to delete (string, Path, DataResult, or OperationResult)
        missing_ok: If True, don't raise error if path doesn't exist

    Returns:
        OperationResult with operation status
    """
    try:
        normalized_path = _normalize_path_param(path)
        result = _safe_delete(normalized_path, missing_ok)

        if result:
            return OperationResult(
                success=True, path=normalized_path,
                message=f"Successfully deleted {normalized_path}"
            )
        else:
            # This branch is hit when the path doesn't exist and missing_ok is True
            return OperationResult(
                success=True,
                path=normalized_path,
                message=f"Path {normalized_path} does not exist, no action taken",
            )
    except Exception as e:
        logger.error(f"Failed to delete {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return OperationResult(
            success=False,
            path=normalized_path,
            error=str(e),
            message="Failed to delete file or directory",
        )
