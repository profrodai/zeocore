# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/directory_ops.py
# module: quack_core.core.fs._ops.directory_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# exports: DirectoryInfo, DirectoryOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

from pathlib import Path
from dataclasses import dataclass
from quack_core.core.fs._internal.directory_ops import _ensure_directory

@dataclass
class DirectoryInfo:
    path: Path
    files: list[Path]
    directories: list[Path]
    total_size: int
    is_empty: bool
    total_files: int
    total_directories: int

class DirectoryOperationsMixin:
    # Thin bridge to _internal
    def _ensure_directory(self, path: Path, exist_ok: bool = True) -> Path:
        return _ensure_directory(path, exist_ok)

    def _list_directory(self, path: Path, pattern: str | None = None, include_hidden: bool = False) -> DirectoryInfo:
        # Implementation moved to _internal? Or kept here as "logic"?
        # Keeping minimal logic here but ensuring no path resolution
        if not path.exists(): raise FileNotFoundError(f"Directory not found: {path}")
        if not path.is_dir(): raise NotADirectoryError(f"Not a directory: {path}")

        files = []
        directories = []
        total_size = 0

        for item in path.iterdir():
            if not include_hidden and item.name.startswith('.'): continue
            if pattern and not item.match(pattern): continue

            if item.is_file():
                files.append(item)
                try: total_size += item.stat().st_size
                except OSError: pass
            elif item.is_dir():
                directories.append(item)

        return DirectoryInfo(
            path=path, files=files, directories=directories, total_size=total_size,
            is_empty=(len(files) == 0 and len(directories) == 0),
            total_files=len(files), total_directories=len(directories)
        )