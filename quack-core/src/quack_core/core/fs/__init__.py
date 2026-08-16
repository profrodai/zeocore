# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/__init__.py
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

from typing import Any

from quack_core.core.fs.results import (  # Typed results; Base results
    BoolResult,
    DataResult,
    DirectoryInfoResult,
    ErrorInfo,
    FileInfoResult,
    FindResult,
    OperationResult,
    PathResult,
    ReadResult,
    WriteResult,
)
from quack_core.core.fs.service import FileSystemService, create_service, get_service

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


# Doctrine enforcement: _internal and _ops are NOT exported.
#
# CPython's import machinery unconditionally binds a submodule as an attribute
# of its parent package the moment ANYTHING imports it (e.g. _ops/*.py's own
# `from quack_core.core.fs._internal.x import y`, which this module transitively
# triggers via the `service` import above). That binding happens regardless of
# __getattr__ below, so without this scrub, plain attribute access
# (`fs._internal`) would find the real bound submodule and never reach
# __getattr__ at all. Deleting the two names here forces attribute access back
# through __getattr__, restoring the doctrine guard for that access path.
#
# NOTE: this does NOT and cannot cover `from quack_core.core.fs import _internal`
# — CPython resolves that directly against sys.modules for any name that is a
# real submodule of the package, a path that never consults __getattr__ or the
# package's __dict__ at all (verified live; PEP 562's module __getattr__ has no
# hook into that specific import form). That is a hard language-level limit,
# not a bug in this module — see test_api_surface.py's own accompanying note.
del globals()["_internal"]
del globals()["_ops"]


def __getattr__(name: str) -> Any:  # noqa: ANN401  # dynamic attr type
    """Prevent accidental imports of internal modules."""
    if name.startswith("_internal") or name.startswith("_ops"):
        raise AttributeError(
            f"Module 'quack_core.core.fs' has no attribute '{name}'. "
            f"Internal modules (_internal, _ops) are not part of the public API. "
            f"Use FileSystemService instead."
        )
    raise AttributeError(f"Module 'quack_core.core.fs' has no attribute '{name}'")
