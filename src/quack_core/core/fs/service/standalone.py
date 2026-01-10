# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/standalone.py
# module: quack_core.core.fs.service.standalone
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+4 more)
# exports: read_text, write_text, read_binary, write_binary, read_lines, write_lines, copy, move (+44 more)
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

"""
Standalone wrappers that delegate to the singleton service.
Ensures consistent configuration and state.
"""
from typing import Any
from pathlib import Path
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import (
    DataResult, DirectoryInfoResult, FileInfoResult, FindResult,
    OperationResult, PathResult, ReadResult, WriteResult
)

def read_text(path: Any, encoding: str = "utf-8") -> ReadResult[str]:
    return get_service().read_text(path, encoding)

def write_text(path: Any, content: str, encoding: str = "utf-8", atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
    return get_service().write_text(path, content, encoding, atomic, calculate_checksum)

def read_binary(path: Any) -> ReadResult[bytes]:
    return get_service().read_binary(path)

def write_binary(path: Any, content: bytes, atomic: bool = True, calculate_checksum: bool = False) -> WriteResult:
    return get_service().write_binary(path, content, atomic, calculate_checksum)

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

def create_directory(path: Any, exist_ok: bool = True) -> OperationResult:
    return get_service().create_directory(path, exist_ok)

def list_directory(path: Any, pattern: str | None = None, include_hidden: bool = False) -> DirectoryInfoResult:
    return get_service().list_directory(path, pattern, include_hidden)

def find_files(path: Any, pattern: str, recursive: bool = True, include_hidden: bool = False) -> FindResult:
    return get_service().find_files(path, pattern, recursive, include_hidden)

def get_file_info(path: Any) -> FileInfoResult:
    return get_service().get_file_info(path)

def read_yaml(path: Any) -> DataResult[dict]:
    return get_service().read_yaml(path)

def write_yaml(path: Any, data: dict, atomic: bool = True) -> WriteResult:
    return get_service().write_yaml(path, data, atomic)

def read_json(path: Any) -> DataResult[dict]:
    return get_service().read_json(path)

def write_json(path: Any, data: dict, atomic: bool = True, indent: int = 2) -> WriteResult:
    return get_service().write_json(path, data, atomic, indent)

def split_path(path: Any) -> DataResult[list[str]]:
    return get_service().split_path(path)

def join_path(*parts: Any) -> DataResult[str]:
    return get_service().join_path(*parts)

def normalize_path(path: Any) -> PathResult:
    return get_service().normalize_path(path)

def normalize_path_with_info(path: Any) -> PathResult:
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

def path_exists(path: Any) -> DataResult[bool]:
    return get_service().path_exists(path)

def is_valid_path(path: Any) -> DataResult[bool]:
    return get_service().is_valid_path(path)

def get_path_info(path: Any) -> PathResult:
    return get_service().get_path_info(path)

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

# Wrappers for path util functions that were in api/public
def extract_path_from_result(path_or_result: Any) -> DataResult[str]:
    # This logic belongs in the service/standalone layer as it deals with result objects
    try:
        from quack_core.core.fs._internal.path_utils import _extract_path_str
        path_str = _extract_path_str(path_or_result)
        return DataResult(success=True, path=Path(path_str), data=path_str, format="path", message="Successfully extracted path")
    except Exception as e:
        return DataResult(success=False, path=None, data=str(path_or_result), format="path", error=str(e), message="Failed to extract path")

def extract_path_str(obj: Any) -> str:
    from quack_core.core.fs._internal.path_utils import _extract_path_str
    return _extract_path_str(obj)

def safe_path_str(obj: Any, default: str | None = None) -> str | None:
    from quack_core.core.fs._internal.path_utils import _safe_path_str
    return _safe_path_str(obj, default)

def coerce_path(obj: Any) -> Path:
    from quack_core.core.fs._internal.path_utils import _normalize_path_param
    return _normalize_path_param(obj)

def coerce_path_str(obj: Any) -> str:
    from quack_core.core.fs._internal.path_utils import _extract_path_str
    return _extract_path_str(obj)

def coerce_path_result(obj: Any) -> DataResult[str]:
    try:
        from quack_core.core.fs._internal.path_utils import _extract_path_str
        p_str = _extract_path_str(obj)
        return DataResult(success=True, path=Path(p_str), data=p_str, format="path", message="Successfully coerced path")
    except Exception as e:
        return DataResult(success=False, path=None, data=str(obj), format="path", error=str(e), message="Failed to coerce path input")

def copy_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    return get_service().copy(src, dst, overwrite)

def move_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    return get_service().move(src, dst, overwrite)

def delete_safely(path: Any, missing_ok: bool = True) -> OperationResult:
    return get_service().delete(path, missing_ok)