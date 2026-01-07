# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/utility_operations.py
# module: quack_core.core.fs.service.utility_operations
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+4 more)
# exports: UtilityOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/service/utility_operations.py
"""
Utility operations for the FileSystemService.
"""

from pathlib import Path

from quack_core.errors import wrap_io_errors
from quack_core.fs import DataResult, OperationResult, WriteResult
from quack_core.fs._operations import FileSystemOperations
from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class UtilityOperationsMixin:
    """Mixin class for utility operations in the FileSystemService."""

    # This ensures the mixin will only be used with classes that have operations
    operations: FileSystemOperations

    # This method is added in the base class
    def _normalize_input_path(self,
                              path: str | Path | DataResult | OperationResult) -> Path:
        """Normalize an input path to a Path object."""
        raise NotImplementedError("This method should be overridden")

    # --- Advanced and Utility Operations ---

    @wrap_io_errors
    def ensure_directory(
            self, path: str | Path | DataResult | OperationResult, exist_ok: bool = True
    ) -> OperationResult:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure exists (string, Path, DataResult, or OperationResult)
            exist_ok: If False, raise an error when directory exists

        Returns:
            OperationResult with operation status
        """
        normalized_path = self._normalize_input_path(path)
        try:
            result_path = self.operations._ensure_directory(normalized_path, exist_ok)
            return OperationResult(
                success=True,
                path=result_path,
                message=f"Directory ensured at: {result_path}"
            )
        except Exception as e:
            return OperationResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message="Failed to ensure directory"
            )

    @wrap_io_errors
    def get_unique_filename(
            self, directory: str | Path | DataResult | OperationResult, filename: str
    ) -> DataResult[str]:
        """
        Generate a unique filename in the given directory.

        Args:
            directory: Directory path (string, Path, DataResult, or OperationResult)
            filename: Base filename

        Returns:
            DataResult with the unique filename
        """
        normalized_directory = self._normalize_input_path(directory)
        try:
            unique_name = self.operations._get_unique_filename(normalized_directory,
                                                               filename)
            # Include the full path in the data for test compatibility
            full_path = str(normalized_directory / unique_name)
            return DataResult(
                success=True,
                path=normalized_directory,
                data=full_path,
                format="filename",
                message=f"Generated unique filename: {unique_name}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_directory,
                data="",
                format="filename",
                error=str(e),
                message="Failed to generate unique filename"
            )

    @wrap_io_errors
    def create_temp_file(
            self,
            suffix: str = ".txt",
            prefix: str = "quackcore_",
            directory: str | Path | DataResult | OperationResult | None = None,
    ) -> DataResult[str]:
        """
        Create a temporary file.

        Args:
            suffix: File suffix (e.g., ".txt")
            prefix: File prefix
            directory: Directory to create the file in (string, Path, DataResult, or OperationResult, default: system temp dir)

        Returns:
            DataResult with path to the created temporary file
        """
        try:
            if directory is not None:
                normalized_directory = self._normalize_input_path(directory)
                temp_file_path = self.operations._create_temp_file(suffix, prefix,
                                                                   normalized_directory)
            else:
                temp_file_path = self.operations._create_temp_file(suffix, prefix, None)

            return DataResult(
                success=True,
                path=temp_file_path,
                data=str(temp_file_path),
                format="path",
                message=f"Created temporary file: {temp_file_path}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=None,
                data="",
                format="path",
                error=str(e),
                message="Failed to create temporary file"
            )

    @wrap_io_errors
    def find_files_by_content(
            self, directory: str | Path | DataResult | OperationResult,
            text_pattern: str, recursive: bool = True
    ) -> DataResult[list[str]]:
        """
        Find files containing the given text pattern.

        Args:
            directory: Directory to search in (string, Path, DataResult, or OperationResult)
            text_pattern: Text pattern to search for
            recursive: Whether to search recursively

        Returns:
            DataResult with list of paths to files containing the pattern
        """
        normalized_directory = self._normalize_input_path(directory)
        try:
            matching_files = self.operations._find_files_by_content(
                normalized_directory, text_pattern, recursive
            )
            return DataResult(
                success=True,
                path=normalized_directory,
                data=[str(p) for p in matching_files],
                format="path_list",
                message=f"Found {len(matching_files)} files containing '{text_pattern}'"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_directory,
                data=[],
                format="path_list",
                error=str(e),
                message="Failed to find files by content"
            )

    @wrap_io_errors
    def get_disk_usage(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[dict[str, int]]:
        """
        Get disk usage information for the given path.

        Args:
            path: Path to get disk usage for (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with dictionary containing total, used, and free space in bytes
        """
        normalized_path = self._normalize_input_path(path)
        try:
            usage = self.operations._get_disk_usage(normalized_path)
            return DataResult(
                success=True,
                path=normalized_path,
                data=usage,
                format="disk_usage",
                message=f"Disk usage for {normalized_path}: {usage}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data={},
                format="disk_usage",
                error=str(e),
                message="Failed to get disk usage"
            )

    @wrap_io_errors
    def get_file_type(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[str]:
        """
        Get the type of a file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with file type string
        """
        normalized_path = self._normalize_input_path(path)
        try:
            file_type = self.operations._get_file_type(normalized_path)
            return DataResult(
                success=True,
                path=normalized_path,
                data=file_type,
                format="file_type",
                message=f"File type for {normalized_path}: {file_type}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data="",
                format="file_type",
                error=str(e),
                message="Failed to get file type"
            )

    @wrap_io_errors
    def get_file_size_str(self, size_bytes: int) -> DataResult[str]:
        """
        Convert file size in bytes to a human-readable string.

        Args:
            size_bytes: File size in bytes

        Returns:
            DataResult with human-readable file size (e.g., "2.5 MB")
        """
        try:
            size_str = self.operations._get_file_size_str(size_bytes)
            return DataResult(
                success=True,
                path=None,
                data=size_str,
                format="size_string",
                message=f"Converted {size_bytes} bytes to: {size_str}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=None,
                data="",
                format="size_string",
                error=str(e),
                message="Failed to convert file size"
            )

    @wrap_io_errors
    def get_mime_type(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[str] | None:
        """
        Get the MIME type of a file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with MIME type string or None if not determinable
        """
        normalized_path = self._normalize_input_path(path)
        try:
            mime_type = self.operations._get_mime_type(normalized_path)
            if mime_type is None:
                return DataResult(
                    success=True,
                    path=normalized_path,
                    data=None,
                    format="mime_type",
                    message=f"No MIME type could be determined for {normalized_path}"
                )
            return DataResult(
                success=True,
                path=normalized_path,
                data=mime_type,
                format="mime_type",
                message=f"MIME type for {normalized_path}: {mime_type}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data=None,
                format="mime_type",
                error=str(e),
                message="Failed to get MIME type"
            )

    @wrap_io_errors
    def is_path_writeable(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[bool]:
        """
        Check if a path is writeable.

        Args:
            path: Path to check (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with True if the path is writeable
        """
        normalized_path = self._normalize_input_path(path)
        try:
            is_writeable = self.operations._is_path_writeable(normalized_path)
            return DataResult(
                success=True,
                path=normalized_path,
                data=is_writeable,
                format="boolean",
                message=f"Path {normalized_path} is {'writeable' if is_writeable else 'not writeable'}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data=False,
                format="boolean",
                error=str(e),
                message="Failed to check if path is writeable"
            )

    @wrap_io_errors
    def is_file_locked(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[bool]:
        """
        Check if a file is locked by another process.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with True if the file is locked
        """
        normalized_path = self._normalize_input_path(path)
        try:
            is_locked = self.operations._is_file_locked(normalized_path)
            return DataResult(
                success=True,
                path=normalized_path,
                data=is_locked,
                format="boolean",
                message=f"File {normalized_path} is {'locked' if is_locked else 'not locked'}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data=False,
                format="boolean",
                error=str(e),
                message="Failed to check if file is locked"
            )

    @wrap_io_errors
    def get_file_timestamp(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[float]:
        """
        Get the latest timestamp (modification time) for a file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with timestamp as float
        """
        normalized_path = self._normalize_input_path(path)
        try:
            timestamp = self.operations._get_file_timestamp(normalized_path)
            return DataResult(
                success=True,
                path=normalized_path,
                data=timestamp,
                format="timestamp",
                message=f"File timestamp for {normalized_path}: {timestamp}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data=0.0,
                format="timestamp",
                error=str(e),
                message="Failed to get file timestamp"
            )

    @wrap_io_errors
    def compute_checksum(
            self, path: str | Path | DataResult | OperationResult,
            algorithm: str = "sha256"
    ) -> DataResult[str]:
        """
        Compute the checksum of a file.

        Args:
            path: Path to the file (string, Path, DataResult, or OperationResult)
            algorithm: Hash algorithm to use (default: "sha256")

        Returns:
            DataResult with hexadecimal string representing the checksum
        """
        normalized_path = self._normalize_input_path(path)
        try:
            checksum = self.operations._compute_checksum(normalized_path, algorithm)
            return DataResult(
                success=True,
                path=normalized_path,
                data=checksum,
                format="checksum",
                message=f"{algorithm} checksum for {normalized_path}: {checksum}"
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data="",
                format="checksum",
                error=str(e),
                message=f"Failed to compute {algorithm} checksum"
            )

    @wrap_io_errors
    def atomic_write(self, path: str | Path | DataResult | OperationResult,
                     content: str | bytes) -> WriteResult:
        """
        Write content to a file atomically using a temporary file.

        Args:
            path: Destination file path (string, Path, DataResult, or OperationResult)
            content: Content to write. Can be either string or bytes.

        Returns:
            WriteResult with path to the written file
        """
        normalized_path = self._normalize_input_path(path)
        try:
            # Determine if content is string or bytes
            if isinstance(content, str):
                result_path = self.operations._write_text(normalized_path, content,
                                                          atomic=True)
                bytes_written = len(content.encode('utf-8'))
            else:
                result_path = self.operations._write_binary(normalized_path, content,
                                                            atomic=True)
                bytes_written = len(content)

            return WriteResult(
                success=True,
                path=result_path,
                message=f"Content atomically written to {result_path}",
                bytes_written=bytes_written
            )
        except Exception as e:
            return WriteResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message="Failed to write content atomically",
                bytes_written=0
            )
