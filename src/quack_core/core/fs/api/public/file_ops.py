# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/file_ops.py
# module: quack_core.core.fs.api.public.file_ops
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, path_ops.py (+3 more)
# exports: atomic_write, ensure_directory, get_unique_filename
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs.api.public.coerce import coerce_path, coerce_path_result
from quack_core.core.fs._internal.file_ops import _atomic_write, _ensure_directory, \
    _get_unique_filename
from quack_core.core.fs.results import WriteResult, OperationResult, DataResult
from quack_core.core.logging import get_logger

logger = get_logger(__name__)

def atomic_write(path: Any, content: str | bytes) -> WriteResult:
    try:
        normalized_path = coerce_path(path)
        # atomic_write determines encoding based on content type
        final_path = _atomic_write(normalized_path, content)
        size = len(content) if isinstance(content, bytes) else len(content.encode('utf-8'))
        return WriteResult(
            success=True, 
            path=final_path, 
            bytes_written=size,
            message="Atomically wrote file"
        )
    except Exception as e:
        logger.error(f"atomic_write failed: {e}")
        safe_p = coerce_path_result(path)
        return WriteResult(
            success=False, 
            path=safe_p.path if safe_p.success else None, 
            error=str(e),
            message="Atomic write failed"
        )

def ensure_directory(path: Any, exist_ok: bool = True) -> OperationResult:
    try:
        normalized_path = coerce_path(path)
        existed = normalized_path.exists()
        _ensure_directory(normalized_path, exist_ok)
        msg = "Directory existed" if existed else "Directory created"
        return OperationResult(success=True, path=normalized_path, message=msg)
    except Exception as e:
        logger.error(f"ensure_directory failed: {e}")
        safe_p = coerce_path_result(path)
        return OperationResult(
            success=False, 
            path=safe_p.path if safe_p.success else None, 
            error=str(e),
            message="Failed to ensure directory"
        )

def get_unique_filename(directory: Any, filename: str) -> DataResult[str]:
    try:
        normalized_dir = coerce_path(directory)
        unique = _get_unique_filename(normalized_dir, filename)
        return DataResult(
            success=True, 
            path=normalized_dir, 
            data=unique.name, 
            format="filename",
            message=f"Generated unique filename: {unique.name}"
        )
    except Exception as e:
        logger.error(f"get_unique_filename failed: {e}")
        safe_p = coerce_path_result(directory)
        return DataResult(
            success=False, 
            path=safe_p.path if safe_p.success else None, 
            data="", 
            format="filename",
            error=str(e),
            message="Failed to generate unique filename"
        )