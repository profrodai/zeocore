# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/temp.py
# module: quack_core.core.fs.api.public.temp
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, file_ops.py (+3 more)
# exports: create_temp_directory, create_temp_file
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import DataResult

def create_temp_directory(prefix: str = "quackcore_", suffix: str = "") -> DataResult[str]:
    return get_service().create_temp_directory(prefix, suffix)

def create_temp_file(suffix: str = ".txt", prefix: str = "quackcore_", directory: Any = None) -> DataResult[str]:
    return get_service().create_temp_file(suffix, prefix, directory)