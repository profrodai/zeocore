# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/core.py
# module: quack_core.core.fs._ops.core
# role: _ops
# neighbors: __init__.py, base.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 0f7f21fc
# === QV-LLM:END ===

import mimetypes
from pathlib import Path

def _initialize_mime_types() -> None:
    mimetypes.init()