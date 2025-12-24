# quack-core/src/quack_core/fs/__init__.py
"""
Filesystem package for quack_core.

This package provides a robust filesystem abstraction with proper error handling,
standardized result objects, and comprehensive file operation capabilities.
"""

# Import utility functions directly to make them available at package level
from quack_core.fs.api.public import (
    atomic_write,
    compute_checksum,
    copy_safely,
    create_temp_directory,
    create_temp_file,
    delete_safely,
    ensure_directory,
    expand_user_vars,
    find_files_by_content,
    get_disk_usage,
    get_file_size_str,
    get_file_timestamp,
    get_file_type,
    get_mime_type,
    get_unique_filename,
    is_file_locked,
    is_path_writeable,
    is_same_file,
    is_subdirectory,
    move_safely,
    normalize_path,
    split_path,
)

# Import core result classes first since many modules depend on them
from quack_core.fs.results import (
    DataResult,
    DirectoryInfoResult,
    FileInfoResult,
    FindResult,
    OperationResult,
    PathResult,
    ReadResult,
    WriteResult,
)


# Define path validation functions for backward compatibility
def get_path_info(path):
    """Get information about a path's validity and format."""
    # Import here to avoid circular imports
    from quack_core.fs.service import service

    return service.get_path_info(path)


def is_valid_path(path):
    """Check if a path has valid syntax."""
    # Import here to avoid circular imports
    from quack_core.fs.service import service

    return service.is_valid_path(path)


def normalize_path_with_info(path):
    """Normalize a path and return detailed information."""
    # Import here to avoid circular imports
    from quack_core.fs.service import service

    return service._normalize_path_with_info(path)


# Create service lazily to avoid circular imports
def _get_service():
    """Get the global filesystem service instance."""
    # Import here to avoid circular imports
    from quack_core.fs.service import service

    return service


# Expose service functions through getters to avoid circular imports
def get_file_info(path):
    """Get information about a file or directory."""
    return _get_service().get_file_info(path)


def create_directory(path, exist_ok=True):
    """Create a directory if it doesn't exist."""
    return _get_service().create_directory(path, exist_ok)


def read_yaml(path):
    """Read a YAML file and parse its contents."""
    return _get_service().read_yaml(path)


def read_text(path, encoding="utf-8"):
    """Read text from a file."""
    return _get_service().read_text(path, encoding)


def write_text(path, content, encoding="utf-8", atomic=True):
    """Write text to a file."""
    return _get_service().write_text(path, content, encoding, atomic)


def read_binary(path):
    """Read binary data from a file."""
    return _get_service().read_binary(path)


def write_binary(path, content, atomic=True):
    """Write binary data to a file."""
    return _get_service().write_binary(path, content, atomic)


def write_yaml(path, data, atomic=True):
    """Write data to a YAML file."""
    return _get_service().write_yaml(path, data, atomic)


def read_json(path):
    """Read a JSON file and parse its contents."""
    return _get_service().read_json(path)


def write_json(path, data, atomic=True, indent=2):
    """Write data to a JSON file."""
    return _get_service().write_json(path, data, atomic, indent)


def list_directory(path, pattern=None, include_hidden=False):
    """List contents of a directory."""
    return _get_service().list_directory(path, pattern, include_hidden)


def find_files(path, pattern, recursive=True, include_hidden=False):
    """Find files matching a pattern."""
    return _get_service().find_files(path, pattern, recursive, include_hidden)


def copy(src, dst, overwrite=False):
    """Copy a file or directory."""
    return _get_service().copy(src, dst, overwrite)


def move(src, dst, overwrite=False):
    """Move a file or directory."""
    return _get_service().move(src, dst, overwrite)


def delete(path, missing_ok=True):
    """Delete a file or directory."""
    return _get_service().delete(path, missing_ok)


# For explicit use when needed
from quack_core.fs._operations import FileSystemOperations
from quack_core.fs.service import FileSystemService, create_service, service

__all__ = [
    # Main service class
    "FileSystemService",
    # Factory function
    "create_service",
    # Global instance
    "service",
    # Core _operations class
    "FileSystemOperations",
    # Result classes
    "OperationResult",
    "ReadResult",
    "WriteResult",
    "FileInfoResult",
    "DirectoryInfoResult",
    "FindResult",
    "DataResult",
    "PathResult",
    # Service utility functions
    "get_file_info",
    "create_directory",
    "read_yaml",
    "read_text",
    "write_text",
    "read_binary",
    "write_binary",
    "write_yaml",
    "read_json",
    "write_json",
    "list_directory",
    "find_files",
    "copy",
    "move",
    "delete",
    # Compatibility methods
    "get_path_info",
    "is_valid_path",
    "normalize_path_with_info",
    # Utility functions
    "atomic_write",
    "compute_checksum",
    "copy_safely",
    "create_temp_directory",
    "create_temp_file",
    "delete_safely",
    "ensure_directory",
    "expand_user_vars",
    "find_files_by_content",
    "get_disk_usage",
    "get_file_size_str",
    "get_file_timestamp",
    "get_file_type",
    "get_mime_type",
    "get_unique_filename",
    "is_file_locked",
    "is_path_writeable",
    "is_same_file",
    "is_subdirectory",
    "move_safely",
    "normalize_path",
    "split_path",
]
