# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/disk.py
# module: quack_core.core.fs.api.public.disk
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, file_info.py, file_ops.py, path_ops.py (+3 more)
# exports: get_disk_usage, is_path_writeable
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import DataResult

def get_disk_usage(path: Any) -> DataResult[dict[str, int]]:
    return get_service().get_disk_usage(path)

def is_path_writeable(path: Any) -> DataResult[bool]:
    return get_service().is_path_writeable(path)