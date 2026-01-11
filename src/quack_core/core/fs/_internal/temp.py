# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/temp.py
# module: quack_core.core.fs._internal.temp
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

import os
import tempfile
from pathlib import Path
from typing import Any

def _create_temp_directory(prefix: str = "quackcore_", suffix: str = "") -> Path:
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix)
        return Path(temp_dir)
    except Exception as e:
        raise IOError(f"Failed to create temporary directory: {e}") from e

def _create_temp_file(suffix: str = ".txt", prefix: str = "quackcore_", directory: Path | None = None) -> Path:
    if directory and not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
        os.close(fd)
        return Path(path)
    except Exception as e:
        raise IOError(f"Failed to create temporary file: {e}") from e