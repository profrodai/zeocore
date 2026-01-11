import os
from pathlib import Path
from quack_core.core.errors import QuackFileExistsError, QuackPermissionError, QuackIOError

def _ensure_directory(path: Path, exist_ok: bool = True) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=exist_ok)
        return path
    except FileExistsError as e:
        raise QuackFileExistsError(str(path), original_error=e) from e
    except PermissionError as e:
        raise QuackPermissionError(str(path), "create directory", original_error=e) from e
    except Exception as e:
        raise QuackIOError(f"Failed to create directory: {e}", str(path), original_error=e) from e