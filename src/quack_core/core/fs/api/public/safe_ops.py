# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/safe_ops.py
# module: quack_core.core.fs.api.public.safe_ops
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, file_ops.py (+3 more)
# exports: copy_safely, move_safely, delete_safely
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs._internal.safe_ops import _safe_copy, _safe_delete, _safe_move
from quack_core.core.fs.api.public.coerce import coerce_path, coerce_path_result
from quack_core.core.fs.results import OperationResult, WriteResult
from quack_core.core.logging import get_logger

logger = get_logger(__name__)


def copy_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    try:
        normalized_src = coerce_path(src)
        normalized_dst = coerce_path(dst)
        result_path = _safe_copy(normalized_src, normalized_dst, overwrite)

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
        safe_dst = coerce_path_result(dst)
        safe_src = coerce_path_result(src)
        return WriteResult(
            success=False,
            path=safe_dst.path if safe_dst.success else None,
            original_path=safe_src.path if safe_src.success else None,
            error=str(e),
            message="Failed to copy file or directory",
        )


def move_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    try:
        normalized_src = coerce_path(src)
        normalized_dst = coerce_path(dst)

        bytes_moved = 0
        if normalized_src.exists() and normalized_src.is_file():
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
        safe_dst = coerce_path_result(dst)
        safe_src = coerce_path_result(src)
        return WriteResult(
            success=False,
            path=safe_dst.path if safe_dst.success else None,
            original_path=safe_src.path if safe_src.success else None,
            error=str(e),
            message="Failed to move file or directory",
        )


def delete_safely(path: Any, missing_ok: bool = True) -> OperationResult:
    try:
        normalized_path = coerce_path(path)
        result = _safe_delete(normalized_path, missing_ok)

        msg = f"Successfully deleted {normalized_path}" if result else f"Path {normalized_path} does not exist, no action taken"

        return OperationResult(
            success=True,
            path=normalized_path,
            message=msg
        )
    except Exception as e:
        logger.error(f"Failed to delete {path}: {e}")
        safe_p = coerce_path_result(path)
        return OperationResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            error=str(e),
            message="Failed to delete file or directory",
        )