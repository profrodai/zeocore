# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/directory_operations.py
# module: quack_core.core.fs.service.directory_operations
# role: service
# neighbors: __init__.py, base.py, factory.py, file_info_operations.py, file_operations.py, full_class.py (+5 more)
# exports: DirectoryOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 2d6aea0e
# === QV-LLM:END ===

from pathlib import Path
from typing import Any
from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.results import DirectoryInfoResult, FindResult, OperationResult, ErrorInfo
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.normalize import safe_path_str

class DirectoryOperationsMixin:
    operations: FileSystemOperations
    logger: Any
    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError
    def _map_error(self, e: Exception) -> ErrorInfo: raise NotImplementedError

    def ensure_directory(self, path: FsPathLike, exist_ok: bool = True) -> OperationResult:
        """
        Ensures a directory exists, creating it if necessary.
        """
        try:
            norm_path = self._normalize_input_path(path)
            # normalized_path is already absolute/anchored
            res_path = self.operations._ensure_directory(norm_path, exist_ok)
            return OperationResult(ok=True, path=res_path, message=f"Directory ensured: {res_path}")
        except Exception as e:
            s = safe_path_str(path)
            # Return None for path on failure to prevent unsafe paths in results
            return OperationResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to ensure directory",
                meta={"input_path": s} if s else None
            )

    def create_directory(self, path: FsPathLike, exist_ok: bool = True) -> OperationResult:
        """
        Create a directory. Alias for ensure_directory, kept for backward compatibility.
        """
        return self.ensure_directory(path, exist_ok)

    def list_directory(self, path: FsPathLike, pattern: str | None = None, recursive: bool = False, include_hidden: bool = False) -> DirectoryInfoResult:
        try:
            normalized_path = self._normalize_input_path(path)
            # Returns _DirectoryInfo (internal DTO)
            dir_info = self.operations._list_directory(normalized_path, pattern, recursive, include_hidden)
            return DirectoryInfoResult(
                ok=True,
                path=normalized_path,
                exists=True,
                files=dir_info.files,
                directories=dir_info.directories,
                total_files=dir_info.total_files,
                total_directories=dir_info.total_directories,
                total_size=dir_info.total_size,
                is_empty=dir_info.is_empty,
                message=f"Listed directory: {normalized_path}"
            )
        except Exception as e:
            s = safe_path_str(path)
            return DirectoryInfoResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to list directory",
                meta={"input_path": s} if s else None
            )

    def find_files(self, path: FsPathLike, pattern: str, recursive: bool = True, include_hidden: bool = False) -> FindResult:
        try:
            normalized_path = self._normalize_input_path(path)
            files, directories = self.operations._find_files(normalized_path, pattern, recursive, include_hidden)
            return FindResult(
                ok=True,
                path=normalized_path,
                files=files,
                directories=directories,
                total_matches=len(files) + len(directories),
                pattern=pattern,
                recursive=recursive,
                message=f"Found {len(files)} files"
            )
        except Exception as e:
            s = safe_path_str(path)
            return FindResult(
                ok=False,
                path=None,
                pattern=pattern,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to find files",
                meta={"input_path": s} if s else None
            )