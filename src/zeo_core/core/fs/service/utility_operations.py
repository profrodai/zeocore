from pathlib import Path
from typing import Any

from zeo_core.core.fs._ops.base import FileSystemOperations
from zeo_core.core.fs.normalize import safe_path_str
from zeo_core.core.fs.protocols import FsPathLike
from zeo_core.core.fs.results import (
    DataResult,
    ErrorInfo,
    WriteResult,
)


class UtilityOperationsMixin:
    """
    Mixin providing utility operations for FileSystemService.
    This is a MIXIN CLASS used in service composition, NOT wrapper functions.
    """

    operations: FileSystemOperations
    logger: Any
    base_dir: Path  # Type hint from the main class

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        raise NotImplementedError

    def _map_error(self, e: Exception) -> ErrorInfo:
        raise NotImplementedError

    def get_unique_filename(
        self, directory: FsPathLike, filename: str
    ) -> DataResult[str]:
        try:
            norm_dir = self._normalize_input_path(directory)
            unique = self.operations._get_unique_filename(norm_dir, filename)
            return DataResult(
                ok=True,
                path=norm_dir,
                data=str(unique.name),
                format="filename",
                message=f"Unique filename: {unique.name}",
            )
        except Exception as e:
            s = safe_path_str(directory)
            return DataResult(
                ok=False,
                path=None,
                data="",
                format="filename",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to generate filename",
                meta={"input_path": s} if s else None,
            )

    def create_temp_file(
        self,
        suffix: str = ".txt",
        prefix: str = "zeocore_",
        directory: FsPathLike | None = None,
    ) -> DataResult[str]:
        try:
            if directory:
                norm_dir = self._normalize_input_path(directory)
            else:
                # Doctrine: Default to .zeo/tmp inside base_dir to ensure sandboxing
                norm_dir = self.base_dir / ".zeo" / "tmp"
                if not norm_dir.exists():
                    self.operations._ensure_directory(norm_dir)

            temp_path = self.operations._create_temp_file(suffix, prefix, norm_dir)
            return DataResult(
                ok=True,
                path=temp_path,
                data=str(temp_path),
                format="path",
                message=f"Created temp file: {temp_path}",
            )
        except Exception as e:
            s = safe_path_str(directory) if directory else None
            return DataResult(
                ok=False,
                path=None,
                data="",
                format="path",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to create temp file",
                meta={"input_path": s} if s else None,
            )

    def create_temp_directory(
        self,
        prefix: str = "zeocore_",
        suffix: str = "",
        directory: FsPathLike | None = None,
    ) -> DataResult[str]:
        """
        Creates a temporary directory.
        Defaults to .zeo/tmp within the service base_dir to ensure sandboxing.
        """
        try:
            if directory:
                norm_dir = self._normalize_input_path(directory)
            else:
                # Doctrine: Default to .zeo/tmp inside base_dir to ensure sandboxing
                norm_dir = self.base_dir / ".zeo" / "tmp"
                if not norm_dir.exists():
                    self.operations._ensure_directory(norm_dir)

            temp_dir = self.operations._create_temp_directory(prefix, suffix, norm_dir)
            return DataResult(
                ok=True,
                path=temp_dir,
                data=str(temp_dir),
                format="path",
                message=f"Created temp dir: {temp_dir}",
            )
        except Exception as e:
            s = safe_path_str(directory) if directory else None
            return DataResult(
                ok=False,
                path=None,
                data="",
                format="path",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to create temp directory",
                meta={"input_path": s} if s else None,
            )

    def find_files_by_content(
        self, directory: FsPathLike, text_pattern: str, recursive: bool = True
    ) -> DataResult[list[str]]:
        try:
            norm_dir = self._normalize_input_path(directory)
            matches = self.operations._find_files_by_content(
                norm_dir, text_pattern, recursive
            )
            return DataResult(
                ok=True,
                path=norm_dir,
                data=[str(p) for p in matches],
                format="path_list",
                message=f"Found {len(matches)} files",
            )
        except Exception as e:
            s = safe_path_str(directory)
            return DataResult(
                ok=False,
                path=None,
                data=[],
                format="path_list",
                error_info=self._map_error(e),
                error=str(e),
                message="Search failed",
                meta={"input_path": s} if s else None,
            )

    def get_disk_usage(self, path: FsPathLike) -> DataResult[dict[str, int]]:
        try:
            norm_path = self._normalize_input_path(path)
            usage = self.operations._get_disk_usage(norm_path)
            return DataResult(
                ok=True,
                path=norm_path,
                data=usage,
                format="disk_usage",
                message="Retrieved disk usage",
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data={},
                format="disk_usage",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get disk usage",
                meta={"input_path": s} if s else None,
            )

    def get_file_type(self, path: FsPathLike) -> DataResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            ftype = self.operations._get_file_type(norm_path)
            return DataResult(
                ok=True,
                path=norm_path,
                data=ftype,
                format="file_type",
                message=f"File type: {ftype}",
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data="",
                format="file_type",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get file type",
                meta={"input_path": s} if s else None,
            )

    def get_file_size_str(self, size_bytes: int) -> DataResult[str]:
        try:
            s = self.operations._get_file_size_str(size_bytes)
            return DataResult(
                ok=True,
                path=None,
                data=s,
                format="size_string",
                message="Formatted size",
            )
        except Exception as e:
            return DataResult(
                ok=False,
                path=None,
                data="",
                format="size_string",
                error_info=self._map_error(e),
                error=str(e),
                message="Formatting failed",
            )

    def get_mime_type(self, path: FsPathLike) -> DataResult[str | None]:
        try:
            norm_path = self._normalize_input_path(path)
            mime = self.operations._get_mime_type(norm_path)
            return DataResult(
                ok=True,
                path=norm_path,
                data=mime,
                format="mime_type",
                message=f"Mime type: {mime}",
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data=None,
                format="mime_type",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get mime type",
                meta={"input_path": s} if s else None,
            )

    def get_file_timestamp(self, path: FsPathLike) -> DataResult[float]:
        try:
            norm_path = self._normalize_input_path(path)
            ts = self.operations._get_file_timestamp(norm_path)
            return DataResult(
                ok=True,
                path=norm_path,
                data=ts,
                format="timestamp",
                message="Retrieved timestamp",
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data=0.0,
                format="timestamp",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to get timestamp",
                meta={"input_path": s} if s else None,
            )

    def compute_checksum(
        self, path: FsPathLike, algorithm: str = "sha256"
    ) -> DataResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            cs = self.operations._compute_checksum(norm_path, algorithm)
            return DataResult(
                ok=True,
                path=norm_path,
                data=cs,
                format="checksum",
                message="Computed checksum",
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data="",
                format="checksum",
                error_info=self._map_error(e),
                error=str(e),
                message="Checksum failed",
                meta={"input_path": s} if s else None,
            )

    def is_path_writeable(self, path: FsPathLike) -> DataResult[bool]:
        """
        Checks if the path is writeable.
        WARNING: This method performs a write probe (side effect) if the path
        does not exist.
        """
        try:
            norm_path = self._normalize_input_path(path)
            w = self.operations._is_path_writeable(norm_path)
            return DataResult(
                ok=True,
                path=norm_path,
                data=w,
                format="boolean",
                message=f"Writeable: {w}",
                meta={"side_effect": "write_probe"},
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data=False,
                format="boolean",
                error_info=self._map_error(e),
                error=str(e),
                message="Check failed",
                meta={"side_effect": "write_probe", "input_path": s}
                if s
                else {"side_effect": "write_probe"},
            )

    def is_file_locked(self, path: FsPathLike) -> DataResult[bool]:
        try:
            norm_path = self._normalize_input_path(path)
            is_locked = self.operations._is_file_locked(norm_path)
            return DataResult(
                ok=True,
                path=norm_path,
                data=is_locked,
                format="boolean",
                message=f"Locked: {is_locked}",
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data=False,
                format="boolean",
                error_info=self._map_error(e),
                error=str(e),
                message="Lock check failed",
                meta={"input_path": s} if s else None,
            )

    def atomic_write(self, path: FsPathLike, content: str | bytes) -> WriteResult:
        try:
            norm_path = self._normalize_input_path(path)
            if isinstance(content, str):
                result_path = self.operations._write_text(
                    norm_path, content, atomic=True
                )
                size = len(content.encode("utf-8"))
            else:
                result_path = self.operations._write_binary(
                    norm_path, content, atomic=True
                )
                size = len(content)
            return WriteResult(
                ok=True,
                path=result_path,
                bytes_written=size,
                message="Atomic write successful",
            )
        except Exception as e:
            s = safe_path_str(path)
            return WriteResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Atomic write failed",
                meta={"input_path": s} if s else None,
            )
