# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/core.py
# module: quack_core.core.fs._operations.core
# role: module
# neighbors: __init__.py, base.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

import mimetypes
from pathlib import Path

def _resolve_path(base_dir: Path, path: str | Path) -> Path:
    """Resolve a path relative to the base directory."""
    try:
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj
        return base_dir / path
    except TypeError:
        return base_dir / str(path)

def _initialize_mime_types() -> None:
    mimetypes.init()