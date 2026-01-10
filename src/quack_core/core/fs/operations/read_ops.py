# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/operations/read_ops.py
# module: quack_core.core.fs.operations.read_ops
# role: operations
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: ReadOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

from pathlib import Path

class ReadOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        resolved = self._resolve_path(path)
        with open(resolved, "r", encoding=encoding) as f:
            return f.read()

    def _read_binary(self, path: str | Path) -> bytes:
        resolved = self._resolve_path(path)
        with open(resolved, "rb") as f:
            return f.read()