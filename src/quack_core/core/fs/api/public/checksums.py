# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/checksums.py
# module: quack_core.core.fs.api.public.checksums
# role: api
# neighbors: __init__.py, coerce.py, disk.py, file_info.py, file_ops.py, path_ops.py (+3 more)
# exports: compute_checksum
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from pathlib import Path
from typing import Any

from quack_core.core.fs._helpers.checksums import _compute_checksum
from quack_core.core.fs._helpers.path_utils import _normalize_path_param
from quack_core.core.fs.api.public.coerce import coerce_path_result
from quack_core.core.fs.results import DataResult, OperationResult
from quack_core.core.logging import get_logger

logger = get_logger(__name__)

def compute_checksum(path: Any, algorithm: str = "sha256") -> DataResult[str]:
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
        # FIX: Use safe coercion here to prevent crashing during error reporting
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data="",
            format="checksum",
            error=str(e),
            message=f"Failed to compute {algorithm} checksum",
        )