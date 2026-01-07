# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/__init__.py
# module: quack_core.core.fs._operations.__init__
# role: module
# neighbors: base.py, core.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# exports: FileSystemOperations, _atomic_write, _compute_checksum, _ensure_directory, _safe_copy, _safe_delete, _safe_move
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_operations/__init__.py
"""
Core filesystem _operations implementation.

This module provides the implementation of filesystem _operations
with proper error handling and consistent return values. It assembles
all the operation mixins into the FileSystemOperations class,
which is the primary internal implementation used by the public API.

The _operations package follows this contract:
- Internal methods return basic types (str, bytes, Path, bool)
- Input types are limited to str or Path and resolved early
- Exceptions are raised naturally and not caught at this level
"""

from pathlib import Path
from typing import Any, TypeVar

# Import utility functions directly into this namespace for backward compatibility
# This will make patching work correctly in tests
from quack_core.fs._helpers import (
    _atomic_write,
    _compute_checksum,
    _ensure_directory,
    _safe_copy,
    _safe_delete,
    _safe_move,
)
from quack_core.logging import get_logger

# Set up module-level logger
logger = get_logger(__name__)

# Import all the mixins we need
from .core import _initialize_mime_types, _resolve_path
from .directory_ops import DirectoryOperationsMixin
from .file_info import FileInfoOperationsMixin
from .find_ops import FindOperationsMixin
from .path_ops import PathOperationsMixin
from .read_ops import ReadOperationsMixin
from .serialization_ops import SerializationOperationsMixin
from .utility_ops import UtilityOperationsMixin
from .write_ops import WriteOperationsMixin


# Define the FileSystemOperations class properly with all mixins
class FileSystemOperations(
    ReadOperationsMixin,
    WriteOperationsMixin,
    FileInfoOperationsMixin,
    DirectoryOperationsMixin,
    FindOperationsMixin,
    SerializationOperationsMixin,
    PathOperationsMixin,
    UtilityOperationsMixin,
):
    """
    Core implementation of filesystem _operations.

    This class combines all operation mixins to provide a complete
    filesystem _operations implementation with error handling,
    logging, and return values. It serves as the internal implementation
    layer used by the public API in quack_core.fs.service.

    All methods follow this contract:
    - Internal methods accept only str or Path input
    - Internal methods return basic types (str, bytes, Path, bool, etc.)
    - Exceptions are raised naturally and not caught at this level
    """

    def __init__(self, base_dir: Any = None) -> None:
        """
        Initialize filesystem _operations.

        Args:
            base_dir: Optional base directory for relative paths.
                     If not provided, the current working directory is used.
        """
        from pathlib import Path

        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        logger.debug(f"Initialized FileSystemOperations with base_dir: {self.base_dir}")
        _initialize_mime_types()

    def _resolve_path(self, path: str | Path) -> Path:
        """
        Resolve a path relative to the base directory.

        This method normalizes all path inputs to Path objects and resolves them
        relative to the base directory set during initialization.

        Args:
            path: Path to resolve (str or Path)

        Returns:
            Path: Resolved Path object

        Note:
            This is an internal helper method called by all other methods.
            It implements the abstract method defined in the mixins.
        """
        return _resolve_path(self.base_dir, path)


# Re-export the FileSystemOperations class and utility functions for backward compatibility
__all__ = [
    "FileSystemOperations",
    "_atomic_write",
    "_compute_checksum",
    "_ensure_directory",
    "_safe_copy",
    "_safe_delete",
    "_safe_move",
]

# Export TypeVar T for backward compatibility
T = TypeVar("T")  # Generic type for flexible typing
