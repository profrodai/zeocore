import os
from pathlib import Path

def _ensure_directory(path: Path, exist_ok: bool = True) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=exist_ok)
        return path
    except FileExistsError as e:
        raise FileExistsError(f"Directory already exists: {path}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied creating directory: {path}") from e
    except Exception as e:
        raise IOError(f"Failed to create directory: {e}") from e