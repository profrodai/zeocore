import os
from pathlib import Path
from typing import Any

def _split_path(path: Path) -> list[str]:
    parts = list(path.parts)
    # Check original string repr if needed, but Path usually handles this.
    # We rely on caller to normalize first.
    return parts

def _expand_user_vars(path: Path) -> Path:
    path_str = str(path)
    path_str = os.path.expanduser(path_str)
    path_str = os.path.expandvars(path_str)
    return Path(path_str)