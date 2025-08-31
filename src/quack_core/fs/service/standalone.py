# quack-core/src/quack-core/fs/service/standalone.py
"""
Standalone utility functions that are exposed at the package level.

These functions provide direct access to common filesystem operations
without having to create a service instance.
"""

from pathlib import Path
from typing import TypeVar

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

# Import the complete FileSystemService with all mixins
from quack_core.fs.service.full_class import FileSystemService

T = TypeVar("T")  # Generic type for flexible typing

# Create a service instance specifically for standalone functions
_service = FileSystemService()


# File operations


def read_text(path: str | Path | DataResult | OperationResult,
              encoding: str = "utf-8") -> ReadResult[str]:
    """
    Read text from a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)
        encoding: Text encoding.

    Returns:
        ReadResult with the file content as text.
    """
    return _service.read_text(path, encoding)


def write_text(
        path: str | Path | DataResult | OperationResult,
        content: str,
        encoding: str = "utf-8",
        atomic: bool = True,
) -> WriteResult:
    """
    Write text to a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)
        content: Content to write.
        encoding: Text encoding.
        atomic: Whether to use atomic writing.

    Returns:
        WriteResult with operation status.
    """
    return _service.write_text(path, content, encoding, atomic)


def read_binary(path: str | Path | DataResult | OperationResult) -> ReadResult[bytes]:
    """
    Read binary data from a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        ReadResult with the file content as bytes.
    """
    return _service.read_binary(path)


def write_binary(
        path: str | Path | DataResult | OperationResult,
        content: bytes,
        atomic: bool = True,
) -> WriteResult:
    """
    Write binary data to a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)
        content: Content to write.
        atomic: Whether to use atomic writing.

    Returns:
        WriteResult with operation status.
    """
    return _service.write_binary(path, content, atomic)


def read_lines(path: str | Path | DataResult | OperationResult,
               encoding: str = "utf-8") -> ReadResult[list[str]]:
    """
    Read lines from a text file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)
        encoding: Text encoding.

    Returns:
        ReadResult with the file content as a list of lines.
    """
    return _service.read_lines(path, encoding)


def write_lines(
        path: str | Path | DataResult | OperationResult,
        lines: list[str],
        encoding: str = "utf-8",
        atomic: bool = True,
        line_ending: str = "\n",
) -> WriteResult:
    """
    Write lines to a text file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)
        lines: Lines to write.
        encoding: Text encoding.
        atomic: Whether to write the file atomically.
        line_ending: The line ending to use.

    Returns:
        WriteResult with the outcome of the operation.
    """
    return _service.write_lines(path, lines, encoding, atomic, line_ending)


def create_directory(path: str | Path | DataResult | OperationResult,
                     exist_ok: bool = True) -> OperationResult:
    """
    Create a directory if it doesn't exist.

    Args:
        path: Directory path to create (string, Path, DataResult, or OperationResult)
        exist_ok: If False, raise an error when the directory exists.

    Returns:
        OperationResult indicating whether the directory was created or already exists.
    """
    return _service.create_directory(path, exist_ok)


def read_yaml(path: str | Path | DataResult | OperationResult) -> DataResult[dict]:
    """
    Read a YAML file and parse its contents.

    Args:
        path: Path to the YAML file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult containing the parsed YAML data.
    """
    return _service.read_yaml(path)


def write_yaml(
        path: str | Path | DataResult | OperationResult,
        data: dict,
        atomic: bool = True,
) -> WriteResult:
    """
    Write data to a YAML file.

    Args:
        path: Path to the YAML file (string, Path, DataResult, or OperationResult)
        data: Data to write.
        atomic: Whether to use atomic writing.

    Returns:
        WriteResult with operation status.
    """
    return _service.write_yaml(path, data, atomic)


def read_json(path: str | Path | DataResult | OperationResult) -> DataResult[dict]:
    """
    Read a JSON file and parse its contents.

    Args:
        path: Path to the JSON file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with parsed JSON data.
    """
    return _service.read_json(path)


