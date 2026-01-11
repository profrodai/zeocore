# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/directory_ops.py
# module: quack_core.core.fs._internal.directory_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 10c11a25
# === QV-LLM:END ===

import os
from pathlib import Path

def _ensure_directory(path: Path, exist_ok: bool = True) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=exist_ok)
        return path
    except FileExistsError as e:
        raise FileExistsError(f"Directory already exists: {path}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied creating directory: {path}") from e
    except Exception as e:
        raise IOError(f"Failed to create directory: {e}") from e