# quack-core/src/quack-core/fs/service/__init__.py
"""
FileSystemService provides a high-level interface for filesystem operations.

This module exports the FileSystemService class and provides utility functions
for common filesystem operations without requiring a service instance.
"""

from typing import TypeVar, cast

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

# Import the factory function but defer creating the service
from quack_core.fs.service.factory import create_service

# Import the complete FileSystemService with all mixins for type hints
from quack_core.fs.service.full_class import FileSystemService

# Create a global instance but initialize it lazily
_service = None


def get_service() -> FileSystemService:
    """
    Get the global filesystem service instance.

    This function initializes the service on first access to avoid circular imports.

    Returns:
        FileSystemService: The global filesystem service instance
    """
    global _service
    if _service is None:
        _service = create_service()
    return cast(FileSystemService, _service)


# Access the service through a property to ensure lazy initialization
service = property(get_service)

# Import all standalone functions
from quack_core.fs.service.standalone import (
    # Utility operations
    atomic_write,
    compute_checksum,
    # File management
    copy,
    # Directory operations
    create_directory,
    create_temp_directory,
    create_temp_file,
    delete,
    ensure_directory,
    expand_user_vars,
    extract_path_from_result,
    find_files,
    find_files_by_content,
    get_disk_usage,
    get_extension,
    # File info
    get_file_info,
    get_file_size_str,
    get_file_timestamp,
    get_file_type,
    get_mime_type,
    get_path_info,
    get_unique_filename,
    is_file_locked,
    is_path_writeable,
    is_same_file,
    is_subdirectory,
    is_valid_path,
    join_path,
    list_directory,
    move,
    normalize_path,
    normalize_path_with_info,
    path_exists,
    read_binary,
    read_json,
    read_lines,
    # Core file operations
    read_text,
    # Structured data
    read_yaml,
    resolve_path,
    # Path operations
    split_path,
    write_binary,
    write_json,
    write_lines,
    write_text,
    write_yaml,
)

# Type variables
T = TypeVar("T")  # Generic type for flexible typing

__all__ = [
    # Main classes
    "FileSystemService",
    "create_service",
    "service",
    "get_service",

    # Core file operations
    "read_text",
    "write_text",
    "read_binary",
    "write_binary",
    "read_lines",
    "write_lines",

    # Directory operations
    "create_directory",
    "list_directory",
    "find_files",

    # File management
    "copy",
    "move",
    "delete",

    # Structured data
    "read_yaml",
    "write_yaml",
    "read_json",
    "write_json",

    # File info
    "get_file_info",

    # Path operations
    "split_path",
    "join_path",
    "path_exists",
    "normalize_path_with_info",
    "normalize_path",
    "get_path_info",
    "is_valid_path",
    "get_extension",
    "expand_user_vars",
    "resolve_path",

    # Utility operations
    "atomic_write",
    "get_disk_usage",
    "get_file_type",
    "get_file_size_str",
    "get_mime_type",
    "get_file_timestamp",
    "compute_checksum",
    "create_temp_file",
    "create_temp_directory",
    "ensure_directory",
    "get_unique_filename",
    "find_files_by_content",
    "is_path_writeable",
    "is_file_locked",
    "is_same_file",
    "is_subdirectory",
    "extract_path_from_result",

    # Result classes for type hints
    "OperationResult",
    "ReadResult",
    "WriteResult",
    "FileInfoResult",
    "DirectoryInfoResult",
    "FindResult",
    "DataResult",
    "PathResult",

    # Type variables
    "T",
]