def write_json(
        path: str | Path | DataResult | OperationResult,
        data: dict,
        atomic: bool = True,
        indent: int = 2,
) -> WriteResult:
    """
    Write data to a JSON file.

    Args:
        path: Path to the JSON file (string, Path, DataResult, or OperationResult)
        data: Data to write.
        atomic: Whether to use atomic writing.
        indent: Number of spaces to indent.

    Returns:
        WriteResult with operation status.
    """
    return _service.write_json(path, data, atomic, indent)


def get_file_info(path: str | Path | DataResult | OperationResult) -> FileInfoResult:
    """
    Get information about a file or directory.

    Args:
        path: Path to get information about (string, Path, DataResult, or OperationResult)

    Returns:
        FileInfoResult with file information.
    """
    return _service.get_file_info(path)


def list_directory(
        path: str | Path | DataResult | OperationResult,
        pattern: str | None = None,
        include_hidden: bool = False,
) -> DirectoryInfoResult:
    """
    List contents of a directory.

    Args:
        path: Directory path to list (string, Path, DataResult, or OperationResult)
        pattern: Pattern to match files against.
        include_hidden: Whether to include hidden files.

    Returns:
        DirectoryInfoResult with directory contents.
    """
    return _service.list_directory(path, pattern, include_hidden)


def find_files(
        path: str | Path | DataResult | OperationResult,
        pattern: str,
        recursive: bool = True,
        include_hidden: bool = False,
) -> FindResult:
    """
    Find files matching a pattern.

    Args:
        path: Directory to search (string, Path, DataResult, or OperationResult)
        pattern: Pattern to match files against.
        recursive: Whether to search recursively.
        include_hidden: Whether to include hidden files.

    Returns:
        FindResult with the matching files.
    """
    return _service.find_files(path, pattern, recursive, include_hidden)


def copy(src: str | Path | DataResult | OperationResult,
         dst: str | Path | DataResult | OperationResult,
         overwrite: bool = False) -> WriteResult:
    """
    Copy a file or directory.

    Args:
        src: Source path (string, Path, DataResult, or OperationResult)
        dst: Destination path (string, Path, DataResult, or OperationResult)
        overwrite: Whether to overwrite if the destination exists.

    Returns:
        WriteResult with operation status.
    """
    return _service.copy(src, dst, overwrite)


def move(src: str | Path | DataResult | OperationResult,
         dst: str | Path | DataResult | OperationResult,
         overwrite: bool = False) -> WriteResult:
    """
    Move a file or directory.

    Args:
        src: Source path (string, Path, DataResult, or OperationResult)
        dst: Destination path (string, Path, DataResult, or OperationResult)
        overwrite: Whether to overwrite if the destination exists.

    Returns:
        WriteResult with operation status.
    """
    return _service.move(src, dst, overwrite)


def delete(path: str | Path | DataResult | OperationResult,
           missing_ok: bool = True) -> OperationResult:
    """
    Delete a file or directory.

    Args:
        path: Path to delete (string, Path, DataResult, or OperationResult)
        missing_ok: Whether to ignore if the path doesn't exist.

    Returns:
        OperationResult with operation status.
    """
    return _service.delete(path, missing_ok)


def split_path(path: str | Path | DataResult | OperationResult) -> DataResult[
    list[str]]:
    """
    Split a path into its components.

    Args:
        path: Path to split (string, Path, DataResult, or OperationResult)

    Returns:
        List of path components.
    """
    return _service.split_path(path)


def join_path(*parts: str | Path | DataResult | OperationResult) -> DataResult[str]:
    """
    Join path components.

    Args:
        *parts: Path parts to join. Each part can be a string, Path, DataResult, or OperationResult.

    Returns:
        Joined path as string.
    """
    return _service.join_path(*parts)


# Updated functions from standalone.py that work with PathValidationMixin


def path_exists(path: str | Path | DataResult | OperationResult) -> DataResult[bool]:
    """
    Check if a path exists using the FileSystemService.

    Args:
        path: The file or directory path to check (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with boolean indicating if path exists
    """
    return _service.path_exists(path)


