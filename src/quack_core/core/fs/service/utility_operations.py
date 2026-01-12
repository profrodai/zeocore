# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/utility_operations.py
# module: quack_core.core.fs.service.utility_operations
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_info_operations.py, file_operations.py (+5 more)
# exports: read_text, write_text, read_bytes, write_bytes, read_lines, write_lines, copy, move (+38 more)
# git_branch: feat/9-make-setup-work
# git_commit: ffd13f1b
# === QV-LLM:END ===


"""
Standalone wrappers that delegate to the singleton service.
Ensures consistent configuration and state.

DOCTRINE:
- These are CONVENIENCE WRAPPERS ONLY (secondary surface)
- They delegate to FileSystemService (primary surface)
- No logic, no normalization, no direct _ops/_internal imports
- May be removed in future without breaking core contracts

CATALOGUE NOTE:
The wrappers here represent the FULL secondary API surface.
See FileSystemService for the primary (canonical) API.
"""
from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import (
    DataResult, DirectoryInfoResult, FileInfoResult, FindResult,
    OperationResult, PathResult, ReadResult, WriteResult, BoolResult
)

# ==============================================================================
# FILE OPERATIONS
# ==============================================================================

def read_text(path: Any, encoding: str = "utf-8") -> ReadResult[str]:
    return get_service().read_text(path, encoding)

