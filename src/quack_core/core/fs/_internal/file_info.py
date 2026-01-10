import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _get_file_timestamp(path: Path) -> float:
    return path.stat().st_mtime

def _get_iso_timestamps(path: Path) -> tuple[str, str]:
    stat = path.stat()
    m_iso = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    c_iso = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
    return m_iso, c_iso

def _get_mime_type(path: Path) -> str | None:
    if not path.is_file():
        return None
    mime, _ = mimetypes.guess_type(str(path))
    return mime

def _get_file_size_str(size_bytes: int) -> str:
    if size_bytes < 0: return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def _get_file_type(path: Path) -> str:
    if not path.exists(): return "nonexistent"
    if path.is_file(): return "file"
    if path.is_dir(): return "directory"
    if path.is_symlink(): return "symlink"
    if path.is_socket(): return "socket"
    if path.is_fifo(): return "fifo"
    return "unknown"

def _is_file_locked(path: Path) -> bool:
    return False # Placeholder