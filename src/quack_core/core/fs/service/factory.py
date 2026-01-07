# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/factory.py
# module: quack_core.core.fs.service.factory
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: create_service
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/service/factory.py
"""
Factory functions for creating FileSystemService instances.
"""

from pathlib import Path

from quack_core.fs.results import DataResult, OperationResult

# Import the full FileSystemService with all mixins
from quack_core.fs.service.full_class import FileSystemService
from quack_core.logging import LOG_LEVELS, LogLevel


def create_service(
    base_dir: str | Path | DataResult | OperationResult | None = None,
    log_level: int = LOG_LEVELS[LogLevel.INFO],
) -> FileSystemService:
    """
    Create a new FileSystemService instance.

    Args:
        base_dir: Optional base directory for relative paths
                 (string, Path, DataResult, or OperationResult, default: current working directory)
        log_level: Logging level for the service

    Returns:
        A new FileSystemService instance
    """
    # Since the FileSystemService initialization already handles Path conversion,
    # we don't need to do additional normalization here.
    return FileSystemService(base_dir=base_dir, log_level=log_level)
