# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/file_operations.py
# module: quack_core.core.fs.service.file_operations
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, full_class.py, path_operations.py (+4 more)
# exports: FileOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/service/file_operations.py

from pathlib import Path

from quack_core.errors import wrap_io_errors
from quack_core.fs._operations import FileSystemOperations
from quack_core.fs.results import DataResult, OperationResult, ReadResult, WriteResult
from quack_core.logging import get_logger

logger = get_logger(__name__)


class FileOperationsMixin:
    """Mixin class for file operations in the FileSystemService."""

    # This mixin expects the implementing class to have an attribute '_operations'
    # that is an instance of FileSystemOperations.
    operations: FileSystemOperations

    # This method is added in the base class
    def _normalize_input_path(self,
                              path: str | Path | DataResult | OperationResult) -> Path:
        """Normalize an input path to a Path object."""
        raise NotImplementedError("This method should be overridden")

    @wrap_io_errors
    def read_text(self, path: str | Path | DataResult | OperationResult,
                  encoding: str = "utf-8") -> ReadResult[str]:
        """
        Read text content from a file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)
            encoding: Text encoding to use (default: utf-8).

        Returns:
            ReadResult with the file content as text.
        """
        normalized_path = self._normalize_input_path(path)
        try:
            content = self.operations._read_text(normalized_path, encoding)
            logger.debug(
                f"Successfully read {len(content)} characters from {normalized_path}")
            return ReadResult(
                success=True,
                path=normalized_path,
                content=content,
                encoding=encoding,
                message=f"Successfully read text from {normalized_path}"
            )
        except Exception as e:
            logger.error(f"Error reading text from {normalized_path}: {str(e)}")
            return ReadResult(
                success=False,
                path=normalized_path,
                content="",
                encoding=encoding,
                error=str(e),
                message=f"Failed to read text from {normalized_path}"
            )

    @wrap_io_errors
    def write_text(
            self,
            path: str | Path | DataResult | OperationResult,
            content: str,
            encoding: str = "utf-8",
            atomic: bool = True,
            calculate_checksum: bool = False,
    ) -> WriteResult:
        """
        Write text content to a file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)
            content: Text content to write.
            encoding: Text encoding to use (default: utf-8).
            atomic: Whether to use atomic write (default: True).
            calculate_checksum: Whether to calculate a checksum (default: False).

        Returns:
            WriteResult with operation status.
        """
        normalized_path = self._normalize_input_path(path)
        try:
            result_path = self.operations._write_text(
                normalized_path, content, encoding, atomic, calculate_checksum
            )
            logger.debug(f"Successfully wrote text to {result_path}")

            # Calculate the bytes written
            bytes_written = len(content.encode(encoding))

            # If checksum was requested, calculate it
            checksum = None
            if calculate_checksum:
                checksum = self.operations._compute_checksum(result_path)

            return WriteResult(
                success=True,
                path=result_path,
                message=f"Successfully wrote text to {result_path}",
                bytes_written=bytes_written,
                checksum=checksum
            )
        except Exception as e:
            logger.error(f"Error writing text to {normalized_path}: {str(e)}")
            return WriteResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message=f"Failed to write text to {normalized_path}",
                bytes_written=0
            )

    @wrap_io_errors
    def read_binary(self, path: str | Path | DataResult | OperationResult) -> \
            ReadResult[bytes]:
        """
        Read binary content from a file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)

        Returns:
            ReadResult with the file content as bytes.
        """
        normalized_path = self._normalize_input_path(path)
        try:
            content = self.operations._read_binary(normalized_path)
            logger.debug(
                f"Successfully read {len(content)} bytes from {normalized_path}")
            return ReadResult(
                success=True,
                path=normalized_path,
                content=content,
                encoding=None,
                message=f"Successfully read binary data from {normalized_path}"
            )
        except Exception as e:
            logger.error(f"Error reading binary data from {normalized_path}: {str(e)}")
            return ReadResult(
                success=False,
                path=normalized_path,
                content=b"",
                encoding=None,
                error=str(e),
                message=f"Failed to read binary data from {normalized_path}"
            )

    @wrap_io_errors
    def write_binary(
            self,
            path: str | Path | DataResult | OperationResult,
            content: bytes,
            atomic: bool = True,
            calculate_checksum: bool = False,
    ) -> WriteResult:
        """
        Write binary content to a file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)
            content: Binary content to write.
            atomic: Whether to use atomic write (default: True).
            calculate_checksum: Whether to calculate a checksum (default: False).

        Returns:
            WriteResult with operation status.
        """
        normalized_path = self._normalize_input_path(path)
        try:
            result_path = self.operations._write_binary(normalized_path, content,
                                                        atomic, calculate_checksum)
            logger.debug(f"Successfully wrote binary data to {result_path}")

            # Calculate the number of bytes written
            bytes_written = len(content)

            # If checksum was requested, calculate it
            checksum = None
            if calculate_checksum:
                checksum = self.operations._compute_checksum(result_path)

            return WriteResult(
                success=True,
                path=result_path,
                message=f"Successfully wrote binary data to {result_path}",
                bytes_written=bytes_written,
                checksum=checksum
            )
        except Exception as e:
            logger.error(f"Error writing binary data to {normalized_path}: {str(e)}")
            return WriteResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message=f"Failed to write binary data to {normalized_path}",
                bytes_written=0
            )

    @wrap_io_errors
    def read_lines(
            self, path: str | Path | DataResult | OperationResult,
            encoding: str = "utf-8"
    ) -> ReadResult[list[str]]:
        """
        Read lines from a text file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)
            encoding: Text encoding

        Returns:
            ReadResult with the file content as a list of lines
        """
        normalized_path = self._normalize_input_path(path)
        try:
            text_content = self.operations._read_text(normalized_path, encoding)
            lines = text_content.splitlines()
            logger.debug(f"Successfully read {len(lines)} lines from {normalized_path}")
            return ReadResult(
                success=True,
                path=normalized_path,
                content=lines,
                encoding=encoding,
                message=f"Successfully read {len(lines)} lines from {normalized_path}"
            )
        except Exception as e:
            logger.error(f"Error reading lines from {normalized_path}: {str(e)}")
            return ReadResult(
                success=False,
                path=normalized_path,
                content=[],
                encoding=encoding,
                error=str(e),
                message=f"Failed to read lines from {normalized_path}"
            )

    @wrap_io_errors
    def write_lines(
            self,
            path: str | Path | DataResult | OperationResult,
            lines: list[str],
            encoding: str = "utf-8",
            atomic: bool = True,
            line_ending: str = "\n",
    ) -> WriteResult:
        """
        Write lines to a text file.

        This method explicitly joins the lines using the specified line ending.
        When a non-default line ending is provided, the content is encoded and written
        in binary mode to prevent any unwanted normalization.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)
            lines: Lines to write.
            encoding: Text encoding to use.
            atomic: Whether to write the file atomically.
            line_ending: The line ending to use.

        Returns:
            WriteResult indicating the outcome of the write operation.
        """
        normalized_path = self._normalize_input_path(path)
        try:
            content = line_ending.join(lines)
            # For non-default line endings, encode and write in binary mode.
            bytes_written = 0
            if line_ending != "\n":
                bytes_content = content.encode(encoding)
                result_path = self.operations._write_binary(normalized_path,
                                                            bytes_content, atomic)
                bytes_written = len(bytes_content)
            else:
                result_path = self.operations._write_text(normalized_path, content,
                                                          encoding, atomic)
                bytes_written = len(content.encode(encoding))

            logger.debug(f"Successfully wrote {len(lines)} lines to {result_path}")
            return WriteResult(
                success=True,
                path=result_path,
                message=f"Successfully wrote {len(lines)} lines to {result_path}",
                bytes_written=bytes_written
            )
        except Exception as e:
            logger.error(f"Error writing lines to {normalized_path}: {str(e)}")
            return WriteResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message=f"Failed to write lines to {normalized_path}",
                bytes_written=0
            )

    # File management operations
    @wrap_io_errors
    def copy(
            self, src: str | Path | DataResult | OperationResult,
            dst: str | Path | DataResult | OperationResult, overwrite: bool = False
    ) -> WriteResult:
        """
        Copy a file or directory.

        Args:
            src: Source path (string, Path, DataResult, or OperationResult)
            dst: Destination path (string, Path, DataResult, or OperationResult)
            overwrite: Whether to overwrite if destination exists

        Returns:
            WriteResult with operation status
        """
        normalized_src = self._normalize_input_path(src)
        normalized_dst = self._normalize_input_path(dst)
        try:
            result_path = self.operations._copy(normalized_src, normalized_dst,
                                                overwrite)
            logger.debug(f"Successfully copied {normalized_src} to {result_path}")

            # Get the size of the copied file if possible
            bytes_written = 0
            try:
                if result_path.is_file():
                    bytes_written = result_path.stat().st_size
            except Exception:
                pass

            return WriteResult(
                success=True,
                path=result_path,
                message=f"Successfully copied {normalized_src} to {result_path}",
                bytes_written=bytes_written
            )
        except Exception as e:
            logger.error(
                f"Error copying {normalized_src} to {normalized_dst}: {str(e)}")
            return WriteResult(
                success=False,
                path=normalized_dst,
                error=str(e),
                message=f"Failed to copy {normalized_src} to {normalized_dst}",
                bytes_written=0
            )

    @wrap_io_errors
    def move(
            self, src: str | Path | DataResult | OperationResult,
            dst: str | Path | DataResult | OperationResult, overwrite: bool = False
    ) -> WriteResult:
        """
        Move a file or directory.

        Args:
            src: Source path (string, Path, DataResult, or OperationResult)
            dst: Destination path (string, Path, DataResult, or OperationResult)
            overwrite: Whether to overwrite if destination exists

        Returns:
            WriteResult with operation status
        """
        normalized_src = self._normalize_input_path(src)
        normalized_dst = self._normalize_input_path(dst)
        try:
            # Get file size before moving if possible
            bytes_written = 0
            try:
                if normalized_src.is_file():
                    bytes_written = normalized_src.stat().st_size
            except Exception:
                pass

            result_path = self.operations._move(normalized_src, normalized_dst,
                                                overwrite)
            logger.debug(f"Successfully moved {normalized_src} to {result_path}")
            return WriteResult(
                success=True,
                path=result_path,
                message=f"Successfully moved {normalized_src} to {result_path}",
                bytes_written=bytes_written
            )
        except Exception as e:
            logger.error(f"Error moving {normalized_src} to {normalized_dst}: {str(e)}")
            return WriteResult(
                success=False,
                path=normalized_dst,
                error=str(e),
                message=f"Failed to move {normalized_src} to {normalized_dst}",
                bytes_written=0
            )

    @wrap_io_errors
    def delete(self, path: str | Path | DataResult | OperationResult,
               missing_ok: bool = True) -> OperationResult:
        """
        Delete a file or directory.

        Args:
            path: Path to delete (string, Path, DataResult, or OperationResult)
            missing_ok: Whether to ignore if the path doesn't exist

        Returns:
            OperationResult with operation status
        """
        normalized_path = self._normalize_input_path(path)
        try:
            result = self.operations._delete(normalized_path, missing_ok)
            if result:
                logger.debug(f"Successfully deleted {normalized_path}")
                return OperationResult(
                    success=True,
                    path=normalized_path,
                    message=f"Successfully deleted {normalized_path}"
                )
            else:
                # Path didn't exist and missing_ok was True
                logger.debug(f"Path {normalized_path} not found, no deletion needed")
                return OperationResult(
                    success=True,
                    path=normalized_path,
                    message=f"Path {normalized_path} not found, no deletion needed"
                )
        except Exception as e:
            logger.error(f"Error deleting {normalized_path}: {str(e)}")
            return OperationResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message=f"Failed to delete {normalized_path}"
            )
