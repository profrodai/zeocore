# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/path_utils.py
# module: quack_core.core.fs.api.public.path_utils
# role: api
# neighbors: __init__.py, checksums.py, disk.py, file_info.py, file_ops.py, path_ops.py (+2 more)
# exports: extract_path_from_result, extract_path_str, safe_path_str
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/api/public/path_utils.py
"""
Public API for path _operations.

This module provides safe, result-oriented wrappers around low-level path _operations.
"""

from pathlib import Path
from typing import Any

from quack_core.fs._helpers.path_utils import (
    _extract_path_str,
    _normalize_path_param,
    _safe_path_str,
)
from quack_core.fs.results import DataResult, OperationResult
from quack_core.logging import get_logger

logger = get_logger(__name__)

def extract_path_from_result(
        path_or_result: str | Path | DataResult | OperationResult) -> DataResult[str]:
    """
    Extract a path string from any result object or path-like object.

    This function handles all types of result objects (PathResult, DataResult,
    OperationResult) and extracts the actual path component for use in path operations.

    Args:
        path_or_result: Any object that might contain a path (string, Path, DataResult,
                        OperationResult, PathResult, or any path-like object)

    Returns:
        DataResult with the extracted path as a string
    """
    try:
        from quack_core.fs._helpers.path_utils import (
            _extract_path_from_result as _extract_path_impl,
        )

        extracted_path = _extract_path_impl(path_or_result)
        normalized_path = _normalize_path_param(path_or_result)

        return DataResult(
            success=True,
            path=normalized_path,
            data=str(extracted_path),
            format="path",
            message="Successfully extracted path from result",
        )
    except Exception as e:
        logger.error(f"Failed to extract path from result {path_or_result}: {e}")

        # Try to get a normalized path for the error report
        try:
            normalized_path = _normalize_path_param(path_or_result)
        except:
            normalized_path = Path()

        return DataResult(
            success=False,
            path=normalized_path,
            data=str(path_or_result),
            format="path",
            error=str(e),
            message="Failed to extract path from result",
        )

def extract_path_str(obj: Any) -> str:
    """
    Extract a string path from any path-like object or result object.

    This function handles various types of objects that might be used
    as paths, including Result objects, Path objects, and strings.

    Args:
        obj: Any object that might contain or represent a path

    Returns:
        A string representation of the path

    Raises:
        TypeError: If the object cannot be converted to a path string
        ValueError: If the object is a failed Result object
    """

    return _extract_path_str(obj)

def safe_path_str(obj: Any, default: str | None = None) -> str | None:
    """
    Safely extract a string path from any object, returning a default on failure.

    This function is similar to extract_path_str, but never raises exceptions.
    Instead, it returns the default value and logs a warning when extraction fails.

    Args:
        obj: Any object that might contain or represent a path
        default: Value to return if path extraction fails

    Returns:
        The extracted path string or the default value
    """

    return _safe_path_str(obj, default)
