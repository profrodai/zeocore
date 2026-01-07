# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/directory_ops.py
# module: quack_core.core.fs._operations.directory_ops
# role: module
# neighbors: __init__.py, base.py, core.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# exports: DirectoryInfo, DirectoryOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_operations/directory_ops.py
"""
Directory _operations.

This module provides internal _operations for working with directories, including
listing contents, getting directory information, and filtering by patterns.
"""

from pathlib import Path

from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class DirectoryInfo:
    """
    Container for directory information.

    This class holds basic information about a directory's contents.
    """

    def __init__(
            self,
            path: Path,
            files: list[Path],
            directories: list[Path],
            total_size: int,
            is_empty: bool,
    ):
        self.path = path
        self.files = files
        self.directories = directories
        self.total_files = len(files)
        self.total_directories = len(directories)
        self.total_size = total_size
        self.is_empty = is_empty


class DirectoryOperationsMixin:
    """
    Directory _operations mixin class.

    Provides internal methods for working with directories, listing their contents,
    and filtering by patterns.
    """

    def _resolve_path(self, path: str | Path) -> Path:
        """
        Resolve a path relative to the base directory.

        Args:
            path: Path to resolve (str or Path)

        Returns:
            Path: Resolved Path object

        Note:
            This method is implemented in the main class.
            It's defined here for type checking.
            Internal helper method not meant for external consumption.
        """
        # This method is implemented in the main class
        # It's defined here for type checking
        raise NotImplementedError("This method should be overridden")

    def _list_directory(
            self, path: str | Path, pattern: str | None = None,
            include_hidden: bool = False
    ) -> DirectoryInfo:
        """
        List contents of a directory with optional pattern filtering.

        This method scans a directory and returns information about its contents,
        including files and subdirectories. Results can be filtered using
        a glob pattern and hidden files can be optionally included.

        Args:
            path: Path to the directory to list (str or Path)
            pattern: Optional glob pattern to match files and directories against
                     (e.g., "*.py", "data*", etc.)
            include_hidden: Whether to include hidden files/directories
                           (those starting with ".")

        Returns:
            DirectoryInfo: Object containing directory contents information including
                          files, directories, sizes, and counts

        Raises:
            FileNotFoundError: If the directory doesn't exist
            NotADirectoryError: If the path is not a directory
            PermissionError: If there's no permission to read the directory
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(
            f"Listing directory {resolved_path}, "
            f"pattern={pattern}, include_hidden={include_hidden}"
        )

        # Check if the path exists and is a directory
        if not resolved_path.exists():
            logger.error(f"Directory does not exist: {resolved_path}")
            raise FileNotFoundError(f"Directory does not exist: {resolved_path}")

        if not resolved_path.is_dir():
            logger.error(f"Path is not a directory: {resolved_path}")
            raise NotADirectoryError(f"Path is not a directory: {resolved_path}")

        files = []
        directories = []
        total_size = 0

        for item in resolved_path.iterdir():
            # Skip hidden files if needed
            if not include_hidden and item.name.startswith("."):
                logger.debug(f"Skipping hidden item: {item}")
                continue

            # Skip items that don't match the pattern
            if pattern and not item.match(pattern):
                logger.debug(f"Skipping item not matching pattern: {item}")
                continue

            if item.is_file():
                try:
                    item_size = item.stat().st_size
                    total_size += item_size
                    files.append(item)
                    logger.debug(f"Found file: {item}, size: {item_size}")
                except (PermissionError, OSError) as e:
                    # Skip files we can't access but log the issue
                    logger.warning(f"Skipping inaccessible file {item}: {str(e)}")
            elif item.is_dir():
                directories.append(item)
                logger.debug(f"Found directory: {item}")

        is_empty = len(files) == 0 and len(directories) == 0
        logger.info(
            f"Found {len(files)} files and {len(directories)} directories in {resolved_path}"
        )

        # Ensure pattern is displayed correctly in message
        pattern_msg = f"matching '{pattern}'" if pattern else ""
        logger.debug(
            f"Directory listing complete. Found {len(files)} files and {len(directories)} directories {pattern_msg}".strip()
        )

        return DirectoryInfo(
            path=resolved_path,
            files=files,
            directories=directories,
            total_size=total_size,
            is_empty=is_empty
        )

    # TODO: Implement delete_directory in fs
