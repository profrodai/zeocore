# quack-core/src/quack-core/fs/_operations/file_info.py
"""
File information _operations.

This module provides internal _operations for retrieving metadata and information
about files and paths in the filesystem. These _operations are used by the public
API but are not meant to be consumed directly.
"""

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from quackcore.logging import get_logger

# Set up logger
logger = get_logger(__name__)


@dataclass
class FileInfo:
    """
    Container for file metadata.

    Holds comprehensive information about a file or directory.
    """
    path: Path
    exists: bool
    is_file: bool = False
    is_dir: bool = False
    size: int = 0
    modified: float = 0.0
    created: float = 0.0
    owner: str | None = None
    permissions: int = 0
    mime_type: str | None = None


class FileInfoOperationsMixin:
    """
    File information _operations mixin class.

    Provides internal methods for retrieving metadata about files and paths,
    including existence checks, permissions, size, and MIME types.
    """

    def _resolve_path(self, path: str | Path) -> Path:
        """
        Resolve a path relative to the base directory.

        Args:
            path: Path to resolve (str or Path)

        Returns:
            Path: Resolved Path object

        Note:
            Internal helper method implemented in the main class.
            Not meant for external consumption.
        """
        # This method is implemented in the main class
        # It's defined here for type checking
        raise NotImplementedError("This method should be overridden")

    def _path_exists(self, path: str | Path) -> bool:
        """
        Check if a path exists.

        Args:
            path: Path to check (str or Path)

        Returns:
            bool: True if the path exists, False otherwise

        Note:
            Internal helper method not meant for external consumption.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Checking if path exists: {resolved_path}")

        try:
            exists = resolved_path.exists()
            is_abs = resolved_path.is_absolute()
            logger.debug(
                f"Path {resolved_path} exists: {exists}, is absolute: {is_abs}"
            )

            return exists
        except Exception as e:
            logger.error(f"Error checking if path exists for {resolved_path}: {str(e)}")
            return False

    def _get_file_info(self, path: str | Path) -> FileInfo:
        """
        Get comprehensive information about a file or directory.

        This method retrieves metadata including basic properties,
        timestamps, ownership, permissions, and MIME type.

        Args:
            path: Path to get information about (str or Path)

        Returns:
            FileInfo: Object containing detailed file information

        Raises:
            PermissionError: If there's no permission to access the file
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Getting file info for: {resolved_path}")

        # Use our _path_exists method to check existence
        exists = self._path_exists(resolved_path)
        if not exists:
            logger.info(f"Path does not exist: {resolved_path}")
            return FileInfo(
                path=resolved_path,
                exists=False,
            )

        # Gather file stats
        stats = resolved_path.stat()
        mime_type = None

        # Get MIME type for files
        if resolved_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(resolved_path))
            logger.debug(f"Determined MIME type for {resolved_path}: {mime_type}")

        # Try to get owner information
        owner = None
        try:
            import pwd
            owner = pwd.getpwuid(stats.st_uid).pw_name
            logger.debug(f"Determined file owner for {resolved_path}: {owner}")
        except (ImportError, KeyError) as e:
            logger.debug(f"Could not determine owner for {resolved_path}: {str(e)}")
            # Continue without owner info

        logger.info(f"Successfully retrieved file info for {resolved_path}")
        return FileInfo(
            path=resolved_path,
            exists=True,
            is_file=resolved_path.is_file(),
            is_dir=resolved_path.is_dir(),
            size=stats.st_size,
            modified=stats.st_mtime,
            created=stats.st_ctime,
            owner=owner,
            permissions=stats.st_mode,
            mime_type=mime_type,
        )
