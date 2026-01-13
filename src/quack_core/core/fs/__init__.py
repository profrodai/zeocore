# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/__init__.py
# module: quack_core.core.fs.__init__
# role: module
# VERSION: V6 FINAL - Hardened public API surface
# === QV-LLM:END ===

"""
Filesystem package for quack_core.

PUBLIC API:
- FileSystemService: Main service class
- get_service(): Get singleton service instance
- create_service(): Factory for new service instances
- Result models: All *Result classes for type hints

DOCTRINE:
This module exposes ONLY the public API surface.
Internal modules (_internal, _ops) are not exported.
"""

from quack_core.core.fs.service import (
    FileSystemService,
    get_service,
    create_service
)

from quack_core.core.fs.results import (
    # Base results
    OperationResult,
    ErrorInfo,

    # Typed results
    BoolResult,
    ReadResult,
    WriteResult,
    FileInfoResult,
    DirectoryInfoResult,
    FindResult,
    DataResult,
    PathResult,
)

# Public API - explicitly defined
__all__ = [
    # Service access
    "FileSystemService",
    "get_service",
    "create_service",

    # Result models (for type hints)
    "OperationResult",
    "ErrorInfo",
    "BoolResult",
    "ReadResult",
    "WriteResult",
    "FileInfoResult",
    "DirectoryInfoResult",
    "FindResult",
    "DataResult",
    "PathResult",
]


# Doctrine enforcement: _internal and _ops are NOT exported
# If you try to import them, you get AttributeError
def __getattr__(name: str):
    """Prevent accidental imports of internal modules."""
    if name.startswith('_internal') or name.startswith('_ops'):
        raise AttributeError(
            f"Module 'quack_core.core.fs' has no attribute '{name}'. "
            f"Internal modules (_internal, _ops) are not part of the public API. "
            f"Use FileSystemService instead."
        )
    raise AttributeError(f"Module 'quack_core.core.fs' has no attribute '{name}'")