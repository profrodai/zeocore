# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/write_ops.py
# module: quack_core.core.fs._operations.write_ops
# role: module
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: WriteOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from pathlib import Path


class WriteOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _write_text(self, path: str | Path, content: str, encoding: str = "utf-8", atomic: bool = True) -> Path:
        from quack_core.core.fs._helpers.file_ops import _atomic_write, _ensure_directory
        resolved = self._resolve_path(path)

        if atomic:
            # Enforce encoding here before passing bytes to atomic write
            return _atomic_write(resolved, content.encode(encoding))
        else:
            _ensure_directory(resolved.parent)
            with open(resolved, "w", encoding=encoding) as f:
                f.write(content)
            return resolved

    def _write_binary(self, path: str | Path, content: bytes, atomic: bool = True) -> Path:
        from quack_core.core.fs._helpers.file_ops import _atomic_write, _ensure_directory
        resolved = self._resolve_path(path)

        if atomic:
            return _atomic_write(resolved, content)
        else:
            _ensure_directory(resolved.parent)
            with open(resolved, "wb") as f:
                f.write(content)
            return resolved

    def _copy(self, src: str | Path, dst: str | Path, overwrite: bool = False) -> Path:
        from quack_core.core.fs._helpers.safe_ops import _safe_copy
        return _safe_copy(self._resolve_path(src), self._resolve_path(dst), overwrite)

    def _move(self, src: str | Path, dst: str | Path, overwrite: bool = False) -> Path:
        from quack_core.core.fs._helpers.safe_ops import _safe_move
        return _safe_move(self._resolve_path(src), self._resolve_path(dst), overwrite)

    def _delete(self, path: str | Path, missing_ok: bool = True) -> bool:
        from quack_core.core.fs._helpers.safe_ops import _safe_delete
        return _safe_delete(self._resolve_path(path), missing_ok)