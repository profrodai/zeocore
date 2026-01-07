# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_helpers/common.py
# module: quack_core.core.fs._helpers.common
# role: module
# neighbors: __init__.py, checksums.py, comparison.py, disk.py, file_info.py, file_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from pathlib import Path

def _get_extension(path: str | Path) -> str:
    """Get the file extension from a path."""
    path_obj = Path(path)
    filename = path_obj.name
    # Special case for dotfiles
    if filename.startswith(".") and "." not in filename[1:]:
        return filename[1:]
    return path_obj.suffix.lstrip(".")

def _normalize_path(path: str | Path) -> Path:
    """
    Normalize a path for cross-platform compatibility.
    Does not check existence.
    """
    path_obj = Path(path).expanduser()
    if path_obj.is_absolute():
        return path_obj
    try:
        return path_obj.resolve()
    except (OSError, RuntimeError):
        return path_obj.absolute()