# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/comparison.py
# module: quack_core.core.fs._internal.comparison
# role: module
# neighbors: __init__.py, checksums.py, common.py, disk.py, file_info.py, file_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

import os
from typing import Any
from quack_core.core.fs._internal.common import _normalize_path
from quack_core.core.fs._internal.path_utils import _normalize_path_param

def _is_same_file(path1: Any, path2: Any) -> bool:
    path1_obj = _normalize_path_param(path1)
    path2_obj = _normalize_path_param(path2)

    try:
        return os.path.samefile(str(path1_obj), str(path2_obj))
    except OSError:
        return _normalize_path(path1_obj) == _normalize_path(path2_obj)

def _is_subdirectory(child: Any, parent: Any) -> bool:
    child_path = _normalize_path(_normalize_path_param(child))
    parent_path = _normalize_path(_normalize_path_param(parent))

    if child_path == parent_path:
        return False

    try:
        child_path.relative_to(parent_path)
        return True
    except ValueError:
        return False