# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/file_operations.py
# module: quack_core.core.fs.service.file_operations
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_info_operations.py, full_class.py (+5 more)
# exports: FileOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 2d6aea0e
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
            return ReadResult(ok=True, path=norm_path, content=content, encoding=encoding, message=f"Read {len(content)} chars")
        except Exception as e:
            s = safe_path_str(path)
            return ReadResult(
                ok=False,
                path=None,
                content=None,
                encoding=encoding,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read file",
                meta={"input_path": s} if s else None
            )

    def write_text(self, path: FsPathLike, content: str, encoding: str = "utf-8", atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
        try:
            norm_path = self._normalize_input_path(path)
            result_path = self.operations._write_text(norm_path, content, encoding, atomic)
            bytes_written = len(content.encode(encoding))
            checksum = None
            if calculate_checksum:
                checksum = self.operations._compute_checksum(result_path, "sha256")
            return WriteResult(ok=True, path=result_path, bytes_written=bytes_written, checksum=checksum, message=f"Wrote {bytes_written} bytes")
        except Exception as e:
            s = safe_path_str(path)
            return WriteResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write file",
                meta={"input_path": s} if s else None
            )

    def read_bytes(self, path: FsPathLike) -> ReadResult[bytes]:
        try:
            norm_path = self._normalize_input_path(path)
            content = self.operations._read_binary(norm_path)
            return ReadResult(ok=True, path=norm_path, content=content, encoding=None, message=f"Read {len(content)} bytes")
        except Exception as e:
            s = safe_path_str(path)
            return ReadResult(
                ok=False,
                path=None,
                content=None,
                encoding=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read binary file",
                meta={"input_path": s} if s else None
            )

    def write_bytes(self, path: FsPathLike, content: bytes, atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
        try:
            norm_path = self._normalize_input_path(path)
            result_path = self.operations._write_binary(norm_path, content, atomic)
            bytes_written = len(content)
            checksum = None
            if calculate_checksum:
                checksum = self.operations._compute_checksum(result_path, "sha256")
            return WriteResult(ok=True, path=result_path, bytes_written=bytes_written, checksum=checksum, message=f"Wrote {bytes_written} bytes")
        except Exception as e:
            s = safe_path_str(path)
            return WriteResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write binary file",
                meta={"input_path": s} if s else None
            )

    def read_lines(self, path: FsPathLike, encoding: str = "utf-8") -> ReadResult[list[str]]:
        try:
            norm_path = self._normalize_input_path(path)
            content_str = self.operations._read_text(norm_path, encoding)
            lines = content_str.splitlines()
            return ReadResult(ok=True, path=norm_path, content=lines, encoding=encoding, message=f"Read {len(lines)} lines")
        except Exception as e:
            s = safe_path_str(path)
            return ReadResult(
                ok=False,
                path=None,
                content=None,
                encoding=encoding,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read lines",
                meta={"input_path": s} if s else None
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
            return WriteResult(ok=True, path=result_path, bytes_written=size, message=f"Wrote {len(lines)} lines")
        except Exception as e:
            s = safe_path_str(path)
            return WriteResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write lines",
                meta={"input_path": s} if s else None
            )

    def copy(self, src: FsPathLike, dst: FsPathLike, overwrite: bool = False) -> WriteResult:
        try:
            norm_src = self._normalize_input_path(src)
            norm_dst = self._normalize_input_path(dst)
            result_path = self.operations._copy(norm_src, norm_dst, overwrite)
            size = 0
            if result_path.is_file():
                size = result_path.stat().st_size
            return WriteResult(ok=True, path=result_path, original_path=norm_src, bytes_written=size, message=f"Copied to {result_path}")
        except Exception as e:
            # For copy/move, return None for path since we may have failed before normalizing both paths
            src_str = safe_path_str(src)
            dst_str = safe_path_str(dst)
            return WriteResult(
                ok=False,
                path=None,
                original_path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Copy failed",
                meta={"input_src": src_str, "input_dst": dst_str} if (src_str or dst_str) else None
            )

    def move(self, src: FsPathLike, dst: FsPathLike, overwrite: bool = False) -> WriteResult:
        try:
            norm_src = self._normalize_input_path(src)
            norm_dst = self._normalize_input_path(dst)
            result_path = self.operations._move(norm_src, norm_dst, overwrite)
            return WriteResult(ok=True, path=result_path, original_path=norm_src, message=f"Moved to {result_path}")
        except Exception as e:
            src_str = safe_path_str(src)
            dst_str = safe_path_str(dst)
            return WriteResult(
                ok=False,
                path=None,
                original_path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Move failed",
                meta={"input_src": src_str, "input_dst": dst_str} if (src_str or dst_str) else None
            )

    def delete(self, path: FsPathLike, missing_ok: bool = True) -> OperationResult:
        try:
            norm_path = self._normalize_input_path(path)
            deleted = self.operations._delete(norm_path, missing_ok)
            return OperationResult(ok=True, path=norm_path, message="Deleted" if deleted else "Not found (ignored)")
        except Exception as e:
            s = safe_path_str(path)
            return OperationResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Delete failed",
                meta={"input_path": s} if s else None
            )