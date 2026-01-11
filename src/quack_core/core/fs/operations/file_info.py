# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/operations/file_info.py
# module: quack_core.core.fs.operations.file_info
# role: operations
# neighbors: __init__.py, base.py, core.py, directory_ops.py, find_ops.py, path_ops.py (+4 more)
# exports: FileInfo, FileInfoOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from quack_core.core.fs._internal.file_info import _get_iso_timestamps

@dataclass
class FileInfo:
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
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _path_exists(self, path: str | Path) -> bool:
        return self._resolve_path(path).exists()

    def _get_file_info(self, path: str | Path) -> FileInfo:
        resolved = self._resolve_path(path)
        if not resolved.exists(): return FileInfo(path=resolved, exists=False)

        stat = resolved.stat()
        mime = None
        if resolved.is_file(): mime, _ = mimetypes.guess_type(str(resolved))

        owner = None
        try:
            import pwd
            owner = pwd.getpwuid(stat.st_uid).pw_name
        except (ImportError, KeyError, AttributeError): pass

        m_iso, c_iso = _get_iso_timestamps(resolved)

        return FileInfo(
            path=resolved, exists=True, is_file=resolved.is_file(), is_dir=resolved.is_dir(),
            size=stat.st_size, modified=stat.st_mtime, created=stat.st_ctime,
            modified_iso=m_iso, created_iso=c_iso, owner=owner,
            permissions=stat.st_mode, mime_type=mime
        )