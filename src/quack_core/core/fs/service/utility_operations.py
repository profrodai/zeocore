from pathlib import Path
from typing import Any
from quack_core.fs.operations.base import FileSystemOperations
from quack_core.fs.results import DataResult, OperationResult, WriteResult, ErrorInfo
from quack_core.fs.protocols import FsPathLike
from quack_core.fs.normalize import safe_path_str

class UtilityOperationsMixin:
    operations: FileSystemOperations
    logger: Any
    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError
    def _map_error(self, e: Exception) -> ErrorInfo: raise NotImplementedError

    def ensure_directory(self, path: FsPathLike, exist_ok: bool = True) -> OperationResult:
        try:
            norm_path = self._normalize_input_path(path)
            res_path = self.operations._ensure_directory(norm_path, exist_ok)
            return OperationResult(success=True, path=res_path, message=f"Directory ensured: {res_path}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return OperationResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to ensure directory"
            )

    def get_unique_filename(self, directory: FsPathLike, filename: str) -> DataResult[str]:
        try:
            norm_dir = self._normalize_input_path(directory)
            unique = self.operations._get_unique_filename(norm_dir, filename)
            # path is the directory context, data is the result filename
            return DataResult(success=True, path=norm_dir, data=str(unique.name), format="filename", message=f"Unique filename: {unique.name}")
        except Exception as e:
            safe_p_str = safe_path_str(directory)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data="",
                format="filename",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to generate filename"
            )

    def create_temp_file(self, suffix: str = ".txt", prefix: str = "quackcore_", directory: FsPathLike | None = None) -> DataResult[str]:
        try:
            norm_dir = self._normalize_input_path(directory) if directory else None
            temp_path = self.operations._create_temp_file(suffix, prefix, norm_dir)
            return DataResult(success=True, path=temp_path, data=str(temp_path), format="path", message=f"Created temp file: {temp_path}")
        except Exception as e:
            safe_p_str = safe_path_str(directory) if directory else None
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data="",
                format="path",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to create temp file"
            )

    def find_files_by_content(self, directory: FsPathLike, text_pattern: str, recursive: bool = True) -> DataResult[list[str]]:
        try:
            norm_dir = self._normalize_input_path(directory)
            matches = self.operations._find_files_by_content(norm_dir, text_pattern, recursive)
            return DataResult(success=True, path=norm_dir, data=[str(p) for p in matches], format="path_list", message=f"Found {len(matches)} files")
        except Exception as e:
            safe_p_str = safe_path_str(directory)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data=[],
                format="path_list",
                error_info=self._map_error(e),
                error=str(e),
                message="Search failed"
            )

    def get_disk_usage(self, path: FsPathLike) -> DataResult[dict[str, int]]:
        try:
            norm_path = self._normalize_input_path(path)
            usage = self.operations._get_disk_usage(norm_path)
            return DataResult(success=True, path=norm_path, data=usage, format="disk_usage", message="Retrieved disk usage")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data={},
                format="disk_usage",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get disk usage"
            )

    def get_file_type(self, path: FsPathLike) -> DataResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            ftype = self.operations._get_file_type(norm_path)
            return DataResult(success=True, path=norm_path, data=ftype, format="file_type", message=f"File type: {ftype}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data="",
                format="file_type",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get file type"
            )

    def get_file_size_str(self, size_bytes: int) -> DataResult[str]:
        try:
            s = self.operations._get_file_size_str(size_bytes)
            return DataResult(success=True, path=None, data=s, format="size_string", message="Formatted size")
        except Exception as e:
            return DataResult(
                success=False,
                path=None,
                data="",
                format="size_string",
                error_info=self._map_error(e),
                error=str(e),
                message="Formatting failed"
            )

    def get_mime_type(self, path: FsPathLike) -> DataResult[str | None]:
        try:
            norm_path = self._normalize_input_path(path)
            mime = self.operations._get_mime_type(norm_path)
            return DataResult(success=True, path=norm_path, data=mime, format="mime_type", message=f"Mime type: {mime}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data=None,
                format="mime_type",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get mime type"
            )

    def get_file_timestamp(self, path: FsPathLike) -> DataResult[float]:
        try:
            norm_path = self._normalize_input_path(path)
            ts = self.operations._get_file_timestamp(norm_path)
            return DataResult(success=True, path=norm_path, data=ts, format="timestamp", message="Retrieved timestamp")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data=0.0,
                format="timestamp",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get timestamp"
            )

    def compute_checksum(self, path: FsPathLike, algorithm: str = "sha256") -> DataResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            cs = self.operations._compute_checksum(norm_path, algorithm)
            return DataResult(success=True, path=norm_path, data=cs, format="checksum", message="Computed checksum")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data="",
                format="checksum",
                error_info=self._map_error(e),
                error=str(e),
                message="Checksum failed"
            )

    def is_path_writeable(self, path: FsPathLike) -> DataResult[bool]:
        try:
            norm_path = self._normalize_input_path(path)
            w = self.operations._is_path_writeable(norm_path)
            return DataResult(success=True, path=norm_path, data=w, format="boolean", message=f"Writeable: {w}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data=False,
                format="boolean",
                error_info=self._map_error(e),
                error=str(e),
                message="Check failed"
            )

    def is_file_locked(self, path: FsPathLike) -> DataResult[bool]:
        try:
            norm_path = self._normalize_input_path(path)
            l = self.operations._is_file_locked(norm_path)
            return DataResult(success=True, path=norm_path, data=l, format="boolean", message=f"Locked: {l}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data=False,
                format="boolean",
                error_info=self._map_error(e),
                error=str(e),
                message="Lock check failed"
            )

    def atomic_write(self, path: FsPathLike, content: str | bytes) -> WriteResult:
        try:
            norm_path = self._normalize_input_path(path)
            if isinstance(content, str):
                result_path = self.operations._write_text(norm_path, content, atomic=True)
                size = len(content.encode('utf-8'))
            else:
                result_path = self.operations._write_binary(norm_path, content, atomic=True)
                size = len(content)
            return WriteResult(success=True, path=result_path, bytes_written=size, message="Atomic write successful")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return WriteResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Atomic write failed"
            )