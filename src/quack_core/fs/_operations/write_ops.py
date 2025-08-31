# quack-core/src/quack-core/fs/_operations/write_ops.py
"""
File writing, copying, moving and deleting _operations.

This module provides internal _operations for modifying the filesystem,
including writing files, copying, moving, deleting files and directories,
and directory creation.
"""

from pathlib import Path

from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class WriteOperationsMixin:
    """
    File writing _operations mixin class.

    Provides internal methods for writing, copying, moving, and deleting
    files and directories.
    """

    def _resolve_path(self, path: str | Path) -> Path:
        """
        Resolve a path relative to the base directory.

        Args:
            path: Path to resolve (str or Path)

        Returns:
            Path: Resolved Path object

        Note:
            Internal helper method that must be implemented in the concrete class.
            Not meant for external consumption.
        """
        raise NotImplementedError("This method should be overridden")

    def _write_text(
            self,
            path: str | Path,
            content: str,
            encoding: str = "utf-8",
            atomic: bool = True,
            calculate_checksum: bool = False,
    ) -> Path:
        """
        Write text content to a file.

        This method handles various text encodings and can perform atomic writes
        for safer file _operations. It can also calculate checksums for data integrity.

        Args:
            path: Path to the file (str or Path)
            content: Text content to write
            encoding: Text encoding (default: utf-8)
            atomic: Whether to use atomic writing (safer but slower)
            calculate_checksum: Whether to calculate a checksum for verification

        Returns:
            Path: The actual path where the file was written

        Raises:
            IOError: If an error occurs during writing
            PermissionError: If there's no permission to write to the file
            FileNotFoundError: If the parent directory doesn't exist

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        # Import necessary utility functions
        from quack_core.fs._operations import (
            _atomic_write,
            _compute_checksum,
            _ensure_directory,
        )

        resolved_path = self._resolve_path(path)
        logger.debug(
            f"Writing text to {resolved_path} with encoding {encoding}, "
            f"atomic={atomic}, calculate_checksum={calculate_checksum}"
        )

        _ensure_directory(resolved_path.parent)
        logger.debug(f"Ensured parent directory exists: {resolved_path.parent}")

        # Handle special encoding (UTF-16 variants)
        if encoding.lower().startswith("utf-16"):
            if encoding.lower() == "utf-16":
                bytes_content = content.encode("utf-16")
            elif encoding.lower() == "utf-16-le":
                bytes_content = content.encode("utf-16-le")
            elif encoding.lower() == "utf-16-be":
                bytes_content = content.encode("utf-16-be")
            else:
                bytes_content = content.encode(encoding)
            logger.debug(f"Encoded text to UTF-16 variant: {encoding}")

            if atomic:
                logger.debug("Using atomic write for binary content (UTF-16)")
                # Capture the return value from atomic_write
                actual_path = _atomic_write(resolved_path, bytes_content)
            else:
                logger.debug("Using direct write for binary content (UTF-16)")
                with open(resolved_path, "wb") as f:
                    f.write(bytes_content)
                actual_path = resolved_path
        else:
            # For other encodings, use text mode
            if atomic:
                logger.debug("Using atomic write for text content")
                # Capture the return value from atomic_write (a Path object)
                actual_path = _atomic_write(resolved_path, content)
            else:
                logger.debug("Using direct write for text content")
                with open(resolved_path, "w", encoding=encoding) as f:
                    f.write(content)
                actual_path = resolved_path

        bytes_written = len(content.encode(encoding))
        logger.info(f"Successfully wrote {bytes_written} bytes to {actual_path}")

        if calculate_checksum:
            logger.debug(f"Calculating checksum for {actual_path}")
            checksum = _compute_checksum(actual_path)
            logger.debug(f"File checksum: {checksum}")

        return actual_path

    def _write_binary(
            self,
            path: str | Path,
            content: bytes,
            atomic: bool = True,
            calculate_checksum: bool = False,
    ) -> Path:
        """
        Write binary data to a file.

        This method writes raw binary data to a file with optional atomic
        writing and checksum calculation.

        Args:
            path: Path to the file (str or Path)
            content: Binary content to write
            atomic: Whether to use atomic writing (safer but slower)
            calculate_checksum: Whether to calculate a checksum for verification

        Returns:
            Path: The actual path where the file was written

        Raises:
            IOError: If an error occurs during writing
            PermissionError: If there's no permission to write to the file
            FileNotFoundError: If the parent directory doesn't exist

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        from quack_core.fs._operations import (
            _atomic_write,
            _compute_checksum,
            _ensure_directory,
        )

        resolved_path = self._resolve_path(path)
        logger.debug(
            f"Writing binary data to {resolved_path}, "
            f"atomic={atomic}, calculate_checksum={calculate_checksum}"
        )

        _ensure_directory(resolved_path.parent)
        logger.debug(f"Ensured parent directory exists: {resolved_path.parent}")

        if atomic:
            logger.debug("Using atomic write for binary data")
            actual_path = _atomic_write(resolved_path, content)
        else:
            logger.debug("Using direct write for binary data")
            with open(resolved_path, "wb") as f:
                f.write(content)
            actual_path = resolved_path

        logger.info(f"Successfully wrote {len(content)} bytes to {actual_path}")

        if calculate_checksum:
            logger.debug(f"Calculating checksum for {actual_path}")
            checksum = _compute_checksum(actual_path)
            logger.debug(f"File checksum: {checksum}")

        return actual_path

    def _copy(
            self,
            src: str | Path,
            dst: str | Path,
            overwrite: bool = False,
    ) -> Path:
        """
        Copy a file or directory.

        This method copies a file or directory to a new location with
        optional overwriting of existing files.

        Args:
            src: Source path (str or Path)
            dst: Destination path (str or Path)
            overwrite: Whether to overwrite if destination exists

        Returns:
            Path: The destination path where the file was copied

        Raises:
            FileNotFoundError: If the source doesn't exist
            FileExistsError: If the destination exists and overwrite is False
            PermissionError: If there's no permission to copy
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        from quack_core.fs._operations import _safe_copy

        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        logger.debug(f"Copying from {src_path} to {dst_path}, overwrite={overwrite}")

        copied_path = _safe_copy(src_path, dst_path, overwrite=overwrite)
        bytes_copied = copied_path.stat().st_size if copied_path.is_file() else 0
        logger.info(
            f"Successfully copied {src_path} to {dst_path} ({bytes_copied} bytes)")

        return copied_path

    def _move(
            self,
            src: str | Path,
            dst: str | Path,
            overwrite: bool = False,
    ) -> Path:
        """
        Move a file or directory.

        This method moves a file or directory to a new location with
        optional overwriting of existing files.

        Args:
            src: Source path (str or Path)
            dst: Destination path (str or Path)
            overwrite: Whether to overwrite if destination exists

        Returns:
            Path: The destination path where the file was moved

        Raises:
            FileNotFoundError: If the source doesn't exist
            FileExistsError: If the destination exists and overwrite is False
            PermissionError: If there's no permission to move
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        from quack_core.fs._operations import _safe_move

        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        logger.debug(f"Moving from {src_path} to {dst_path}, overwrite={overwrite}")

        # Get file size before moving (if it's a file)
        try:
            bytes_moved = src_path.stat().st_size if src_path.is_file() else 0
        except (FileNotFoundError, PermissionError):
            bytes_moved = 0
            logger.warning(f"Could not determine size of {src_path} before moving")

        moved_path = _safe_move(src_path, dst_path, overwrite=overwrite)
        logger.info(
            f"Successfully moved {src_path} to {moved_path} ({bytes_moved} bytes)")

        return moved_path

    def _delete(self, path: str | Path, missing_ok: bool = True) -> bool:
        """
        Delete a file or directory.

        This method safely removes a file or directory with configurable
        behavior for handling missing files.

        Args:
            path: Path to delete (str or Path)
            missing_ok: Whether to ignore if the path doesn't exist

        Returns:
            bool: True if the path was deleted, False if it didn't exist and missing_ok is True

        Raises:
            FileNotFoundError: If the path doesn't exist and missing_ok is False
            PermissionError: If there's no permission to delete
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        from quack_core.fs._operations import _safe_delete

        resolved_path = self._resolve_path(path)
        logger.debug(f"Deleting {resolved_path}, missing_ok={missing_ok}")

        result = _safe_delete(resolved_path, missing_ok=missing_ok)

        if result:
            logger.info(f"Successfully deleted {resolved_path}")
        else:
            logger.debug(f"Path {resolved_path} not found or not deleted")

        return result

    def _create_directory(
            self, path: str | Path, exist_ok: bool = True
    ) -> Path:
        """
        Create a directory.

        This method creates a directory with configurable behavior
        for handling existing directories.

        Args:
            path: Path to create (str or Path)
            exist_ok: Whether to ignore if the directory already exists

        Returns:
            Path: The path of the created directory

        Raises:
            FileExistsError: If the directory already exists and exist_ok is False
            PermissionError: If there's no permission to create the directory
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        from quack_core.fs._operations import _ensure_directory

        resolved_path = self._resolve_path(path)
        logger.debug(f"Creating directory {resolved_path}, exist_ok={exist_ok}")

        dir_path = _ensure_directory(resolved_path, exist_ok=exist_ok)
        logger.info(f"Successfully created directory {dir_path}")

        return dir_path
