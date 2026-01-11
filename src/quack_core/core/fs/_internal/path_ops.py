# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/path_ops.py
# module: quack_core.core.fs._internal.path_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, directory_ops.py, disk.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

import os
from pathlib import Path
from typing import Any

def _split_path(path: Path) -> list[str]:
    parts = list(path.parts)
    # Check original string repr if needed, but Path usually handles this.
    # We rely on caller to normalize first.
    return parts

def _expand_user_vars(path: Path) -> Path:
    path_str = str(path)
    path_str = os.path.expanduser(path_str)
    path_str = os.path.expandvars(path_str)
    return Path(path_str)