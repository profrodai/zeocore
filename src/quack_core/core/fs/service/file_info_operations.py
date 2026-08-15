# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/file_info_operations.py
# module: quack_core.core.fs.service.file_info_operations
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+5 more)
# exports: FileInfoOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: f4879df3
# === QV-LLM:END ===

from pathlib import Path
from typing import Any

from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.normalize import safe_path_str
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.results import ErrorInfo, FileInfoResult


class FileInfoOperationsMixin:
    operations: FileSystemOperations
    logger: Any
    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError
    def _map_error(self, e: Exception) -> ErrorInfo: raise NotImplementedError

    def get_file_info(self, path: FsPathLike) -> FileInfoResult:
        try:
            normalized_path = self._normalize_input_path(path)
            # Returns _FileInfo (internal DTO)
            file_info = self.operations._get_file_info(normalized_path)
            if not file_info.exists:
                return FileInfoResult(ok=True, path=normalized_path, exists=False, message="Path does not exist")

            return FileInfoResult(
                ok=True,
                path=normalized_path,
                exists=file_info.exists,
                is_file=file_info.is_file,
                is_dir=file_info.is_dir,
                size=file_info.size,
                modified=file_info.modified,
                created=file_info.created,
                modified_iso=file_info.modified_iso,
                created_iso=file_info.created_iso,
                owner=file_info.owner,
                permissions=file_info.permissions,
                mime_type=file_info.mime_type,
                message=f"FileInfo: {normalized_path}"
            )
        except Exception as e:
            s = safe_path_str(path)
            return FileInfoResult(
                ok=False,
                path=None,
                exists=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get info",
                meta={"input_path": s} if s else None
            )
