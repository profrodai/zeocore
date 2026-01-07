# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/file_info.py
# module: quack_core.core.fs.api.public.file_info
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_ops.py, path_ops.py (+3 more)
# exports: get_file_type, get_file_size_str, get_file_timestamp, get_mime_type, is_file_locked
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs._helpers.file_info import (
    _get_file_size_str,
    _get_file_timestamp,
    _get_file_type,
    _get_mime_type,
    _is_file_locked,
)
from quack_core.core.fs.api.public.coerce import coerce_path, coerce_path_result
from quack_core.core.fs.results import DataResult
from quack_core.core.logging import get_logger

logger = get_logger(__name__)

def get_file_type(path: Any) -> DataResult[str]:
    try:
        normalized_path = coerce_path(path)
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
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data="unknown",
            format="file_type",
            error=str(e),
            message="Failed to determine file type",
        )

def get_file_size_str(size_bytes: int) -> DataResult[str]:
    try:
        size_str = _get_file_size_str(size_bytes)
        return DataResult(
            success=True,
            path=None,
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

def get_file_timestamp(path: Any) -> DataResult[float]:
    try:
        normalized_path = coerce_path(path)
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
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data=0.0,
            format="timestamp",
            error=str(e),
            message="Failed to get file timestamp",
        )

def get_mime_type(path: Any) -> DataResult[str | None]:
    try:
        normalized_path = coerce_path(path)
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
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data=None,
            format="mime_type",
            error=str(e),
            message="Failed to determine MIME type",
        )

def is_file_locked(path: Any) -> DataResult[bool]:
    try:
        normalized_path = coerce_path(path)
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
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data=False,
            format="boolean",
            error=str(e),
            message="Failed to check if file is locked",
        )