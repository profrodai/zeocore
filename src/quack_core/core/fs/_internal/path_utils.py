# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/path_utils.py
# module: quack_core.core.fs._internal.path_utils
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

import os
from pathlib import Path
from typing import Any
from quack_core.core.fs.protocols import HasData, HasPath, HasUnwrap, HasValue

def _extract_path_str(obj: Any) -> str:
    if obj is None:
        raise TypeError("Path cannot be None")
    if isinstance(obj, str):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "__fspath__"):
        return os.fspath(obj) # type: ignore

    if hasattr(obj, "success") and not getattr(obj, "success", True):
        raise ValueError(f"Cannot extract path from failed Result object: {obj}")

    if isinstance(obj, HasValue):
        return _extract_path_str(obj.value())
    if isinstance(obj, HasUnwrap):
        return _extract_path_str(obj.unwrap())

    if isinstance(obj, HasData) and obj.data is not None:
        if obj.data is not obj:
            try:
                return _extract_path_str(obj.data)
            except (TypeError, ValueError):
                pass

    if isinstance(obj, HasPath) and obj.path is not None:
        return _extract_path_str(obj.path)

    raise TypeError(f"Could not coerce object of type {type(obj)} to path string")

def _normalize_path_param(obj: Any) -> Path:
    try:
        s = _extract_path_str(obj)
        return Path(s)
    except (TypeError, ValueError) as e:
        raise TypeError(f"Could not coerce {type(obj)} to Path: {e}") from e

def _safe_path_str(obj: Any, default: str | None = None) -> str | None:
    try:
        return _extract_path_str(obj)
    except (TypeError, ValueError, AttributeError):
        return default