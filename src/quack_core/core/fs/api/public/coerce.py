# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/coerce.py
# module: quack_core.core.fs.api.public.coerce
# role: api
# neighbors: __init__.py, checksums.py, disk.py, file_info.py, file_ops.py, path_ops.py (+3 more)
# exports: coerce_path, coerce_path_str, coerce_path_result
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

from __future__ import annotations
from pathlib import Path
from typing import Any
from quack_core.core.fs._internal.path_utils import _normalize_path_param, _extract_path_str
from quack_core.core.fs.results import DataResult

def coerce_path(obj: Any) -> Path:
    return _normalize_path_param(obj)

def coerce_path_str(obj: Any) -> str:
    return _extract_path_str(obj)

def coerce_path_result(obj: Any) -> DataResult[str]:
    try:
        p_str = _extract_path_str(obj)
        return DataResult(success=True, path=Path(p_str), data=p_str, format="path", message="Successfully coerced path")
    except Exception as e:
        return DataResult(success=False, path=None, data=str(obj), format="path", error=str(e), message="Failed to coerce path input")