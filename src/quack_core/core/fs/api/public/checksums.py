# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/checksums.py
# module: quack_core.core.fs.api.public.checksums
# role: api
# neighbors: __init__.py, disk.py, file_info.py, file_ops.py, path_ops.py, path_utils.py (+2 more)
# exports: compute_checksum
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/api/public/checksums.py
"""
Public API for file checksum _operations.

This module provides safe, result-oriented wrappers around low-level checksum _operations.
"""

from pathlib import Path

from quack_core.fs._helpers.checksums import _compute_checksum
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.fs.results import DataResult, OperationResult
from quack_core.logging import get_logger

logger = get_logger(__name__)


def compute_checksum(path: str | Path | DataResult | OperationResult,
                     algorithm: str = "sha256") -> DataResult[str]:
    """
    Compute the checksum of a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)
        algorithm: Hash algorithm to use (default: "sha256")

    Returns:
        DataResult with hexadecimal checksum string
    """
    try:
        normalized_path = _normalize_path_param(path)
        checksum = _compute_checksum(normalized_path, algorithm)

        return DataResult(
            success=True,
            path=normalized_path,
            data=checksum,
            format="checksum",
            message=f"Computed {algorithm} checksum for {normalized_path}: {checksum}",
        )
    except Exception as e:
        logger.error(f"Failed to compute checksum for {path}: {e}")
        normalized_path = _normalize_path_param(path)
        return DataResult(
            success=False,
            path=normalized_path,
            data="",
            format="checksum",
            error=str(e),
            message=f"Failed to compute {algorithm} checksum",
        )
