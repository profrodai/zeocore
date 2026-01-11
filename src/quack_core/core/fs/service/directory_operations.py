# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/directory_operations.py
# module: quack_core.core.fs.service.directory_operations
# role: service
# neighbors: __init__.py, base.py, factory.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: DirectoryOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

from pathlib import Path
from typing import Any
from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.results import DirectoryInfoResult, FindResult, OperationResult, FileInfoResult, ErrorInfo
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.normalize import safe_path_str

class DirectoryOperationsMixin:
    operations: FileSystemOperations
    logger: Any
    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError
    def _map_error(self, e: Exception) -> ErrorInfo: raise NotImplementedError

    def create_directory(self, path: FsPathLike, exist_ok: bool = True) -> OperationResult:
        try:
            normalized_path = self._normalize_input_path(path)
            # normalized_path is already absolute/anchored
            result_path = self.operations._ensure_directory(normalized_path, exist_ok)
            return OperationResult(success=True, path=result_path, message=f"Directory created: {result_path}")
        except Exception as e:
            # No logging on expected errors
            safe_p = Path(safe_path_str(path) or "")
            return OperationResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to create directory"
            )