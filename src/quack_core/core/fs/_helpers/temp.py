# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_helpers/temp.py
# module: quack_core.core.fs._helpers.temp
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

import os
import tempfile
from pathlib import Path
from typing import Any
from quack_core.core.errors import QuackIOError
from quack_core.core.fs._helpers.path_utils import _normalize_path_param

def _create_temp_directory(prefix: str = "quackcore_", suffix: str = "") -> Path:
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix)
        return Path(temp_dir)
    except Exception as e:
        raise QuackIOError(f"Failed to create temporary directory: {e}") from e

def _create_temp_file(
        suffix: str = ".txt",
        prefix: str = "quackcore_",
        directory: Any = None,
) -> Path:
    dir_path = _normalize_path_param(directory) if directory is not None else None

    if dir_path and not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)

    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir_path)
        os.close(fd)
        return Path(path)
    except Exception as e:
        raise QuackIOError(f"Failed to create temporary file: {e}") from e