# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/__init__.py
# module: quack_core.core.fs.service.__init__
# role: service
# VERSION: V6 FINAL - Hardened service API exports
# === QV-LLM:END ===

"""
Filesystem service module.

PUBLIC EXPORTS:
- FileSystemService: The main service class (canonical API)
- get_service(): Singleton accessor
- create_service(): Factory function

INTERNAL (not exported):
- Individual mixins (DirectoryOperationsMixin, etc.)
- Base classes (_BaseFileSystemService)
- Operation modules

Use FileSystemService for all filesystem operations.
"""

from functools import lru_cache
from typing import TypeVar

from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.fs.service.factory import create_service

T = TypeVar("T")


@lru_cache(maxsize=1)
def get_service() -> FileSystemService:
    """
    Get the singleton FileSystemService instance.

    This is the recommended way to access filesystem operations.
    The service is configured with default settings (CWD as base_dir).

    Returns:
        FileSystemService: Configured singleton instance
    """
    return create_service()


# Public API - only these three
__all__ = [
    "FileSystemService",
    "create_service",
    "get_service",
]


# Doctrine enforcement: Internal modules not exported
def __getattr__(name: str):
    """Prevent accidental imports of internal service modules."""
    # List of internal names that should not be imported
    internal_names = {
        '_BaseFileSystemService',
        'DirectoryOperationsMixin',
        'FileOperationsMixin',
        'FileInfoOperationsMixin',
        'PathOperationsMixin',
        'PathValidationMixin',
        'UtilityOperationsMixin',
        'StructuredDataMixin',
    }

    if name in internal_names:
        raise AttributeError(
            f"'{name}' is an internal service component and not part of the public API. "
            f"Use FileSystemService instead, which includes all operations."
        )

    raise AttributeError(f"Module 'quack_core.core.fs.service' has no attribute '{name}'")