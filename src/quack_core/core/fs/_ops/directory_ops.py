# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/directory_ops.py
# module: quack_core.core.fs._ops.directory_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# exports: DirectoryOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 2d6aea0e
# === QV-LLM:END ===

from pathlib import Path
from dataclasses import dataclass
from quack_core.core.fs._internal.directory_ops import _ensure_directory, _scan_directory


@dataclass
class _DirectoryInfo:
    """Internal DTO for directory stats. Not a public Result."""
    path: Path
    files: list[Path]
    directories: list[Path]
    total_size: int
    is_empty: bool
    total_files: int
    total_directories: int


class DirectoryOperationsMixin:
    def _ensure_directory(self, path: Path, exist_ok: bool = True) -> Path:
        return _ensure_directory(path, exist_ok)

    def _list_directory(self, path: Path, pattern: str | None = None, recursive: bool = False,
                        include_hidden: bool = False) -> _DirectoryInfo:
        stats = _scan_directory(path, pattern, recursive, include_hidden)

        return _DirectoryInfo(
            path=path,
            files=stats.files,
            directories=stats.directories,
            total_size=stats.total_size,
            is_empty=(len(stats.files) == 0 and len(stats.directories) == 0),
            total_files=len(stats.files),
            total_directories=len(stats.directories)
        )