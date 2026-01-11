# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/disk.py
# module: quack_core.core.fs._internal.disk
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, directory_ops.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

import os
import shutil
from typing import Any
from pathlib import Path

def _get_disk_usage(path: Path) -> dict[str, int]:
    try:
        total, used, free = shutil.disk_usage(str(path))
        return {"total": total, "used": used, "free": free}
    except Exception as e:
        raise IOError(f"Error getting disk usage: {e}") from e

def _is_path_writeable(path: Path) -> bool:
    if not path.exists():
        try:
            if path.suffix:
                with open(path, "w") as _: pass
                path.unlink()
            else:
                path.mkdir(parents=True)
                path.rmdir()
            return True
        except Exception:
            return False
    if path.is_file():
        return os.access(path, os.W_OK)
    if path.is_dir():
        try:
            test_file = path / f"test_write_{os.getpid()}.tmp"
            with open(test_file, "w") as _: pass
            test_file.unlink()
            return True
        except Exception:
            return False
    return False