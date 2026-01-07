# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/find_ops.py
# module: quack_core.core.fs._operations.find_ops
# role: module
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, path_ops.py (+4 more)
# exports: FindOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_operations/find_ops.py
"""
File finding _operations.

This module provides internal _operations for finding files and directories
based on patterns, with support for recursive searching and filtering.
"""

from pathlib import Path

from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class FindOperationsMixin:
    """
    File finding _operations mixin class.

    Provides internal methods for finding files and directories based on
    patterns, with support for recursive search and filtering options.
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

    def _find_files(
        self,
        path: str | Path,
        pattern: str,
        recursive: bool = True,
        include_hidden: bool = False,
    ) -> tuple[list[Path], list[Path]]:
        """
        Find files and directories matching a pattern.

        Args:
            path: Directory to search (str or Path)
            pattern: Pattern to match files against (glob pattern)
            recursive: Whether to search recursively in subdirectories
            include_hidden: Whether to include hidden files/directories
                           (those starting with ".")

        Returns:
            tuple[list[Path], list[Path]]: A tuple containing (matching files, matching directories)

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
            f"Finding files in {resolved_path} with pattern '{pattern}', "
            f"recursive={recursive}, include_hidden={include_hidden}"
        )

        # Early validation of the path
        if not self._validate_search_path(resolved_path):
            logger.error(
                f"Directory does not exist or is not a directory: {resolved_path}"
            )
            raise NotADirectoryError(
                f"Directory does not exist or is not a directory: {resolved_path}"
            )

        # Perform the search
        files, directories = self._perform_pattern_search(
            resolved_path, pattern, recursive, include_hidden
        )

        # Log results
        total_matches = len(files) + len(directories)
        logger.info(
            f"Found {len(files)} files and {len(directories)} directories "
            f"matching '{pattern}' in {resolved_path}"
        )

        return files, directories

    def _validate_search_path(self, path: Path) -> bool:
        """
        Validate that a path exists and is a directory.

        Args:
            path: Path to validate

        Returns:
            bool: True if the path exists and is a directory, False otherwise

        Note:
            Internal helper method not meant for external consumption.
            Used by _find_files to validate search paths.
        """
        valid = path.exists() and path.is_dir()
        if not valid:
            logger.debug(
                f"Path validation failed: exists={path.exists()}, is_dir={path.is_dir() if path.exists() else False}"
            )
        return valid

    def _perform_pattern_search(
        self, directory: Path, pattern: str, recursive: bool, include_hidden: bool
    ) -> tuple[list[Path], list[Path]]:
        """
        Perform the actual search for files and directories matching a pattern.

        Args:
            directory: Directory to search in
            pattern: Pattern to match against (glob pattern)
            recursive: Whether to search recursively
            include_hidden: Whether to include hidden files/directories

        Returns:
            tuple[list[Path], list[Path]]: tuple of (matching files, matching directories)

        Note:
            Internal helper method not meant for external consumption.
            Used by _find_files to perform the actual search logic.
        """
        files: list[Path] = []
        directories: list[Path] = []

        # Choose the appropriate search method explicitly
        if recursive:
            logger.debug(f"Performing recursive glob with pattern '{pattern}'")
            items = list(directory.rglob(pattern))
        else:
            logger.debug(f"Performing non-recursive glob with pattern '{pattern}'")
            items = list(directory.glob(pattern))

        logger.debug(f"Found {len(items)} total items matching pattern")

        for item in items:
            # Skip hidden items if not requested
            if not include_hidden and item.name.startswith("."):
                logger.debug(f"Skipping hidden item: {item}")
                continue

            try:
                if item.is_file():
                    files.append(item)
                    logger.debug(f"Found matching file: {item}")
                elif item.is_dir():
                    directories.append(item)
                    logger.debug(f"Found matching directory: {item}")
            except (PermissionError, OSError) as e:
                # Skip items we can't access
                logger.warning(f"Skipping inaccessible item {item}: {str(e)}")
                continue

        return files, directories
