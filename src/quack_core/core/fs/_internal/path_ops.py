# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/path_ops.py
# module: quack_core.core.fs._internal.path_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, directory_ops.py, disk.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 0f7f21fc
# === QV-LLM:END ===

import os
from pathlib import Path

def _split_path(path: Path) -> list[str]:
    return list(path.parts)

def _expand_user_vars(path: Path) -> Path:
    path_str = str(path)
    path_str = os.path.expanduser(path_str)
    path_str = os.path.expandvars(path_str)
    return Path(path_str)

def _resolve_path(path: Path, strict: bool = False) -> Path:
    """
    Wrapper around Path.resolve().
    If strict=True, raises FileNotFoundError if path doesn't exist.
    """
    return path.resolve(strict=strict)