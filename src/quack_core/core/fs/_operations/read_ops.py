# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/read_ops.py
# module: quack_core.core.fs._operations.read_ops
# role: module
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: ReadOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_operations/read_ops.py
"""
File reading _operations for the filesystem _operations.

This module provides internal _operations for reading both text and binary
data from files with basic error handling.
"""

from pathlib import Path

from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class ReadOperationsMixin:
    """
    File reading _operations mixin class.

    Provides internal methods for reading text and binary data from files
    with consistent error handling and return types.
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

    def _read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        """
        Read text from a file.

        Args:
            path: Path to the file (str or Path)
            encoding: Text encoding (default: utf-8)

        Returns:
            str: The file content as text

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to read the file
            UnicodeDecodeError: If the file content can't be decoded with the specified encoding
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Reading text from: {resolved_path} with encoding: {encoding}")

        with open(resolved_path, encoding=encoding) as f:
            content = f.read()

        logger.debug(
            f"Successfully read {len(content)} characters from {resolved_path}"
        )
        return content

    def _read_binary(self, path: str | Path) -> bytes:
        """
        Read binary data from a file.

        Args:
            path: Path to the file (str or Path)

        Returns:
            bytes: The file content as bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to read the file
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Reading binary data from: {resolved_path}")

        with open(resolved_path, "rb") as f:
            content = f.read()

        logger.debug(f"Successfully read {len(content)} bytes from {resolved_path}")
        return content
