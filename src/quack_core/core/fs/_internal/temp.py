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