def write_text(path: Any, content: str, encoding: str = "utf-8", atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
    return get_service().write_text(path, content, encoding, atomic, calculate_checksum)

def read_bytes(path: Any) -> ReadResult[bytes]:
    return get_service().read_bytes(path)

# Legacy alias
read_binary = read_bytes

def write_bytes(path: Any, content: bytes, atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
    return get_service().write_bytes(path, content, atomic, calculate_checksum)

# Legacy alias
write_binary = write_bytes

def read_lines(path: Any, encoding: str = "utf-8") -> ReadResult[list[str]]:
    return get_service().read_lines(path, encoding)

def write_lines(path: Any, lines: list[str], encoding: str = "utf-8", atomic: bool = True, line_ending: str = "\n") -> WriteResult:
    return get_service().write_lines(path, lines, encoding, atomic, line_ending)

def copy(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    return get_service().copy(src, dst, overwrite)

def move(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    return get_service().move(src, dst, overwrite)

def delete(path: Any, missing_ok: bool = True) -> OperationResult:
    return get_service().delete(path, missing_ok)

# ==============================================================================
# DIRECTORY OPERATIONS
# ==============================================================================

def create_directory(path: Any, exist_ok: bool = True) -> OperationResult:
    return get_service().create_directory(path, exist_ok)

def list_directory(path: Any, pattern: str | None = None, recursive: bool = False, include_hidden: bool = False) -> DirectoryInfoResult:
    return get_service().list_directory(path, pattern, recursive, include_hidden)

def find_files(path: Any, pattern: str, recursive: bool = True, include_hidden: bool = False) -> FindResult:
    return get_service().find_files(path, pattern, recursive, include_hidden)

# ==============================================================================
# FILE INFO OPERATIONS
# ==============================================================================

def get_file_info(path: Any) -> FileInfoResult:
    return get_service().get_file_info(path)

# ==============================================================================
# STRUCTURED DATA OPERATIONS
# ==============================================================================

def read_yaml(path: Any) -> DataResult[dict]:
    return get_service().read_yaml(path)

def write_yaml(path: Any, data: dict, atomic: bool = True) -> WriteResult:
    return get_service().write_yaml(path, data, atomic)

def read_json(path: Any) -> DataResult[dict]:
    return get_service().read_json(path)

def write_json(path: Any, data: dict, atomic: bool = True, indent: int = 2) -> WriteResult:
    return get_service().write_json(path, data, atomic, indent)

# ==============================================================================
# PATH OPERATIONS
# ==============================================================================

def split_path(path: Any) -> DataResult[list[str]]:
    return get_service().split_path(path)

def join_path(*parts: Any) -> DataResult[str]:
    return get_service().join_path(*parts)

def normalize_path(path: Any) -> PathResult:
    return get_service().normalize_path(path)

def normalize_path_with_info(path: Any) -> PathResult:
    """
    Normalize path and return detailed info about it.
    Includes: absolute status, validity, existence.
    """
    return get_service().normalize_path_with_info(path)

def expand_user_vars(path: Any) -> DataResult[str]:
    return get_service().expand_user_vars(path)

def get_extension(path: Any) -> DataResult[str]:
    return get_service().get_extension(path)

def resolve_path(path: Any) -> PathResult:
    return get_service().resolve_path(path)

def is_same_file(path1: Any, path2: Any) -> DataResult[bool]:
    return get_service().is_same_file(path1, path2)

def is_subdirectory(child: Any, parent: Any) -> DataResult[bool]:
    return get_service().is_subdirectory(child, parent)

# ==============================================================================
# PATH VALIDATION OPERATIONS
# ==============================================================================

def path_exists(path: Any) -> BoolResult:
    return get_service().path_exists(path)

def is_valid_path(path: Any) -> BoolResult:
    return get_service().is_valid_path(path)

def is_safe_path(path: Any) -> BoolResult:
    return get_service().is_safe_path(path)

# ==============================================================================
# UTILITY OPERATIONS
# ==============================================================================

def ensure_directory(path: Any, exist_ok: bool = True) -> OperationResult:
    return get_service().ensure_directory(path, exist_ok)

def get_unique_filename(directory: Any, filename: str) -> DataResult[str]:
    return get_service().get_unique_filename(directory, filename)

def create_temp_file(suffix: str = ".txt", prefix: str = "quackcore_", directory: Any = None) -> DataResult[str]:
    return get_service().create_temp_file(suffix, prefix, directory)

def create_temp_directory(prefix: str = "quackcore_", suffix: str = "") -> DataResult[str]:
    return get_service().create_temp_directory(prefix, suffix)

def find_files_by_content(directory: Any, text_pattern: str, recursive: bool = True) -> DataResult[list[str]]:
    return get_service().find_files_by_content(directory, text_pattern, recursive)

def get_disk_usage(path: Any) -> DataResult[dict[str, int]]:
    return get_service().get_disk_usage(path)

def get_file_type(path: Any) -> DataResult[str]:
    return get_service().get_file_type(path)

def get_file_size_str(size_bytes: int) -> DataResult[str]:
    return get_service().get_file_size_str(size_bytes)

def get_file_timestamp(path: Any) -> DataResult[float]:
    return get_service().get_file_timestamp(path)

def get_mime_type(path: Any) -> DataResult[str | None]:
    return get_service().get_mime_type(path)

def compute_checksum(path: Any, algorithm: str = "sha256") -> DataResult[str]:
    return get_service().compute_checksum(path, algorithm)

def is_path_writeable(path: Any) -> DataResult[bool]:
    return get_service().is_path_writeable(path)

def is_file_locked(path: Any) -> DataResult[bool]:
    return get_service().is_file_locked(path)

def atomic_write(path: Any, content: str | bytes) -> WriteResult:
    return get_service().atomic_write(path, content)

# ==============================================================================
# SAFE OPERATION ALIASES (delegate to same methods - naming for clarity)
# ==============================================================================

def copy_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    """
    Alias for copy(). The 'safely' suffix indicates error handling via Results.
    All core operations are 'safe' (never raise), so this is semantic clarity only.
    """
    return get_service().copy(src, dst, overwrite)

def move_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    """
    Alias for move(). The 'safely' suffix indicates error handling via Results.
    All core operations are 'safe' (never raise), so this is semantic clarity only.
    """
    return get_service().move(src, dst, overwrite)

def delete_safely(path: Any, missing_ok: bool = True) -> OperationResult:
    """
    Alias for delete(). The 'safely' suffix indicates error handling via Results.
    All core operations are 'safe' (never raise), so this is semantic clarity only.
    """
    return get_service().delete(path, missing_ok)