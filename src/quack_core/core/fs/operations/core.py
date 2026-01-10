# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/operations/core.py
# module: quack_core.core.fs.operations.core
# role: operations
# neighbors: __init__.py, base.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

import mimetypes
from pathlib import Path

def _resolve_path(base_dir: Path, path: str | Path) -> Path:
    try:
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj
        return base_dir / path
    except TypeError:
        return base_dir / str(path)

def _initialize_mime_types() -> None:
    mimetypes.init()