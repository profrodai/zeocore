import os
from typing import Any
from pathlib import Path
from quack_core.fs._internal.common import _normalize_path

def _is_same_file(path1: Path, path2: Path) -> bool:
    try:
        return os.path.samefile(str(path1), str(path2))
    except OSError:
        return _normalize_path(path1) == _normalize_path(path2)

def _is_subdirectory(child: Path, parent: Path) -> bool:
    child_path = _normalize_path(child)
    parent_path = _normalize_path(parent)
    if child_path == parent_path:
        return False
    try:
        child_path.relative_to(parent_path)
        return True
    except ValueError:
        return False