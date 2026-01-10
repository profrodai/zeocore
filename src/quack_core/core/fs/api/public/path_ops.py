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