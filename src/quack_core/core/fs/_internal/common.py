# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/common.py
# module: quack_core.core.fs._internal.common
# role: module
# neighbors: __init__.py, checksums.py, comparison.py, directory_ops.py, disk.py, file_info.py (+5 more)
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

from pathlib import Path

def _get_extension(path: str | Path) -> str:
    path_obj = Path(path)
    filename = path_obj.name
    if filename.startswith(".") and "." not in filename[1:]:
        return filename[1:]
    return path_obj.suffix.lstrip(".")

def _normalize_path(path: str | Path) -> Path:
    path_obj = Path(path).expanduser()
    if path_obj.is_absolute():
        return path_obj
    try:
        return path_obj.resolve()
    except (OSError, RuntimeError):
        return path_obj.absolute()