def normalize_path_with_info(
        path: str | Path | DataResult | OperationResult) -> PathResult:
    """
    Normalize a path and return detailed information.

    Args:
        path: The path to normalize (string, Path, DataResult, or OperationResult)

    Returns:
        PathResult containing the normalized path and status information.
    """
    return _service.normalize_path_with_info(path)


def normalize_path(path: str | Path | DataResult | OperationResult) -> PathResult:
    """
    Normalize a path.

    Args:
        path: The path to normalize (string, Path, DataResult, or OperationResult)

    Returns:
        PathResult containing the normalized path and status information.
    """
    return _service.normalize_path(path)


def get_path_info(path: str | Path | DataResult | OperationResult) -> PathResult:
    """
    Get information about a path's validity and format.

    Args:
        path: The path to check (string, Path, DataResult, or OperationResult)

    Returns:
        PathResult containing validation results.
    """
    return _service.get_path_info(path)


def is_valid_path(path: str | Path | DataResult | OperationResult) -> DataResult[bool]:
    """
    Check if a path has valid syntax.

    Args:
        path: The path to check (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with boolean indicating if the path has valid syntax.
    """
    return _service.is_valid_path(path)


def get_extension(path: str | Path | DataResult | OperationResult) -> DataResult[str]:
    """
    Get the file extension from a path.

    Args:
        path: Path to get extension from (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with file extension without the dot
    """
    return _service.get_extension(path)


def expand_user_vars(path: str | Path | DataResult | OperationResult) -> DataResult[
    str]:
    """
    Expand user variables and environment variables in a path.

    Args:
        path: Path with variables to expand (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with expanded path as string
    """
    return _service.expand_user_vars(path)


def resolve_path(path: str | Path | DataResult | OperationResult) -> PathResult:
    """
    Resolve a path relative to the service's base_dir and return as a string.

    This is a public, safe wrapper around _resolve_path that conforms to
    the DataResult structure used throughout quack_core.

    Args:
        path: Input path (absolute or relative) (string, Path, DataResult, or OperationResult)

    Returns:
        PathResult with the fully resolved, absolute path as a string.
    """
    return _service.resolve_path(path)


def get_mime_type(path: str | Path | DataResult | OperationResult) -> DataResult[
                                                                          str] | None:
    """
    Get the MIME type of a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        MIME type string or None if not determinable
    """
    return _service.get_mime_type(path)


def create_temp_directory(prefix: str = "quackcore_", suffix: str = "") -> DataResult[
    str]:
    """
    Create a temporary directory.

    Args:
        prefix: Prefix for the temporary directory name
        suffix: Suffix for the temporary directory name

    Returns:
        DataResult with path to the created temporary directory
    """
    return _service.create_temp_directory(prefix, suffix)


def extract_path_from_result(
        path_or_result: str | Path | DataResult | OperationResult) -> DataResult[str]:
    """
    Extract a path string from any result object or path-like object.

    Args:
        path_or_result: Any object that might contain a path (string, Path, DataResult,
                        OperationResult, PathResult, or any path-like object)

    Returns:
        The extracted path as a string
    """
    if hasattr(path_or_result, "path") and path_or_result.path is not None:
        path = path_or_result.path
    elif hasattr(path_or_result, "data") and path_or_result.data is not None:
        path = path_or_result.data
    else:
        path = str(path_or_result)

    return DataResult(
        success=True,
        path=Path(path),
        data=str(path),
        format="path",
        message="Successfully extracted path"
    )


# New utility functions added in the refactoring


def atomic_write(path: str | Path | DataResult | OperationResult,
                 content: str | bytes) -> WriteResult:
    """
    Write content to a file atomically using a temporary file.

    Args:
        path: Destination file path (string, Path, DataResult, or OperationResult)
        content: Content to write. Can be either string or bytes.

    Returns:
        WriteResult with path to the written file.
    """
    return _service.atomic_write(path, content)


def get_disk_usage(path: str | Path | DataResult | OperationResult) -> DataResult[
    dict[str, int]]:
    """
    Get disk usage information for the given path.

    Args:
        path: Path to get disk usage for (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with dictionary containing total, used, and free space in bytes
    """
    return _service.get_disk_usage(path)


