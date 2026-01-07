# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/file_info.py
# module: quack_core.core.fs._internal.file_info
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from quack_core.core.fs._internal.path_utils import _normalize_path_param

def _get_file_timestamp(path: Any) -> float:
    p = _normalize_path_param(path)
    return p.stat().st_mtime

def _get_iso_timestamps(path: Any) -> tuple[str, str]:
    p = _normalize_path_param(path)
    stat = p.stat()
    m_iso = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    c_iso = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
    return m_iso, c_iso

def _get_mime_type(path: Any) -> str | None:
    p = _normalize_path_param(path)
    if not p.is_file():
        return None
    mime, _ = mimetypes.guess_type(str(p))
    return mime

def _get_file_size_str(size_bytes: int) -> str:
    if size_bytes < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def _get_file_type(path: Any) -> str:
    p = _normalize_path_param(path)
    if not p.exists(): return "nonexistent"
    if p.is_file(): return "file"
    if p.is_dir(): return "directory"
    if p.is_symlink(): return "symlink"
    if p.is_socket(): return "socket"
    if p.is_fifo(): return "fifo"
    return "unknown"

def _is_file_locked(path: Any) -> bool:
    # Placeholder for platform-specific lock check
    return False