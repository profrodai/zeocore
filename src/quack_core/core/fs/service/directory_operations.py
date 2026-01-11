# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/directory_operations.py
# module: quack_core.core.fs.service.directory_operations
# role: service
# neighbors: __init__.py, base.py, factory.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: DirectoryOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
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
            result_path = self.operations._ensure_directory(normalized_path, exist_ok)
            return OperationResult(success=True, path=result_path, message=f"Directory created: {result_path}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return OperationResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to create directory"
            )

    def get_file_info(self, path: FsPathLike) -> FileInfoResult:
        try:
            normalized_path = self._normalize_input_path(path)
            file_info = self.operations._get_file_info(normalized_path)
            if not file_info.exists:
                return FileInfoResult(success=True, path=normalized_path, exists=False, message="Path does not exist")

            return FileInfoResult(
                success=True,
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
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return FileInfoResult(
                success=False,
                path=safe_p,
                exists=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get info"
            )

    def list_directory(self, path: FsPathLike, pattern: str | None = None, include_hidden: bool = False) -> DirectoryInfoResult:
        try:
            normalized_path = self._normalize_input_path(path)
            dir_info = self.operations._list_directory(normalized_path, pattern, include_hidden)
            return DirectoryInfoResult(
                success=True,
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
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DirectoryInfoResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to list directory"
            )

    def find_files(self, path: FsPathLike, pattern: str, recursive: bool = True, include_hidden: bool = False) -> FindResult:
        try:
            normalized_path = self._normalize_input_path(path)
            files, directories = self.operations._find_files(normalized_path, pattern, recursive, include_hidden)
            return FindResult(
                success=True,
                path=normalized_path,
                files=files,
                directories=directories,
                total_matches=len(files) + len(directories),
                pattern=pattern,
                recursive=recursive,
                message=f"Found {len(files)} files"
            )
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return FindResult(
                success=False,
                path=safe_p,
                pattern=pattern,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to find files"
            )