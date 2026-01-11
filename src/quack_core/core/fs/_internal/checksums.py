# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/checksums.py
# module: quack_core.core.fs._internal.checksums
# role: module
# neighbors: __init__.py, common.py, comparison.py, directory_ops.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

import hashlib
from typing import Any
from pathlib import Path

def _compute_checksum(path: Path, algorithm: str = "sha256") -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    if not path.is_file():
        raise IOError(f"Not a file: {path}")

    try:
        hash_obj = getattr(hashlib, algorithm)()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except AttributeError:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    except Exception as e:
        raise IOError(f"Checksum computation failed: {e}") from e