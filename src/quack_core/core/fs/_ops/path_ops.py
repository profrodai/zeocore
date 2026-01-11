# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/path_ops.py
# module: quack_core.core.fs._ops.path_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: PathOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

from pathlib import Path
from quack_core.core.fs._internal.path_ops import _expand_user_vars, _split_path
from quack_core.core.fs._internal.common import _get_extension, _normalize_path
from quack_core.core.fs._internal.comparison import _is_same_file, _is_subdirectory

class PathOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _split_path(self, path: str | Path) -> list[str]:
        return _split_path(self._resolve_path(path))

    def _normalize_path(self, path: str | Path) -> Path:
        return _normalize_path(self._resolve_path(path))

    def _expand_user_vars(self, path: str | Path) -> str:
        return str(_expand_user_vars(self._resolve_path(path)))

    def _is_same_file(self, path1: str | Path, path2: str | Path) -> bool:
        return _is_same_file(self._resolve_path(path1), self._resolve_path(path2))

    def _is_subdirectory(self, child: str | Path, parent: str | Path) -> bool:
        return _is_subdirectory(self._resolve_path(child), self._resolve_path(parent))

    def _get_extension(self, path: str | Path) -> str:
        return _get_extension(self._resolve_path(path))

    def _is_path_syntax_valid(self, path_str: str) -> bool:
        try:
            Path(path_str)
            return True
        except Exception:
            return False