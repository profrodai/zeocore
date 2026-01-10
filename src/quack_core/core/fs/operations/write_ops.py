# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/operations/write_ops.py
# module: quack_core.core.fs.operations.write_ops
# role: operations
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: WriteOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

from pathlib import Path
from quack_core.core.fs._internal.file_ops import _atomic_write, _ensure_directory
from quack_core.core.fs._internal.safe_ops import _safe_copy, _safe_move, _safe_delete

class WriteOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _write_text(self, path: str | Path, content: str, encoding: str = "utf-8", atomic: bool = True) -> Path:
        resolved = self._resolve_path(path)
        if atomic:
            return _atomic_write(resolved, content.encode(encoding))
        else:
            _ensure_directory(resolved.parent)
            with open(resolved, "w", encoding=encoding) as f:
                f.write(content)
            return resolved

    def _write_binary(self, path: str | Path, content: bytes, atomic: bool = True) -> Path:
        resolved = self._resolve_path(path)
        if atomic:
            return _atomic_write(resolved, content)
        else:
            _ensure_directory(resolved.parent)
            with open(resolved, "wb") as f:
                f.write(content)
            return resolved

    def _copy(self, src: str | Path, dst: str | Path, overwrite: bool = False) -> Path:
        return _safe_copy(self._resolve_path(src), self._resolve_path(dst), overwrite)

    def _move(self, src: str | Path, dst: str | Path, overwrite: bool = False) -> Path:
        return _safe_move(self._resolve_path(src), self._resolve_path(dst), overwrite)

    def _delete(self, path: str | Path, missing_ok: bool = True) -> bool:
        return _safe_delete(self._resolve_path(path), missing_ok)