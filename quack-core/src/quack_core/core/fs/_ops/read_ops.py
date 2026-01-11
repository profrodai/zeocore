# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/read_ops.py
# module: quack_core.core.fs._ops.read_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: ReadOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 10c11a25
# === QV-LLM:END ===

from pathlib import Path

class ReadOperationsMixin:
    def _read_text(self, path: Path, encoding: str = "utf-8") -> str:
        with open(path, "r", encoding=encoding) as f:
            return f.read()

    def _read_binary(self, path: Path) -> bytes:
        with open(path, "rb") as f:
            return f.read()