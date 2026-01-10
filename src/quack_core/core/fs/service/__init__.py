from functools import lru_cache
from typing import TypeVar

from quack_core.fs.service.full_class import FileSystemService
from quack_core.fs.service.factory import create_service

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