def get_file_type(path: str | Path | DataResult | OperationResult) -> DataResult[str]:
    """
    Get the type of a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with file type string
    """
    return _service.get_file_type(path)


def get_file_size_str(size_bytes: int) -> DataResult[str]:
    """
    Convert file size in bytes to a human-readable string.

    Args:
        size_bytes: File size in bytes

    Returns:
        DataResult with human-readable file size (e.g., "2.5 MB")
    """
    return _service.get_file_size_str(size_bytes)


def get_file_timestamp(path: str | Path | DataResult | OperationResult) -> DataResult[
    float]:
    """
    Get the latest timestamp (modification time) for a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with timestamp as float
    """
    return _service.get_file_timestamp(path)


def compute_checksum(
        path: str | Path | DataResult | OperationResult, algorithm: str = "sha256"
) -> DataResult[str]:
    """
    Compute the checksum of a file.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)
        algorithm: Hash algorithm to use (default: "sha256")

    Returns:
        DataResult with hexadecimal string representing the checksum
    """
    return _service.compute_checksum(path, algorithm)


def create_temp_file(
        suffix: str = ".txt", prefix: str = "quackcore_",
        directory: str | Path | DataResult | OperationResult | None = None
) -> DataResult[str]:
    """
    Create a temporary file.

    Args:
        suffix: File suffix (e.g., ".txt")
        prefix: File prefix
        directory: Directory to create the file in (string, Path, DataResult,
                  or OperationResult, default: system temp dir)

    Returns:
        DataResult with path to the created temporary file
    """
    return _service.create_temp_file(suffix, prefix, directory)


def ensure_directory(
        path: str | Path | DataResult | OperationResult, exist_ok: bool = True
) -> OperationResult:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists (string, Path, DataResult, or OperationResult)
        exist_ok: If False, raise an error when directory exists

    Returns:
        OperationResult with operation status
    """
    return _service.ensure_directory(path, exist_ok)


def get_unique_filename(
        directory: str | Path | DataResult | OperationResult, filename: str
) -> DataResult[str]:
    """
    Generate a unique filename in the given directory.

    Args:
        directory: Directory path (string, Path, DataResult, or OperationResult)
        filename: Base filename

    Returns:
        DataResult with the unique filename
    """
    return _service.get_unique_filename(directory, filename)


def find_files_by_content(
        directory: str | Path | DataResult | OperationResult, text_pattern: str,
        recursive: bool = True
) -> DataResult[list[str]]:
    """
    Find files containing the given text pattern.

    Args:
        directory: Directory to search in (string, Path, DataResult, or OperationResult)
        text_pattern: Text pattern to search for
        recursive: Whether to search recursively

    Returns:
        DataResult with list of paths to files containing the pattern
    """
    return _service.find_files_by_content(directory, text_pattern, recursive)


def is_path_writeable(path: str | Path | DataResult | OperationResult) -> DataResult[
    bool]:
    """
    Check if a path is writeable.

    Args:
        path: Path to check (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with True if the path is writeable
    """
    return _service.is_path_writeable(path)


def is_file_locked(path: str | Path | DataResult | OperationResult) -> DataResult[bool]:
    """
    Check if a file is locked by another process.

    Args:
        path: Path to the file (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with True if the file is locked
    """
    return _service.is_file_locked(path)


def is_same_file(
        path1: str | Path | DataResult | OperationResult,
        path2: str | Path | DataResult | OperationResult
) -> DataResult[bool]:
    """
    Check if two paths refer to the same file.

    Args:
        path1: First path (string, Path, DataResult, or OperationResult)
        path2: Second path (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with True if paths refer to the same file
    """
    return _service.is_same_file(path1, path2)


def is_subdirectory(
        child: str | Path | DataResult | OperationResult,
        parent: str | Path | DataResult | OperationResult
) -> DataResult[bool]:
    """
    Check if a path is a subdirectory of another path.

    Args:
        child: Potential child path (string, Path, DataResult, or OperationResult)
        parent: Potential parent path (string, Path, DataResult, or OperationResult)

    Returns:
        DataResult with True if child is a subdirectory of parent
    """
    return _service.is_subdirectory(child, parent)
