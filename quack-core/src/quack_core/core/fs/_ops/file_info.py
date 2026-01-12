# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/file_info.py
# module: quack_core.core.fs._ops.file_info
# role: _ops
# neighbors: __init__.py, base.py, core.py, directory_ops.py, find_ops.py, path_ops.py (+4 more)
# exports: FileInfoOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 945fec3c
# === QV-LLM:END ===

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from quack_core.core.fs._internal.file_info import _get_iso_timestamps

@dataclass
class _FileInfo:
    """Internal DTO for file stats. Not a public Result."""
    path: Path
    exists: bool
    is_file: bool = False
    is_dir: bool = False
    size: int = 0
    modified: float = 0.0
    created: float = 0.0
    modified_iso: Optional[str] = None
    created_iso: Optional[str] = None
    owner: Optional[str] = None
    permissions: int = 0
    mime_type: Optional[str] = None

class FileInfoOperationsMixin:
    def _path_exists(self, path: Path) -> bool:
        return path.exists()

    def _get_file_info(self, path: Path) -> _FileInfo:
        if not path.exists(): return _FileInfo(path=path, exists=False)

        stat = path.stat()
        mime = None
        if path.is_file(): mime, _ = mimetypes.guess_type(str(path))

        owner = None
        try:
            import pwd
            owner = pwd.getpwuid(stat.st_uid).pw_name
        except (ImportError, KeyError, AttributeError): pass

        m_iso, c_iso = _get_iso_timestamps(path)

        return _FileInfo(
            path=path, exists=True, is_file=path.is_file(), is_dir=path.is_dir(),
            size=stat.st_size, modified=stat.st_mtime, created=stat.st_ctime,
            modified_iso=m_iso, created_iso=c_iso, owner=owner,
            permissions=stat.st_mode, mime_type=mime
        )