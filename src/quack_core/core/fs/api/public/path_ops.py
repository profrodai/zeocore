# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/path_ops.py
# module: quack_core.core.fs.api.public.path_ops
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, file_ops.py (+3 more)
# exports: split_path, expand_user_vars, normalize_path, is_same_file, is_subdirectory
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from pathlib import Path
from typing import Any

from quack_core.core.fs._helpers.common import _normalize_path
from quack_core.core.fs._helpers.comparison import _is_same_file, _is_subdirectory
from quack_core.core.fs._helpers.path_ops import _expand_user_vars, _split_path
from quack_core.core.fs.api.public.coerce import coerce_path, coerce_path_result
from quack_core.core.fs.results import DataResult, PathResult
from quack_core.core.logging import get_logger

logger = get_logger(__name__)

def split_path(path: Any) -> DataResult[list[str]]:
    try:
        normalized_path = coerce_path(path)
        components = _split_path(normalized_path)
        return DataResult(
            success=True,
            path=normalized_path,
            data=components,
            format="path_components",
            message=f"Successfully split path into {len(components)} components",
        )
    except Exception as e:
        logger.error(f"Failed to split path {path}: {e}")
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data=[],
            format="path_components",
            error=str(e),
            message="Failed to split path",
        )

def expand_user_vars(path: Any) -> DataResult[str]:
    try:
        normalized_path = coerce_path(path)
        expanded_path = _expand_user_vars(normalized_path)
        return DataResult(
            success=True,
            path=normalized_path,
            data=str(expanded_path),
            format="path",
            message="Successfully expanded path variables",
        )
    except Exception as e:
        logger.error(f"Failed to expand user vars in path {path}: {e}")
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data=str(path),
            format="path",
            error=str(e),
            message="Failed to expand path variables",
        )

def normalize_path(path: Any) -> PathResult:
    try:
        normalized_input = coerce_path(path)
        normalized = _normalize_path(normalized_input)
        is_abs = normalized.is_absolute()
        exists = normalized.exists()

        return PathResult(
            success=True,
            path=normalized,
            is_absolute=is_abs,
            is_valid=True,
            exists=exists,
            message="Successfully normalized path",
        )
    except Exception as e:
        logger.error(f"Failed to normalize path {path}: {e}")
        safe_p = coerce_path_result(path)
        return PathResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            is_absolute=False,
            is_valid=False,
            exists=False,
            error=str(e),
            message="Failed to normalize path",
        )

def is_same_file(path1: Any, path2: Any) -> DataResult[bool]:
    try:
        p1 = coerce_path(path1)
        p2 = coerce_path(path2)
        result = _is_same_file(p1, p2)

        return DataResult(
            success=True,
            path=p1, # Use path1 as the primary path
            data=result,
            format="boolean",
            message=f"Paths refer to {'the same' if result else 'different'} files",
        )
    except Exception as e:
        logger.error(f"Failed to check same file for {path1}, {path2}: {e}")
        safe_p = coerce_path_result(path1)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data=False,
            format="boolean",
            error=str(e),
            message="Failed to check if paths refer to the same file",
        )

def is_subdirectory(child: Any, parent: Any) -> DataResult[bool]:
    try:
        c = coerce_path(child)
        p = coerce_path(parent)
        result = _is_subdirectory(c, p)

        return DataResult(
            success=True,
            path=c,
            data=result,
            format="boolean",
            message=f"Path {'is' if result else 'is not'} a subdirectory",
        )
    except Exception as e:
        logger.error(f"Failed to check subdirectory {child} in {parent}: {e}")
        safe_p = coerce_path_result(child)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data=False,
            format="boolean",
            error=str(e),
            message="Failed to check subdirectory relationship",
        )