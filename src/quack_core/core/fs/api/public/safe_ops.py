from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import OperationResult, WriteResult

def copy_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    return get_service().copy(src, dst, overwrite)

def move_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    return get_service().move(src, dst, overwrite)

def delete_safely(path: Any, missing_ok: bool = True) -> OperationResult:
    return get_service().delete(path, missing_ok)