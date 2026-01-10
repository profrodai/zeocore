# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/file_ops.py
# module: quack_core.core.fs.api.public.file_ops
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, path_ops.py (+3 more)
# exports: atomic_write, ensure_directory, get_unique_filename, find_files_by_content
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import WriteResult, OperationResult, DataResult

def atomic_write(path: Any, content: str | bytes) -> WriteResult:
    return get_service().atomic_write(path, content)

def ensure_directory(path: Any, exist_ok: bool = True) -> OperationResult:
    return get_service().ensure_directory(path, exist_ok)

def get_unique_filename(directory: Any, filename: str) -> DataResult[str]:
    return get_service().get_unique_filename(directory, filename)

def find_files_by_content(directory: Any, text_pattern: str, recursive: bool = True) -> DataResult[list[str]]:
    return get_service().find_files_by_content(directory, text_pattern, recursive)