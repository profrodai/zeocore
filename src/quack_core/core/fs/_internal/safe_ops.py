import shutil
from pathlib import Path
from typing import Any
from quack_core.core.errors import QuackFileExistsError, QuackFileNotFoundError, QuackIOError, QuackPermissionError
from quack_core.core.fs._internal.path_utils import _normalize_path_param

def _safe_copy(src: Any, dst: Any, overwrite: bool = False) -> Path:
    src_path = _normalize_path_param(src)
    dst_path = _normalize_path_param(dst)
    if not src_path.exists(): raise QuackFileNotFoundError(str(src_path))
    if dst_path.exists() and not overwrite: raise QuackFileExistsError(str(dst_path))
    try:
        if src_path.is_dir():
            if dst_path.exists() and overwrite: shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
        else:
            if not dst_path.parent.exists(): dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
        return dst_path
    except PermissionError as e:
        raise QuackPermissionError(str(dst_path), "copy", original_error=e) from e
    except Exception as e:
        raise QuackIOError(f"Copy failed: {e}", str(dst_path), original_error=e) from e

def _safe_move(src: Any, dst: Any, overwrite: bool = False) -> Path:
    src_path = _normalize_path_param(src)
    dst_path = _normalize_path_param(dst)
    if not src_path.exists(): raise QuackFileNotFoundError(str(src_path))
    if dst_path.exists() and not overwrite: raise QuackFileExistsError(str(dst_path))
    try:
        if not dst_path.parent.exists(): dst_path.parent.mkdir(parents=True, exist_ok=True)
        if dst_path.exists() and overwrite:
            if dst_path.is_dir(): shutil.rmtree(dst_path)
            else: dst_path.unlink()
        shutil.move(str(src_path), str(dst_path))
        return dst_path
    except PermissionError as e:
        raise QuackPermissionError(str(dst_path), "move", original_error=e) from e
    except Exception as e:
        raise QuackIOError(f"Move failed: {e}", str(dst_path), original_error=e) from e

def _safe_delete(path: Any, missing_ok: bool = True) -> bool:
    path_obj = _normalize_path_param(path)
    if not path_obj.exists():
        if missing_ok: return False
        raise QuackFileNotFoundError(str(path_obj))
    try:
        if path_obj.is_dir(): shutil.rmtree(path_obj)
        else: path_obj.unlink()
        return True
    except PermissionError as e:
        raise QuackPermissionError(str(path_obj), "delete", original_error=e) from e
    except Exception as e:
        raise QuackIOError(f"Delete failed: {e}", str(path_obj), original_error=e) from e