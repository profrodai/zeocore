# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/disk.py
# module: quack_core.core.fs.api.public.disk
# role: api
# neighbors: __init__.py, checksums.py, file_info.py, file_ops.py, path_ops.py, path_utils.py (+2 more)
# exports: get_disk_usage, is_path_writeable
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/api/public/disk.py
"""
Public API for disk _operations.

This module provides safe, result-oriented wrappers around low-level disk _operations.
"""

from pathlib import Path

from quack_core.fs._helpers.disk import _get_disk_usage, _is_path_writeable
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.fs.results import DataResult, OperationResult
from quack_core.logging import get_logger

logger = get_logger(__name__)


def get_disk_usage(path: str | Path | DataResult | OperationResult) -> DataResult[
    dict[str, int]]:
    """
    Get disk usage information for the given path.

    Args:
        path: Path to get disk usage for (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with total, used, and free space in bytes
    """
    try:
        # Convert path to Path object to ensure consistent handling
        normalized_path = _normalize_path_param(path)
        usage_data = _get_disk_usage(normalized_path)

        return DataResult(
            success=True,
            path=normalized_path,
            data=usage_data,
            format="disk_usage",
            message=f"Successfully retrieved disk usage for {normalized_path}",
        )
    except Exception as e:
        logger.error(f"Failed to get disk usage for {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return DataResult(
            success=False,
            path=normalized_path,
            data={},
            format="disk_usage",
            error=str(e),
            message="Failed to get disk usage",
        )


def is_path_writeable(path: str | Path | DataResult | OperationResult) -> DataResult[
    bool]:
    """
    Check if a path is writeable.

    Args:
        path: Path to check (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with boolean indicating if path is writeable
    """
    try:
        normalized_path = _normalize_path_param(path)
        is_writeable = _is_path_writeable(normalized_path)

        return DataResult(
            success=True,
            path=normalized_path,
            data=is_writeable,
            format="boolean",
            message=f"Path {normalized_path} is {'writeable' if is_writeable else 'not writeable'}",
        )
    except Exception as e:
        logger.error(f"Failed to check if path is writeable {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return DataResult(
            success=False,
            path=normalized_path,
            data=False,
            format="boolean",
            error=str(e),
            message="Failed to check if path is writeable",
        )
