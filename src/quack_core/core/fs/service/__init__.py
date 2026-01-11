# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/__init__.py
# module: quack_core.core.fs.service.__init__
# role: service
# neighbors: base.py, directory_operations.py, factory.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: FileSystemService, create_service, get_service
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

from functools import lru_cache
from typing import TypeVar

from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.fs.service.factory import create_service

T = TypeVar("T")

@lru_cache(maxsize=1)
def get_service() -> FileSystemService:
    """Lazy-loaded singleton."""
    return create_service()

__all__ = [
    "FileSystemService",
    "create_service",
    "get_service",
]