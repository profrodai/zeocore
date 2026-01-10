# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/safe_ops.py
# module: quack_core.core.fs.api.public.safe_ops
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, file_ops.py (+3 more)
# exports: copy_safely, move_safely, delete_safely
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import OperationResult, WriteResult

def copy_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    return get_service().copy(src, dst, overwrite)

def move_safely(src: Any, dst: Any, overwrite: bool = False) -> WriteResult:
    return get_service().move(src, dst, overwrite)

def delete_safely(path: Any, missing_ok: bool = True) -> OperationResult:
    return get_service().delete(path, missing_ok)