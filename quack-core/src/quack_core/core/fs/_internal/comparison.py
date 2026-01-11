import os
from pathlib import Path

def _is_same_file(path1: Path, path2: Path) -> bool:
    try:
        return os.path.samefile(str(path1), str(path2))
    except OSError:
        # Fallback for non-existent paths
        return path1.resolve() == path2.resolve()

def _is_subdirectory(child: Path, parent: Path) -> bool:
    child_path = child.resolve()
    parent_path = parent.resolve()
    if child_path == parent_path:
        return False
    try:
        child_path.relative_to(parent_path)
        return True
    except ValueError:
        return False