import os
from pathlib import Path

def _split_path(path: Path) -> list[str]:
    return list(path.parts)

def _expand_user_vars(path: Path) -> Path:
    path_str = str(path)
    path_str = os.path.expanduser(path_str)
    path_str = os.path.expandvars(path_str)
    return Path(path_str)