# quack-core/src/quack_core/fs/service/directory_operations.py

from pathlib import Path
from typing import Protocol

from quack_core.errors import wrap_io_errors
from quack_core.fs._operations import FileSystemOperations
from quack_core.fs.results import (
    DataResult,
    DirectoryInfoResult,
    FileInfoResult,
    FindResult,
    OperationResult,
)
from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class HasOperations(Protocol):
    """Protocol for classes that have operations."""

    operations: FileSystemOperations


class DirectoryOperationsMixin:
    """Mixin class for directory operations in the FileSystemService."""

    # This ensures the mixin will only be used with classes that have operations
    operations: FileSystemOperations

    # This method is added in the base class
    def _normalize_input_path(self,
                              path: str | Path | DataResult | OperationResult) -> Path:
        """Normalize an input path to a Path object."""
        raise NotImplementedError("This method should be overridden")

    @wrap_io_errors
    def create_directory(
            self, path: str | Path | DataResult | OperationResult, exist_ok: bool = True
    ) -> OperationResult:
        """
        Create a directory.

        Args:
            path: Path to create (string, Path, DataResult, or OperationResult)
            exist_ok: Whether to ignore if the directory already exists

        Returns:
            OperationResult with operation status
        """
        normalized_path = self._normalize_input_path(path)
        try:
            result_path = self.operations._create_directory(normalized_path, exist_ok)
            return OperationResult(
                success=True,
                path=result_path,
                message=f"Directory created at: {result_path}"
            )
        except Exception as e:
            logger.error(f"Error creating directory {normalized_path}: {str(e)}")
            return OperationResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message=f"Failed to create directory: {normalized_path}"
            )

    # --- Information and Listing Operations ---

    @wrap_io_errors
    def get_file_info(self,
                      path: str | Path | DataResult | OperationResult) -> FileInfoResult:
        """
        Get information about a file or directory.

        Args:
            path: Path to get information about (string, Path, DataResult, or OperationResult)

        Returns:
            FileInfoResult with file information
        """
        normalized_path = self._normalize_input_path(path)
        try:
            file_info = self.operations._get_file_info(normalized_path)
            if not file_info.exists:
                return FileInfoResult(
                    success=True,
                    path=normalized_path,
                    exists=False,
                    message=f"Path does not exist: {normalized_path}"
                )

            return FileInfoResult(
                success=True,
                path=normalized_path,
                exists=file_info.exists,
                is_file=file_info.is_file,
                is_dir=file_info.is_dir,
                size=file_info.size,
                modified=file_info.modified,
                created=file_info.created,
                owner=file_info.owner,
                permissions=file_info.permissions,
                mime_type=file_info.mime_type,
                message=f"Retrieved file information for: {normalized_path}"
            )
        except Exception as e:
            logger.error(f"Error getting file info for {normalized_path}: {str(e)}")
            return FileInfoResult(
                success=False,
                path=normalized_path,
                exists=False,
                error=str(e),
                message=f"Failed to get file information: {normalized_path}"
            )

    @wrap_io_errors
    def list_directory(
            self,
            path: str | Path | DataResult | OperationResult,
            pattern: str | None = None,
            include_hidden: bool = False,
    ) -> DirectoryInfoResult:
        """
        List contents of a directory.

        Args:
            path: Path to list (string, Path, DataResult, or OperationResult)
            pattern: Pattern to match files against
            include_hidden: Whether to include hidden files

        Returns:
            DirectoryInfoResult with directory contents
        """
        normalized_path = self._normalize_input_path(path)
        try:
            dir_info = self.operations._list_directory(normalized_path, pattern,
                                                       include_hidden)

            # Convert Path objects to strings for the result
            files = [str(p) for p in dir_info.files]
            directories = [str(p) for p in dir_info.directories]

            return DirectoryInfoResult(
                success=True,
                path=normalized_path,
                exists=True,  # Fix: Set exists to True since we successfully listed the directory
                files=files,
                directories=directories,
                total_files=dir_info.total_files,
                total_directories=dir_info.total_directories,
                total_size=dir_info.total_size,
                is_empty=dir_info.is_empty,
                message=(
                    f"Listed directory {normalized_path}: "
                    f"{dir_info.total_files} files, {dir_info.total_directories} directories"
                )
            )
        except FileNotFoundError as e:
            logger.error(f"Directory not found {normalized_path}: {str(e)}")
            return DirectoryInfoResult(
                success=False,
                path=normalized_path,
                exists=False,
                files=[],
                directories=[],
                total_files=0,
                total_directories=0,
                total_size=0,
                is_empty=True,
                error=str(e),
                message=f"Directory not found: {normalized_path}"
            )
        except Exception as e:
            logger.error(f"Error listing directory {normalized_path}: {str(e)}")
            return DirectoryInfoResult(
                success=False,
                path=normalized_path,
                exists=False,
                files=[],
                directories=[],
                total_files=0,
                total_directories=0,
                total_size=0,
                is_empty=True,
                error=str(e),
                message=f"Failed to list directory: {normalized_path}"
            )

    @wrap_io_errors
    def find_files(
            self,
            path: str | Path | DataResult | OperationResult,
            pattern: str,
            recursive: bool = True,
            include_hidden: bool = False,
    ) -> FindResult:
        """
        Find files matching a pattern.

        Args:
            path: Directory to search (string, Path, DataResult, or OperationResult)
            pattern: Pattern to match files against
            recursive: Whether to search recursively
            include_hidden: Whether to include hidden files

        Returns:
            FindResult with matching files
        """
        normalized_path = self._normalize_input_path(path)
        try:
            files, directories = self.operations._find_files(
                normalized_path, pattern, recursive, include_hidden
            )

            # Convert Path objects to strings for the result
            file_paths = [str(p) for p in files]
            dir_paths = [str(p) for p in directories]

            return FindResult(
                success=True,
                path=normalized_path,
                files=file_paths,
                directories=dir_paths,
                pattern=pattern,
                recursive=recursive,
                include_hidden=include_hidden,
                message=(
                    f"Found {len(file_paths)} files and {len(dir_paths)} directories "
                    f"matching '{pattern}' in {normalized_path}"
                )
            )
        except Exception as e:
            logger.error(f"Error finding files in {normalized_path}: {str(e)}")
            return FindResult(
                success=False,
                path=normalized_path,
                files=[],
                directories=[],
                pattern=pattern,
                recursive=recursive,
                include_hidden=include_hidden,
                error=str(e),
                message=f"Failed to find files: {normalized_path}"
            )
