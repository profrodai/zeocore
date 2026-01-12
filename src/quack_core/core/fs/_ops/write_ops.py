# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/write_ops.py
# module: quack_core.core.fs._ops.write_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: WriteOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 6e6469fe
# === QV-LLM:END ===

from pathlib import Path
from quack_core.core.fs._internal.file_ops import _atomic_write, _write_file_text, _write_file_bytes
from quack_core.core.fs._internal.safe_ops import _safe_copy, _safe_move, _safe_delete

class WriteOperationsMixin:
    def _write_text(self, path: Path, content: str, encoding: str = "utf-8", atomic: bool = True) -> Path:
        if atomic:
            return _atomic_write(path, content.encode(encoding))
        else:
            return _write_file_text(path, content, encoding)

    def _write_binary(self, path: Path, content: bytes, atomic: bool = True) -> Path:
        if atomic:
            return _atomic_write(path, content)
        else:
            return _write_file_bytes(path, content)

    def _copy(self, src: Path, dst: Path, overwrite: bool = False) -> Path:
        return _safe_copy(src, dst, overwrite)

    def _move(self, src: Path, dst: Path, overwrite: bool = False) -> Path:
        return _safe_move(src, dst, overwrite)

    def _delete(self, path: Path, missing_ok: bool = True) -> bool:
        return _safe_delete(path, missing_ok)