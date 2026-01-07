# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/temp.py
# module: quack_core.core.fs.api.public.temp
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, file_ops.py (+3 more)
# exports: create_temp_directory, create_temp_file
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs._internal.temp import _create_temp_directory, _create_temp_file
from quack_core.core.fs.api.public.coerce import coerce_path, coerce_path_result
from quack_core.core.fs.results import DataResult
from quack_core.core.logging import get_logger

logger = get_logger(__name__)


def create_temp_directory(prefix: str = "quackcore_", suffix: str = "") -> DataResult[str]:
    try:
        temp_dir = _create_temp_directory(prefix, suffix)
        return DataResult(
            success=True,
            path=temp_dir,
            data=str(temp_dir),
            format="path",
            message=f"Created temporary directory: {temp_dir}",
        )
    except Exception as e:
        logger.error(f"Failed to create temporary directory: {e}")
        return DataResult(
            success=False,
            path=None,
            data="",
            format="path",
            error=str(e),
            message="Failed to create temporary directory",
        )


def create_temp_file(
        suffix: str = ".txt",
        prefix: str = "quackcore_",
        directory: Any = None,
) -> DataResult[str]:
    try:
        normalized_dir = coerce_path(directory) if directory is not None else None
        temp_file = _create_temp_file(suffix, prefix, normalized_dir)

        dir_msg = f" in directory {normalized_dir}" if normalized_dir else ""
        return DataResult(
            success=True,
            path=temp_file,
            data=str(temp_file),
            format="path",
            message=f"Created temporary file: {temp_file}{dir_msg}",
        )
    except Exception as e:
        logger.error(f"Failed to create temporary file: {e}")
        safe_p = coerce_path_result(directory) if directory else None

        return DataResult(
            success=False,
            path=safe_p.path if safe_p and safe_p.success else None,
            data="",
            format="path",
            error=str(e),
            message="Failed to create temporary file",
        )