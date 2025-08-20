# quack-core/src/quack-core/fs/_operations/utility_ops.py
"""
Utility operations for filesystems.

This module provides internal operations for filesystem utilities like calculating checksums,
creating temporary files, finding unique filenames, and other specialized tasks.
"""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from quackcore.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class UtilityOperationsMixin:
    """
    Utility operations mixin class.

    Provides internal methods for utility operations like computing checksums,
    creating temporary files, ensuring directories exist, and other specialized tasks.
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

    def _compute_checksum(self, path: str | Path,
                          algorithm: str = "sha256") -> str:
        """
        Compute the checksum of a file.

        Args:
            path: Path to the file
            algorithm: Hash algorithm to use (default: "sha256")

        Returns:
            str: Hexadecimal string representing the checksum

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to read the file
            ValueError: If an unsupported algorithm is specified
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Computing {algorithm} checksum for: {resolved_path}")

        if not resolved_path.exists():
            logger.error(f"File not found: {resolved_path}")
            raise FileNotFoundError(f"File not found: {resolved_path}")

        if not resolved_path.is_file():
            logger.error(f"Path is not a file: {resolved_path}")
            raise ValueError(f"Path is not a file: {resolved_path}")

        # Get the hash algorithm
        try:
            hash_obj = hashlib.new(algorithm)
        except ValueError:
            logger.error(f"Unsupported hash algorithm: {algorithm}")
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        # Read the file in chunks to handle large files efficiently
        buffer_size = 65536  # 64KB chunks
        try:
            with open(resolved_path, "rb") as f:
                while True:
                    data = f.read(buffer_size)
                    if not data:
                        break
                    hash_obj.update(data)

            checksum = hash_obj.hexdigest()
            logger.debug(f"Computed {algorithm} checksum: {checksum}")
            return checksum
        except Exception as e:
            logger.error(f"Error computing checksum for {resolved_path}: {str(e)}")
            raise

    def _create_temp_file(
            self,
            suffix: str = ".txt",
            prefix: str = "quackcore_",
            directory: str | Path | None = None,
    ) -> Path:
        """
        Create a temporary file.

        Args:
            suffix: File suffix (e.g., ".txt")
            prefix: File prefix
            directory: Directory to create the file in (default: system temp dir)

        Returns:
            Path: Path to the created temporary file

        Raises:
            PermissionError: If there's no permission to create the file
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        try:
            resolved_dir = None
            if directory is not None:
                resolved_dir = self._resolve_path(directory)
                logger.debug(f"Creating temp file in custom directory: {resolved_dir}")
                if not resolved_dir.exists():
                    logger.debug(
                        f"Directory {resolved_dir} does not exist, creating it")
                    resolved_dir.mkdir(parents=True, exist_ok=True)
            else:
                logger.debug("Creating temp file in system temp directory")

            # Create the temporary file
            fd, temp_path = tempfile.mkstemp(
                suffix=suffix, prefix=prefix, dir=resolved_dir
            )
            # Close the file descriptor since we only want the path
            os.close(fd)

            path_obj = Path(temp_path)
            logger.info(f"Created temporary file: {path_obj}")
            return path_obj
        except Exception as e:
            logger.error(f"Error creating temporary file: {str(e)}")
            raise

    def _create_temp_directory(
            self, prefix: str = "quackcore_", suffix: str = ""
    ) -> Path:
        """
        Create a temporary directory.

        Args:
            prefix: Prefix for the temporary directory name
            suffix: Suffix for the temporary directory name

        Returns:
            Path: Path to the created temporary directory

        Raises:
            PermissionError: If there's no permission to create the directory
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        try:
            temp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix)
            path_obj = Path(temp_dir)
            logger.info(f"Created temporary directory: {path_obj}")
            return path_obj
        except Exception as e:
            logger.error(f"Error creating temporary directory: {str(e)}")
            raise

    def _get_unique_filename(
            self, directory: str | Path, filename: str
    ) -> str:
        """
        Generate a unique filename in the given directory.

        If the filename already exists, it appends a numeric suffix to ensure uniqueness.

        Args:
            directory: Directory path
            filename: Base filename

        Returns:
            str: Unique filename

        Raises:
            FileNotFoundError: If the directory doesn't exist
            NotADirectoryError: If the path is not a directory
            PermissionError: If there's no permission to read the directory
            ValueError: If the filename is empty
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_dir = self._resolve_path(directory)
        logger.debug(
            f"Getting unique filename for '{filename}' in directory: {resolved_dir}")

        if not resolved_dir.exists():
            logger.error(f"Directory does not exist: {resolved_dir}")
            raise FileNotFoundError(f"Directory does not exist: {resolved_dir}")

        if not resolved_dir.is_dir():
            logger.error(f"Path is not a directory: {resolved_dir}")
            raise NotADirectoryError(f"Path is not a directory: {resolved_dir}")

        if not filename:
            logger.error("Filename cannot be empty")
            raise ValueError("Filename cannot be empty")

        # Split the filename into base name and extension
        base_name, ext = os.path.splitext(filename)
        counter = 0
        current_name = filename

        # Find a unique name by incrementing counter until we find one that doesn't exist
        while (resolved_dir / current_name).exists():
            counter += 1
            current_name = f"{base_name}_{counter}{ext}"
            logger.debug(f"Testing filename: {current_name}")

        logger.info(f"Generated unique filename: {current_name}")
        return current_name

    def _ensure_directory(self, path: str | Path, exist_ok: bool = True) -> Path:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure exists
            exist_ok: If False, raise an error when directory exists

        Returns:
            Path: Path to the directory

        Raises:
            FileExistsError: If the directory exists and exist_ok is False
            PermissionError: If there's no permission to create the directory
            FileNotFoundError: If the parent directory doesn't exist
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Ensuring directory exists: {resolved_path}, exist_ok={exist_ok}")

        try:
            resolved_path.mkdir(parents=True, exist_ok=exist_ok)
            logger.info(f"Directory ensured: {resolved_path}")
            return resolved_path
        except Exception as e:
            logger.error(f"Error ensuring directory {resolved_path}: {str(e)}")
            raise

    def _get_disk_usage(self, path: str | Path) -> dict[str, int]:
        """
        Get disk usage information for the given path.

        Args:
            path: Path to get disk usage for

        Returns:
            dict[str, int]: Dictionary with total, used, and free space in bytes

        Raises:
            FileNotFoundError: If the path doesn't exist
            PermissionError: If there's no permission to access the path
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Getting disk usage for: {resolved_path}")

        if not resolved_path.exists():
            logger.error(f"Path does not exist: {resolved_path}")
            raise FileNotFoundError(f"Path does not exist: {resolved_path}")

        try:
            usage = shutil.disk_usage(resolved_path)
            result = {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
            }
            logger.debug(f"Disk usage for {resolved_path}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting disk usage for {resolved_path}: {str(e)}")
            raise

    def _get_file_size_str(self, size_bytes: int) -> str:
        """
        Convert file size in bytes to a human-readable string.

        Args:
            size_bytes: File size in bytes

        Returns:
            str: Human-readable file size (e.g., "2.5 MB")

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        logger.debug(f"Converting {size_bytes} bytes to human-readable format")

        if size_bytes < 0:
            logger.warning("Negative file size provided")
            size_bytes = 0

        units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        # Format with 2 decimal places if above bytes, otherwise as an integer
        if unit_index == 0:
            formatted_size = f"{int(size)} {units[unit_index]}"
        else:
            formatted_size = f"{size:.2f} {units[unit_index]}"

        logger.debug(f"Formatted size: {formatted_size}")
        return formatted_size

    def _get_file_timestamp(self, path: str | Path) -> float:
        """
        Get the latest timestamp (modification time) for a file.

        Args:
            path: Path to the file

        Returns:
            float: Timestamp as float

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to access the file
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Getting file timestamp for: {resolved_path}")

        if not resolved_path.exists():
            logger.error(f"File not found: {resolved_path}")
            raise FileNotFoundError(f"File not found: {resolved_path}")

        try:
            timestamp = resolved_path.stat().st_mtime
            logger.debug(f"File timestamp for {resolved_path}: {timestamp}")
            return timestamp
        except Exception as e:
            logger.error(f"Error getting timestamp for {resolved_path}: {str(e)}")
            raise

    def _get_file_type(self, path: str | Path) -> str:
        """
        Get the type of a file (file, directory, symlink, etc.).

        Args:
            path: Path to the file

        Returns:
            str: File type string

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to access the file
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Getting file type for: {resolved_path}")

        if not resolved_path.exists():
            logger.error(f"File not found: {resolved_path}")
            raise FileNotFoundError(f"File not found: {resolved_path}")

        try:
            if resolved_path.is_file():
                file_type = "file"
            elif resolved_path.is_dir():
                file_type = "directory"
            elif resolved_path.is_symlink():
                file_type = "symlink"
            elif resolved_path.is_socket():
                file_type = "socket"
            elif resolved_path.is_fifo():
                file_type = "fifo"
            elif resolved_path.is_block_device():
                file_type = "block_device"
            elif resolved_path.is_char_device():
                file_type = "char_device"
            else:
                file_type = "unknown"

            logger.debug(f"File type for {resolved_path}: {file_type}")
            return file_type
        except Exception as e:
            logger.error(f"Error getting file type for {resolved_path}: {str(e)}")
            raise

    def _get_mime_type(self, path: str | Path) -> str | None:
        """
        Get the MIME type of a file.

        Args:
            path: Path to the file

        Returns:
            Optional[str]: MIME type string or None if not determinable

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to access the file
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        import mimetypes

        resolved_path = self._resolve_path(path)
        logger.debug(f"Getting MIME type for: {resolved_path}")

        if not resolved_path.exists():
            logger.error(f"File not found: {resolved_path}")
            raise FileNotFoundError(f"File not found: {resolved_path}")

        if not resolved_path.is_file():
            logger.warning(f"Path is not a file: {resolved_path}")
            return None

        try:
            mime_type, _ = mimetypes.guess_type(str(resolved_path))
            logger.debug(f"MIME type for {resolved_path}: {mime_type}")
            return mime_type
        except Exception as e:
            logger.error(f"Error determining MIME type for {resolved_path}: {str(e)}")
            raise

    def _is_path_writeable(self, path: str | Path) -> bool:
        """
        Check if a path is writeable.

        Args:
            path: Path to check

        Returns:
            bool: True if the path is writeable

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Checking if path is writeable: {resolved_path}")

        try:
            # If path exists, check if it's writeable
            if resolved_path.exists():
                return os.access(resolved_path, os.W_OK)

            # If path doesn't exist, check if parent directory is writeable
            parent_dir = resolved_path.parent
            while not parent_dir.exists() and parent_dir != parent_dir.parent:
                parent_dir = parent_dir.parent

            # If we found a parent that exists, check if it's writeable
            if parent_dir.exists():
                is_writeable = os.access(parent_dir, os.W_OK)
                logger.debug(
                    f"Parent directory {parent_dir} is writeable: {is_writeable}")
                return is_writeable

            logger.warning(f"Could not determine if {resolved_path} is writeable")
            return False
        except Exception as e:
            logger.error(f"Error checking if {resolved_path} is writeable: {str(e)}")
            return False

    def _is_file_locked(self, path: str | Path) -> bool:
        """
        Check if a file is locked by another process.

        Args:
            path: Path to the file

        Returns:
            bool: True if the file is locked

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Checking if file is locked: {resolved_path}")

        if not resolved_path.exists():
            logger.warning(f"File does not exist: {resolved_path}")
            return False

        if not resolved_path.is_file():
            logger.warning(f"Path is not a file: {resolved_path}")
            return False

        try:
            # Try to open the file for writing to see if it's locked
            with open(resolved_path, "a") as f:
                # On Windows, try to get an exclusive lock
                if os.name == "nt":
                    try:
                        import msvcrt
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        logger.debug(f"File {resolved_path} is locked (Windows)")
                        return True
                # On Unix, try to get an advisory lock
                else:
                    try:
                        import fcntl
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        logger.debug(f"File {resolved_path} is locked (Unix)")
                        return True

            logger.debug(f"File {resolved_path} is not locked")
            return False
        except PermissionError:
            # If we can't open the file due to permissions, consider it locked
            logger.debug(f"File {resolved_path} is locked (permission denied)")
            return True
        except Exception as e:
            logger.error(f"Error checking if {resolved_path} is locked: {str(e)}")
            # Consider it locked if we encounter an error
            return True

    def _find_files_by_content(
            self,
            directory: str | Path,
            text_pattern: str,
            recursive: bool = True,
    ) -> list[Path]:
        """
        Find files containing the given text pattern.

        Args:
            directory: Directory to search in
            text_pattern: Text pattern to search for
            recursive: Whether to search recursively

        Returns:
            list[Path]: List of paths to files containing the pattern

        Raises:
            NotADirectoryError: If the path is not a directory
            FileNotFoundError: If the directory doesn't exist
            PermissionError: If there's no permission to read the directory
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        import re

        resolved_dir = self._resolve_path(directory)
        logger.debug(
            f"Finding files containing '{text_pattern}' in {resolved_dir}, "
            f"recursive={recursive}"
        )

        if not resolved_dir.exists():
            logger.error(f"Directory does not exist: {resolved_dir}")
            raise FileNotFoundError(f"Directory does not exist: {resolved_dir}")

        if not resolved_dir.is_dir():
            logger.error(f"Path is not a directory: {resolved_dir}")
            raise NotADirectoryError(f"Path is not a directory: {resolved_dir}")

        try:
            # Compile the pattern for better performance
            pattern = re.compile(text_pattern)

            # Get all files to search
            if recursive:
                file_paths = [p for p in resolved_dir.glob("**/*") if p.is_file()]
            else:
                file_paths = [p for p in resolved_dir.glob("*") if p.is_file()]

            logger.debug(f"Found {len(file_paths)} files to search")

            # Search each file for the pattern
            matching_files = []
            for file_path in file_paths:
                try:
                    # Skip binary files
                    if self._is_binary_file(file_path):
                        continue

                    # Search the file content
                    with open(file_path, errors="ignore") as f:
                        content = f.read()
                        if pattern.search(content):
                            matching_files.append(file_path)
                            logger.debug(f"Found match in file: {file_path}")
                except Exception as e:
                    logger.warning(f"Error searching file {file_path}: {str(e)}")
                    continue

            logger.info(
                f"Found {len(matching_files)} files containing '{text_pattern}' "
                f"in {resolved_dir}"
            )
            return matching_files
        except Exception as e:
            logger.error(f"Error finding files by content in {resolved_dir}: {str(e)}")
            raise

    def _is_binary_file(self, file_path: Path) -> bool:
        """
        Check if a file is binary.

        Args:
            file_path: Path to the file

        Returns:
            bool: True if the file is binary
        """
        try:
            chunk_size = 1024
            with open(file_path, "rb") as f:
                chunk = f.read(chunk_size)
                if b"\0" in chunk:  # Null bytes indicate binary file
                    return True
                # Check for high concentration of non-ASCII chars
                non_ascii = sum(1 for byte in chunk if byte > 127)
                return non_ascii / len(chunk) > 0.3 if chunk else False
        except Exception:
            return False
