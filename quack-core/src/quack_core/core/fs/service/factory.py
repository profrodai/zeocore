# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/factory.py
# module: quack_core.core.fs.service.factory
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, file_info_operations.py, file_operations.py, full_class.py (+5 more)
# exports: create_service
# git_branch: feat/9-make-setup-work
# git_commit: d5eb52c8
# === QV-LLM:END ===

from pathlib import Path
from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.logging import LOG_LEVELS, LogLevel


def create_service(
        base_dir: str | Path | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        unsafe_allow_absolute_paths: bool = False,
) -> FileSystemService:
    """
    Factory to create a FileSystemService instance.

    Args:
        base_dir: Root directory for the service. Defaults to CWD.
        log_level: Logging verbosity.
        unsafe_allow_absolute_paths: If True, allows operations outside the base_dir.
                                      ⚠️  WARNING: Disables filesystem sandboxing for absolute paths.
                                      This should only be used in trusted environments.
    """
    return FileSystemService(
        base_dir=base_dir,
        log_level=log_level,
        unsafe_allow_absolute_paths=unsafe_allow_absolute_paths
    )