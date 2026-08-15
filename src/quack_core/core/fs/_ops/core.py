# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/core.py
# module: quack_core.core.fs._ops.core
# role: _ops
# neighbors: __init__.py, base.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# git_branch: main
# git_commit: f0715f0c
# === QV-LLM:END ===

import mimetypes


def _initialize_mime_types() -> None:
    mimetypes.init()
