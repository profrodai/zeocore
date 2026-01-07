# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/path_ops.py
# module: quack_core.core.fs._operations.path_ops
# role: module
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: PathOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

# This file now simply delegates to _helpers (SSOT).
# No logic duplication.

from pathlib import Path
from quack_core.core.fs._helpers.path_ops import _expand_user_vars, _split_path
from quack_core.core.fs._helpers.common import _get_extension, _normalize_path
from quack_core.core.fs._helpers.comparison import _is_same_file, _is_subdirectory

class PathOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _split_path(self, path: str | Path) -> list[str]:
        resolved = self._resolve_path(path)
        return _split_path(resolved)

    def _normalize_path(self, path: str | Path) -> Path:
        resolved = self._resolve_path(path)
        return _normalize_path(resolved)

    def _expand_user_vars(self, path: str | Path) -> str:
        resolved = self._resolve_path(path)
        return str(_expand_user_vars(resolved))

    def _is_same_file(self, path1: str | Path, path2: str | Path) -> bool:
        p1 = self._resolve_path(path1)
        p2 = self._resolve_path(path2)
        return _is_same_file(p1, p2)

    def _is_subdirectory(self, child: str | Path, parent: str | Path) -> bool:
        c = self._resolve_path(child)
        p = self._resolve_path(parent)
        return _is_subdirectory(c, p)

    def _get_extension(self, path: str | Path) -> str:
        resolved = self._resolve_path(path)
        return _get_extension(resolved)

    def _is_path_syntax_valid(self, path_str: str) -> bool:
        try:
            Path(path_str)
            return True
        except Exception:
            return False