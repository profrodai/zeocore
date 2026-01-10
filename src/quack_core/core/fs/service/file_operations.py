from pathlib import Path
from typing import Any
from quack_core.core.fs.operations.base import FileSystemOperations
from quack_core.core.fs.results import ReadResult, WriteResult, OperationResult
from quack_core.core.fs.api.public.coerce import coerce_path_result
from quack_core.core.fs.protocols import FsPathLike

class FileOperationsMixin:
    operations: FileSystemOperations
    logger: Any

    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError

    def read_text(self, path: FsPathLike, encoding: str = "utf-8") -> ReadResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            content = self.operations._read_text(norm_path, encoding)
            return ReadResult(success=True, path=norm_path, content=content, encoding=encoding, message=f"Read {len(content)} chars")
        except Exception as e:
            self.logger.error(f"read_text failed: {e}")
            safe_p = coerce_path_result(path)
            return ReadResult(success=False, path=safe_p.path if safe_p.success else None, content=None, encoding=encoding, error=str(e), message="Failed to read file")

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
            self.logger.error(f"write_text failed: {e}")
            safe_p = coerce_path_result(path)
            return WriteResult(success=False, path=safe_p.path if safe_p.success else None, error=str(e), message="Failed to write file")

    def read_binary(self, path: FsPathLike) -> ReadResult[bytes]:
        try:
            norm_path = self._normalize_input_path(path)
            content = self.operations._read_binary(norm_path)
            return ReadResult(success=True, path=norm_path, content=content, encoding=None, message=f"Read {len(content)} bytes")
        except Exception as e:
            self.logger.error(f"read_binary failed: {e}")
            safe_p = coerce_path_result(path)
            return ReadResult(success=False, path=safe_p.path if safe_p.success else None, content=None, encoding=None, error=str(e), message="Failed to read binary file")

    def write_binary(self, path: FsPathLike, content: bytes, atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
        try:
            norm_path = self._normalize_input_path(path)
            result_path = self.operations._write_binary(norm_path, content, atomic)
            bytes_written = len(content)
            checksum = None
            if calculate_checksum:
                checksum = self.operations._compute_checksum(result_path, "sha256")
            return WriteResult(success=True, path=result_path, bytes_written=bytes_written, checksum=checksum, message=f"Wrote {bytes_written} bytes")
        except Exception as e:
            self.logger.error(f"write_binary failed: {e}")
            safe_p = coerce_path_result(path)
            return WriteResult(success=False, path=safe_p.path if safe_p.success else None, error=str(e), message="Failed to write binary file")

    def read_lines(self, path: FsPathLike, encoding: str = "utf-8") -> ReadResult[list[str]]:
        try:
            norm_path = self._normalize_input_path(path)
            content_str = self.operations._read_text(norm_path, encoding)
            lines = content_str.splitlines()
            return ReadResult(success=True, path=norm_path, content=lines, encoding=encoding, message=f"Read {len(lines)} lines")
        except Exception as e:
            self.logger.error(f"read_lines failed: {e}")
            safe_p = coerce_path_result(path)
            return ReadResult(success=False, path=safe_p.path if safe_p.success else None, content=None, encoding=encoding, error=str(e), message="Failed to read lines")

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
            self.logger.error(f"write_lines failed: {e}")
            safe_p = coerce_path_result(path)
            return WriteResult(success=False, path=safe_p.path if safe_p.success else None, error=str(e), message="Failed to write lines")

    def copy(self, src: FsPathLike, dst: FsPathLike, overwrite: bool = False) -> WriteResult:
        try:
            norm_src = self._normalize_input_path(src)
            norm_dst = self._normalize_input_path(dst)
            result_path = self.operations._copy(norm_src, norm_dst, overwrite)
            size = 0
            if result_path.is_file(): size = result_path.stat().st_size
            return WriteResult(success=True, path=result_path, original_path=norm_src, bytes_written=size, message=f"Copied to {result_path}")
        except Exception as e:
            self.logger.error(f"copy failed: {e}")
            safe_src = coerce_path_result(src)
            safe_dst = coerce_path_result(dst)
            return WriteResult(success=False, path=safe_dst.path if safe_dst.success else None, original_path=safe_src.path if safe_src.success else None, error=str(e), message="Copy failed")

    def move(self, src: FsPathLike, dst: FsPathLike, overwrite: bool = False) -> WriteResult:
        try:
            norm_src = self._normalize_input_path(src)
            norm_dst = self._normalize_input_path(dst)
            result_path = self.operations._move(norm_src, norm_dst, overwrite)
            return WriteResult(success=True, path=result_path, original_path=norm_src, message=f"Moved to {result_path}")
        except Exception as e:
            self.logger.error(f"move failed: {e}")
            safe_src = coerce_path_result(src)
            safe_dst = coerce_path_result(dst)
            return WriteResult(success=False, path=safe_dst.path if safe_dst.success else None, original_path=safe_src.path if safe_src.success else None, error=str(e), message="Move failed")

    def delete(self, path: FsPathLike, missing_ok: bool = True) -> OperationResult:
        try:
            norm_path = self._normalize_input_path(path)
            deleted = self.operations._delete(norm_path, missing_ok)
            return OperationResult(success=True, path=norm_path, message="Deleted" if deleted else "Not found (ignored)")
        except Exception as e:
            self.logger.error(f"delete failed: {e}")
            safe_p = coerce_path_result(path)
            return OperationResult(success=False, path=safe_p.path if safe_p.success else None, error=str(e), message="Delete failed")