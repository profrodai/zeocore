# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/common.py
# module: quack_core.core.fs._internal.common
# role: module
# neighbors: __init__.py, checksums.py, comparison.py, directory_ops.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 76a2f2b9
# === QV-LLM:END ===

from pathlib import Path

def _get_extension(path: Path) -> str:
    # Doctrine: _internal receives strict Paths, no strings.
    filename = path.name
    if filename.startswith(".") and "." not in filename[1:]:
        return filename[1:]
    return path.suffix.lstrip(".")