# quack-core/src/quack_core/fs/_operations/path_ops.py
"""
Path operations for filesystems.

This module provides internal operations for path manipulation, validation,
and information extraction, with support for cross-platform compatibility.
"""

import os
import re
from pathlib import Path

from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class PathOperationsMixin:
    """
    Path operations mixin class.

    Provides internal methods for path manipulation, validation, and information
    extraction, with support for cross-platform compatibility.
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

    def _split_path(self, path: str | Path) -> list[str]:
        """
        Split a path into its components.

        Args:
            path: Path to split

        Returns:
            list[str]: list of path components

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Splitting path: {resolved_path}")

        # For PureWindowsPath, use drive and parts
        if resolved_path.is_absolute() and hasattr(resolved_path,
                                                   "drive") and resolved_path.drive:
            # For Windows paths with drive component
            drive = resolved_path.drive
            parts = list(resolved_path.parts)
            if parts and parts[0] == drive:
                parts = parts[1:]  # Remove the drive from parts

            # Include the drive as a separate part if it exists
            components = [drive] + parts if drive else parts
        else:
            # For non-Windows paths or relative Windows paths
            components = list(resolved_path.parts)

        logger.debug(f"Path components: {components}")
        return components

    def _normalize_path(self, path: str | Path) -> Path:
        """
        Normalize a path for cross-platform compatibility.

        This method normalizes path separators, removes double slashes,
        and handles relative path components like '.' and '..'.

        Args:
            path: Path to normalize

        Returns:
            Path: Normalized Path object

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Normalizing path: {resolved_path}")

        try:
            # Normalize path separators, collapse redundant separators, and handle
            # relative components using Path's built-in normalization
            normalized = resolved_path.expanduser().resolve()
            logger.debug(f"Normalized path: {normalized}")
            return normalized
        except (FileNotFoundError, RuntimeError):
            # If the path doesn't exist or has too many symlinks,
            # normalize as best we can without resolving
            normalized = resolved_path.expanduser()
            logger.debug(f"Partially normalized path (file not found): {normalized}")
            return normalized

    def _expand_user_vars(self, path: str | Path) -> str:
        """
        Expand user variables and environment variables in a path.

        Args:
            path: Path with variables to expand

        Returns:
            str: Expanded path as string

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        path_str = str(resolved_path)
        logger.debug(f"Expanding variables in path: {path_str}")

        # Expand user home directory
        if "~" in path_str:
            path_str = os.path.expanduser(path_str)
            logger.debug(f"After expanduser: {path_str}")

        # Expand environment variables
        # Pattern for ${VAR} and $VAR forms
        pattern = r"\$\{([^}]+)\}|\$([a-zA-Z0-9_]+)"

        def replace_env_var(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, match.group(0))

        expanded_path = re.sub(pattern, replace_env_var, path_str)
        logger.debug(f"Expanded path: {expanded_path}")

        return expanded_path

    def _is_same_file(self, path1: str | Path, path2: str | Path) -> bool:
        """
        Check if two paths refer to the same file.

        Args:
            path1: First path
            path2: Second path

        Returns:
            bool: True if paths refer to the same file

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path1 = self._resolve_path(path1)
        resolved_path2 = self._resolve_path(path2)
        logger.debug(
            f"Checking if paths refer to the same file: {resolved_path1} and {resolved_path2}")

        try:
            # Handle non-existent files
            if not resolved_path1.exists() or not resolved_path2.exists():
                result = False
            else:
                # Use samefile for comparison
                result = resolved_path1.samefile(resolved_path2)

            logger.debug(f"Paths refer to the same file: {result}")
            return result
        except Exception as e:
            logger.error(f"Error checking if paths refer to the same file: {str(e)}")
            return False

    def _is_subdirectory(self, child: str | Path,
                         parent: str | Path) -> bool:
        """
        Check if a path is a subdirectory of another path.

        Args:
            child: Potential child path
            parent: Potential parent path

        Returns:
            bool: True if child is a subdirectory of parent

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_child = self._resolve_path(child)
        resolved_parent = self._resolve_path(parent)
        logger.debug(
            f"Checking if {resolved_child} is a subdirectory of {resolved_parent}")

        try:
            # Try to get absolute paths for more accurate comparison
            try:
                abs_child = resolved_child.resolve()
                abs_parent = resolved_parent.resolve()
            except (FileNotFoundError, RuntimeError):
                # If paths don't exist or have symlink loops, use the originals
                abs_child = resolved_child
                abs_parent = resolved_parent

            # Check if parent is a parent of child
            try:
                is_subdirectory = abs_parent in abs_child.parents
            except (ValueError, TypeError):
                # Some path objects might not support the parents property
                # Fall back to string-based comparison
                str_child = str(abs_child)
                str_parent = str(abs_parent)
                is_subdirectory = (
                        str_child.startswith(str_parent)
                        and (
                                len(str_child) == len(str_parent)
                                or str_child[len(str_parent)] == os.sep
                        )
                )

            logger.debug(f"Is subdirectory: {is_subdirectory}")
            return is_subdirectory
        except Exception as e:
            logger.error(f"Error checking if path is a subdirectory: {str(e)}")
            return False

    def _get_extension(self, path: str | Path) -> str:
        """
        Get the file extension from a path.

        Args:
            path: Path to get extension from

        Returns:
            str: File extension without the dot

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Getting file extension for: {resolved_path}")

        # Get the extension and remove the leading dot
        ext = resolved_path.suffix.lstrip(".")
        logger.debug(f"File extension: {ext}")
        return ext

    def _is_path_syntax_valid(self, path_str: str) -> bool:
        """
        Check if a path string has valid syntax.

        Args:
            path_str: Path string to check

        Returns:
            bool: True if the path has valid syntax

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        logger.debug(f"Checking if path syntax is valid: {path_str}")

        try:
            # Attempt to create a Path object from the string
            path_obj = Path(path_str)

            # Windows-specific checks for reserved characters and names
            if os.name == "nt":
                reserved_chars = '<>:"|?*'
                if any(char in path_obj.name for char in reserved_chars):
                    logger.debug(f"Path contains reserved characters: {path_str}")
                    return False

                reserved_names = [
                    "CON", "PRN", "AUX", "NUL",
                    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8",
                    "COM9",
                    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8",
                    "LPT9"
                ]
                if any(part.upper() in reserved_names for part in path_obj.parts):
                    logger.debug(f"Path contains reserved names: {path_str}")
                    return False

            logger.debug(f"Path syntax is valid: {path_str}")
            return True
        except Exception as e:
            logger.debug(f"Path syntax is invalid: {path_str}, error: {str(e)}")
            return False
