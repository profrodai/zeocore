# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/directory_ops.py
# module: quack_core.core.fs._internal.directory_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

import os
from pathlib import Path
from quack_core.core.errors import QuackFileExistsError, QuackPermissionError, QuackIOError

def _ensure_directory(path: Path, exist_ok: bool = True) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=exist_ok)
        return path
    except FileExistsError as e:
        raise QuackFileExistsError(str(path), original_error=e) from e
    except PermissionError as e:
        raise QuackPermissionError(str(path), "create directory", original_error=e) from e
    except Exception as e:
        raise QuackIOError(f"Failed to create directory: {e}", str(path), original_error=e) from e