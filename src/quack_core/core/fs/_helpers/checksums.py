# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_helpers/checksums.py
# module: quack_core.core.fs._helpers.checksums
# role: module
# neighbors: __init__.py, common.py, comparison.py, disk.py, file_info.py, file_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

import hashlib
from typing import Any
from quack_core.core.fs._helpers.path_utils import _normalize_path_param
from quack_core.core.errors import QuackFileNotFoundError, QuackIOError

def _compute_checksum(path: Any, algorithm: str = "sha256") -> str:
    path_obj = _normalize_path_param(path)

    if not path_obj.exists():
        raise QuackFileNotFoundError(str(path_obj))
    if not path_obj.is_file():
        raise QuackIOError("Not a file", str(path_obj))

    try:
        hash_obj = getattr(hashlib, algorithm)()
        with open(path_obj, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except AttributeError:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    except Exception as e:
        raise QuackIOError(f"Checksum computation failed: {e}", str(path_obj)) from e