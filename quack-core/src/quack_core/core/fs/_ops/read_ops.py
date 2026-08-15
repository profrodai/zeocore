# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/read_ops.py
# module: quack_core.core.fs._ops.read_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: ReadOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: f4879df3
# === QV-LLM:END ===

from pathlib import Path

from quack_core.core.fs._internal.file_ops import _read_file_bytes, _read_file_text


class ReadOperationsMixin:
    def _read_text(self, path: Path, encoding: str = "utf-8") -> str:
        return _read_file_text(path, encoding)

    def _read_binary(self, path: Path) -> bytes:
        return _read_file_bytes(path)
