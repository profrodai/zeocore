# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/path_ops.py
# module: quack_core.core.fs.api.public.path_ops
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, file_ops.py (+3 more)
# exports: split_path, expand_user_vars, normalize_path, is_same_file, is_subdirectory
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import DataResult, PathResult

def split_path(path: Any) -> DataResult[list[str]]:
    return get_service().split_path(path)

def expand_user_vars(path: Any) -> DataResult[str]:
    return get_service().expand_user_vars(path)

def normalize_path(path: Any) -> PathResult:
    return get_service().normalize_path(path)

def is_same_file(path1: Any, path2: Any) -> DataResult[bool]:
    return get_service().is_same_file(path1, path2)

def is_subdirectory(child: Any, parent: Any) -> DataResult[bool]:
    return get_service().is_subdirectory(child, parent)