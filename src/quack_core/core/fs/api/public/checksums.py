# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/checksums.py
# module: quack_core.core.fs.api.public.checksums
# role: api
# neighbors: __init__.py, coerce.py, disk.py, file_info.py, file_ops.py, path_ops.py (+3 more)
# exports: compute_checksum
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import DataResult

def compute_checksum(path: Any, algorithm: str = "sha256") -> DataResult[str]:
    return get_service().compute_checksum(path, algorithm)