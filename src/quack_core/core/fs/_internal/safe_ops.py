# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/safe_ops.py
# module: quack_core.core.fs._internal.safe_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===

import shutil
from pathlib import Path
from typing import Any

def _safe_copy(src: Path, dst: Path, overwrite: bool = False) -> Path:
    if not src.exists(): raise FileNotFoundError(str(src))
    if dst.exists() and not overwrite: raise FileExistsError(str(dst))
    try:
        if src.is_dir():
            if dst.exists() and overwrite: shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            if not dst.parent.exists(): dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return dst
    except PermissionError as e:
        raise PermissionError(f"Permission denied copying to {dst}") from e
    except Exception as e:
        raise IOError(f"Copy failed: {e}") from e

def _safe_move(src: Path, dst: Path, overwrite: bool = False) -> Path:
    if not src.exists(): raise FileNotFoundError(str(src))
    if dst.exists() and not overwrite: raise FileExistsError(str(dst))
    try:
        if not dst.parent.exists(): dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and overwrite:
            if dst.is_dir(): shutil.rmtree(dst)
            else: dst.unlink()
        shutil.move(str(src), str(dst))
        return dst
    except PermissionError as e:
        raise PermissionError(f"Permission denied moving to {dst}") from e
    except Exception as e:
        raise IOError(f"Move failed: {e}") from e

def _safe_delete(path: Path, missing_ok: bool = True) -> bool:
    if not path.exists():
        if missing_ok: return False
        raise FileNotFoundError(str(path))
    try:
        if path.is_dir(): shutil.rmtree(path)
        else: path.unlink()
        return True
    except PermissionError as e:
        raise PermissionError(f"Permission denied deleting {path}") from e
    except Exception as e:
        raise IOError(f"Delete failed: {e}") from e