# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/factory.py
# module: quack_core.core.fs.service.factory
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: create_service
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

from pathlib import Path
from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.logging import LOG_LEVELS, LogLevel

def create_service(
    base_dir: str | Path | None = None,
    log_level: int = LOG_LEVELS[LogLevel.INFO],
) -> FileSystemService:
    return FileSystemService(base_dir=base_dir, log_level=log_level)