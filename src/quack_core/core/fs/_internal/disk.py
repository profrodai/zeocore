import os
import shutil
from typing import Any
from quack_core.core.errors import QuackIOError
from quack_core.core.fs._internal.path_utils import _normalize_path_param

def _get_disk_usage(path: Any) -> dict[str, int]:
    path_obj = _normalize_path_param(path)
    try:
        total, used, free = shutil.disk_usage(str(path_obj))
        return {"total": total, "used": used, "free": free}
    except Exception as e:
        raise QuackIOError(f"Error getting disk usage: {e}", str(path_obj)) from e

def _is_path_writeable(path: Any) -> bool:
    path_obj = _normalize_path_param(path)
    if not path_obj.exists():
        try:
            if path_obj.suffix:
                with open(path_obj, "w") as _: pass
                path_obj.unlink()
            else:
                path_obj.mkdir(parents=True)
                path_obj.rmdir()
            return True
        except Exception:
            return False
    if path_obj.is_file():
        return os.access(path_obj, os.W_OK)
    if path_obj.is_dir():
        try:
            test_file = path_obj / f"test_write_{os.getpid()}.tmp"
            with open(test_file, "w") as _: pass
            test_file.unlink()
            return True
        except Exception:
            return False
    return False