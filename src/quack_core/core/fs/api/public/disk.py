# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/disk.py
# module: quack_core.core.fs.api.public.disk
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, file_info.py, file_ops.py, path_ops.py (+3 more)
# exports: get_disk_usage, is_path_writeable
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs._internal.disk import _get_disk_usage, _is_path_writeable
from quack_core.core.fs.api.public.coerce import coerce_path, coerce_path_result
from quack_core.core.fs.results import DataResult
from quack_core.core.logging import get_logger

logger = get_logger(__name__)

def get_disk_usage(path: Any) -> DataResult[dict[str, int]]:
    try:
        normalized_path = coerce_path(path)
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
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data={},
            format="disk_usage",
            error=str(e),
            message="Failed to get disk usage",
        )

def is_path_writeable(path: Any) -> DataResult[bool]:
    try:
        normalized_path = coerce_path(path)
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
        safe_p = coerce_path_result(path)
        return DataResult(
            success=False,
            path=safe_p.path if safe_p.success else None,
            data=False,
            format="boolean",
            error=str(e),
            message="Failed to check if path is writeable",
        )