# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/file_operations.py
# module: quack_core.core.fs.service.file_operations
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, full_class.py, path_operations.py (+4 more)
# exports: FileOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

from pathlib import Path
from typing import Any
from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.results import ReadResult, WriteResult, OperationResult, ErrorInfo
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.normalize import safe_path_str

class FileOperationsMixin:
    operations: FileSystemOperations
    logger: Any
    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError
    def _map_error(self, e: Exception) -> ErrorInfo: raise NotImplementedError

    def read_text(self, path: FsPathLike, encoding: str = "utf-8") -> ReadResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            content = self.operations._read_text(norm_path, encoding)
            return ReadResult(success=True, path=norm_path, content=content, encoding=encoding, message=f"Read {len(content)} chars")
        except Exception as e:
            # No logging on expected errors, let caller handle via result.success
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return ReadResult(
                success=False,
                path=safe_p,
                content=None,
                encoding=encoding,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read file"
            )

    def write_text(self, path: FsPathLike, content: str, encoding: str = "utf-8", atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
        try:
            norm_path = self._normalize_input_path(path)
            result_path = self.operations._write_text(norm_path, content, encoding, atomic)
            bytes_written = len(content.encode(encoding))
            checksum = None
            if calculate_checksum:
                checksum = self.operations._compute_checksum(result_path, "sha256")
            return WriteResult(success=True, path=result_path, bytes_written=bytes_written, checksum=checksum, message=f"Wrote {bytes_written} bytes")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return WriteResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write file"
            )

    def read_bytes(self, path: FsPathLike) -> ReadResult[bytes]:
        try:
            norm_path = self._normalize_input_path(path)
            content = self.operations._read_binary(norm_path)
            return ReadResult(success=True, path=norm_path, content=content, encoding=None, message=f"Read {len(content)} bytes")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return ReadResult(
                success=False,
                path=safe_p,
                content=None,
                encoding=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read binary file"
            )

    # Renamed from write_binary for consistency
    def write_bytes(self, path: FsPathLike, content: bytes, atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
        try:
            norm_path = self._normalize_input_path(path)
            result_path = self.operations._write_binary(norm_path, content, atomic)
            bytes_written = len(content)
            checksum = None
            if calculate_checksum:
                checksum = self.operations._compute_checksum(result_path, "sha256")
            return WriteResult(success=True, path=result_path, bytes_written=bytes_written, checksum=checksum, message=f"Wrote {bytes_written} bytes")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return WriteResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write binary file"
            )

    def read_lines(self, path: FsPathLike, encoding: str = "utf-8") -> ReadResult[list[str]]:
        try:
            norm_path = self._normalize_input_path(path)
            content_str = self.operations._read_text(norm_path, encoding)
            lines = content_str.splitlines()
            return ReadResult(success=True, path=norm_path, content=lines, encoding=encoding, message=f"Read {len(lines)} lines")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return ReadResult(
                success=False,
                path=safe_p,
                content=None,
                encoding=encoding,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read lines"
            )

    def write_lines(self, path: FsPathLike, lines: list[str], encoding: str = "utf-8", atomic: bool = True, line_ending: str = "\n") -> WriteResult:
        try:
            norm_path = self._normalize_input_path(path)
            content = line_ending.join(lines)
            if line_ending != "\n":
                b_content = content.encode(encoding)
                result_path = self.operations._write_binary(norm_path, b_content, atomic)
                size = len(b_content)
            else:
                result_path = self.operations._write_text(norm_path, content, encoding, atomic)
                size = len(content.encode(encoding))
            return WriteResult(success=True, path=result_path, bytes_written=size, message=f"Wrote {len(lines)} lines")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return WriteResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write lines"
            )

    def copy(self, src: FsPathLike, dst: FsPathLike, overwrite: bool = False) -> WriteResult:
        try:
            norm_src = self._normalize_input_path(src)
            norm_dst = self._normalize_input_path(dst)
            result_path = self.operations._copy(norm_src, norm_dst, overwrite)
            size = 0
            if result_path.is_file():
                size = result_path.stat().st_size
            return WriteResult(success=True, path=result_path, original_path=norm_src, bytes_written=size, message=f"Copied to {result_path}")
        except Exception as e:
            safe_src_str = safe_path_str(src)
            safe_dst_str = safe_path_str(dst)
            safe_dst = Path(safe_dst_str) if safe_dst_str else None
            safe_src = Path(safe_src_str) if safe_src_str else None
            return WriteResult(
                success=False,
                path=safe_dst,
                original_path=safe_src,
                error_info=self._map_error(e),
                error=str(e),
                message="Copy failed"
            )

    def move(self, src: FsPathLike, dst: FsPathLike, overwrite: bool = False) -> WriteResult:
        try:
            norm_src = self._normalize_input_path(src)
            norm_dst = self._normalize_input_path(dst)
            result_path = self.operations._move(norm_src, norm_dst, overwrite)
            return WriteResult(success=True, path=result_path, original_path=norm_src, message=f"Moved to {result_path}")
        except Exception as e:
            safe_src_str = safe_path_str(src)
            safe_dst_str = safe_path_str(dst)
            safe_dst = Path(safe_dst_str) if safe_dst_str else None
            safe_src = Path(safe_src_str) if safe_src_str else None
            return WriteResult(
                success=False,
                path=safe_dst,
                original_path=safe_src,
                error_info=self._map_error(e),
                error=str(e),
                message="Move failed"
            )

    def delete(self, path: FsPathLike, missing_ok: bool = True) -> OperationResult:
        try:
            norm_path = self._normalize_input_path(path)
            deleted = self.operations._delete(norm_path, missing_ok)
            return OperationResult(success=True, path=norm_path, message="Deleted" if deleted else "Not found (ignored)")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return OperationResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Delete failed"
            )