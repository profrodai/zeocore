# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/path_utils.py
# module: quack_core.core.fs.api.public.path_utils
# role: api
# neighbors: __init__.py, checksums.py, coerce.py, disk.py, file_info.py, file_ops.py (+3 more)
# exports: extract_path_str, safe_path_str
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from typing import Any

from quack_core.core.fs._helpers.path_utils import (
    _extract_path_str,
    _safe_path_str,
)
from quack_core.core.logging import get_logger

logger = get_logger(__name__)

def extract_path_str(obj: Any) -> str:
    """
    Extract a string path from any path-like object or result object.
    Strict: raises TypeError/ValueError on failure.
    """
    return _extract_path_str(obj)

def safe_path_str(obj: Any, default: str | None = None) -> str | None:
    """
    Safely extract a string path from any object, returning a default on failure.
    Never raises.
    """
    return _safe_path_str(obj, default)