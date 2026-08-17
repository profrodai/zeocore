import os
import tempfile
from pathlib import Path


def _create_temp_directory(
    prefix: str = "zeocore_", suffix: str = "", directory: Path | None = None
) -> Path:
    if directory and not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=directory)
        return Path(temp_dir)
    except Exception as e:
        raise OSError(f"Failed to create temporary directory: {e}") from e


def _create_temp_file(
    suffix: str = ".txt", prefix: str = "zeocore_", directory: Path | None = None
) -> Path:
    if directory and not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
        os.close(fd)
        return Path(path)
    except Exception as e:
        raise OSError(f"Failed to create temporary file: {e}") from e
