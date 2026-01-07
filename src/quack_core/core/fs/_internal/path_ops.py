# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/path_ops.py
# module: quack_core.core.fs._internal.path_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

import os
from pathlib import Path
from typing import Any
from quack_core.core.fs._internal.path_utils import _normalize_path_param

def _split_path(path: Any) -> list[str]:
    path_obj = _normalize_path_param(path)
    parts = list(path_obj.parts)
    if str(path).startswith("./"):
        parts.insert(0, ".")
    return parts

def _expand_user_vars(path: Any) -> Path:
    path_obj = _normalize_path_param(path)
    path_str = str(path_obj)
    path_str = os.path.expanduser(path_str)
    path_str = os.path.expandvars(path_str)
    return Path(path_str)