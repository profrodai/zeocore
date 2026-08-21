"""
Standalone wrappers that delegate to the singleton service.
Ensures consistent configuration and state.
"""

from typing import Any

from zeo_core.core.fs.protocols import FsPathLike
from zeo_core.core.fs.results import (
    BoolResult,
    DataResult,
    DirectoryInfoResult,
    FileInfoResult,
    FindResult,
    OperationResult,
    PathResult,
    ReadResult,
    WriteResult,
)
from zeo_core.core.fs.service import get_service


def read_text(path: FsPathLike, encoding: str = "utf-8") -> ReadResult[str]:
    return get_service().read_text(path, encoding)


def write_text(
    path: FsPathLike,
    content: str,
    encoding: str = "utf-8",
    atomic: bool = True,
    calculate_checksum: bool = False,
    mode: int | None = None,
) -> WriteResult:
    return get_service().write_text(
        path, content, encoding, atomic, calculate_checksum, mode=mode
    )


def read_bytes(path: FsPathLike) -> ReadResult[bytes]:
    return get_service().read_bytes(path)


# Legacy alias
read_binary = read_bytes


def write_bytes(
    path: FsPathLike,
    content: bytes,
    atomic: bool = True,
    calculate_checksum: bool = False,
    mode: int | None = None,
) -> WriteResult:
    return get_service().write_bytes(
        path, content, atomic, calculate_checksum, mode=mode
    )


# Legacy alias
write_binary = write_bytes


def read_lines(path: FsPathLike, encoding: str = "utf-8") -> ReadResult[list[str]]:
    return get_service().read_lines(path, encoding)


def write_lines(
    path: FsPathLike,
    lines: list[str],
    encoding: str = "utf-8",
    atomic: bool = True,
    line_ending: str = "\n",
) -> WriteResult:
    return get_service().write_lines(path, lines, encoding, atomic, line_ending)


def copy(src: FsPathLike, dst: FsPathLike, overwrite: bool = False) -> WriteResult:
    return get_service().copy(src, dst, overwrite)


def move(src: FsPathLike, dst: FsPathLike, overwrite: bool = False) -> WriteResult:
    return get_service().move(src, dst, overwrite)


def delete(path: FsPathLike, missing_ok: bool = True) -> OperationResult:
    return get_service().delete(path, missing_ok)


def create_directory(path: FsPathLike, exist_ok: bool = True) -> OperationResult:
    return get_service().create_directory(path, exist_ok)


def list_directory(
    path: FsPathLike,
    pattern: str | None = None,
    recursive: bool = False,
    include_hidden: bool = False,
) -> DirectoryInfoResult:
    return get_service().list_directory(path, pattern, recursive, include_hidden)


def find_files(
    path: FsPathLike, pattern: str, recursive: bool = True, include_hidden: bool = False
) -> FindResult:
    return get_service().find_files(path, pattern, recursive, include_hidden)


def get_file_info(path: FsPathLike) -> FileInfoResult:
    return get_service().get_file_info(path)


def read_yaml(path: FsPathLike) -> DataResult[dict[str, Any]]:
    return get_service().read_yaml(path)


def write_yaml(
    path: FsPathLike,
    data: dict[str, Any],
    atomic: bool = True,
    mode: int | None = None,
) -> WriteResult:
    return get_service().write_yaml(path, data, atomic, mode=mode)


def read_json(path: FsPathLike) -> DataResult[dict[str, Any]]:
    return get_service().read_json(path)


def write_json(
    path: FsPathLike,
    data: dict[str, Any],
    atomic: bool = True,
    indent: int = 2,
    mode: int | None = None,
) -> WriteResult:
    return get_service().write_json(path, data, atomic, indent, mode=mode)


def split_path(path: FsPathLike) -> DataResult[list[str]]:
    return get_service().split_path(path)


def join_path(*parts: FsPathLike) -> DataResult[str]:
    return get_service().join_path(*parts)


def normalize_path(path: FsPathLike) -> PathResult:
    return get_service().normalize_path(path)


def normalize_path_with_info(path: FsPathLike) -> PathResult:
    return get_service().normalize_path_with_info(path)


def expand_user_vars(path: FsPathLike) -> DataResult[str]:
    return get_service().expand_user_vars(path)


def get_extension(path: FsPathLike) -> DataResult[str]:
    return get_service().get_extension(path)


def resolve_path(path: FsPathLike) -> PathResult:
    return get_service().resolve_path(path)


def is_same_file(path1: FsPathLike, path2: FsPathLike) -> DataResult[bool]:
    return get_service().is_same_file(path1, path2)


def is_subdirectory(child: FsPathLike, parent: FsPathLike) -> DataResult[bool]:
    return get_service().is_subdirectory(child, parent)


def path_exists(path: FsPathLike) -> BoolResult:
    return get_service().path_exists(path)


def is_valid_path(path: FsPathLike) -> BoolResult:
    return get_service().is_valid_path(path)


def is_safe_path(path: FsPathLike) -> BoolResult:
    return get_service().is_safe_path(path)


def get_path_info(path: FsPathLike) -> PathResult:
    return get_service().normalize_path_with_info(path)


def ensure_directory(path: FsPathLike, exist_ok: bool = True) -> OperationResult:
    return get_service().ensure_directory(path, exist_ok)


def get_unique_filename(directory: FsPathLike, filename: str) -> DataResult[str]:
    return get_service().get_unique_filename(directory, filename)


def create_temp_file(
    suffix: str = ".txt",
    prefix: str = "zeocore_",
    directory: FsPathLike | None = None,
) -> DataResult[str]:
    return get_service().create_temp_file(suffix, prefix, directory)


def create_temp_directory(
    prefix: str = "zeocore_", suffix: str = ""
) -> DataResult[str]:
    return get_service().create_temp_directory(prefix, suffix)


def find_files_by_content(
    directory: FsPathLike, text_pattern: str, recursive: bool = True
) -> DataResult[list[str]]:
    return get_service().find_files_by_content(directory, text_pattern, recursive)


def get_disk_usage(path: FsPathLike) -> DataResult[dict[str, int]]:
    return get_service().get_disk_usage(path)


def get_file_type(path: FsPathLike) -> DataResult[str]:
    return get_service().get_file_type(path)


def get_file_size_str(size_bytes: int) -> DataResult[str]:
    return get_service().get_file_size_str(size_bytes)


def get_file_timestamp(path: FsPathLike) -> DataResult[float]:
    return get_service().get_file_timestamp(path)


def get_mime_type(path: FsPathLike) -> DataResult[str | None]:
    return get_service().get_mime_type(path)


def compute_checksum(path: FsPathLike, algorithm: str = "sha256") -> DataResult[str]:
    return get_service().compute_checksum(path, algorithm)


def is_path_writeable(path: FsPathLike) -> DataResult[bool]:
    return get_service().is_path_writeable(path)


def is_file_locked(path: FsPathLike) -> DataResult[bool]:
    return get_service().is_file_locked(path)


def atomic_write(path: FsPathLike, content: str | bytes) -> WriteResult:
    return get_service().atomic_write(path, content)


def copy_safely(
    src: FsPathLike, dst: FsPathLike, overwrite: bool = False
) -> WriteResult:
    return get_service().copy(src, dst, overwrite)


def move_safely(
    src: FsPathLike, dst: FsPathLike, overwrite: bool = False
) -> WriteResult:
    return get_service().move(src, dst, overwrite)


def delete_safely(path: FsPathLike, missing_ok: bool = True) -> OperationResult:
    return get_service().delete(path, missing_ok)
