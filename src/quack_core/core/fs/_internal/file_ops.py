# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/file_ops.py
# module: quack_core.core.fs._internal.file_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

import os
import re
import tempfile
from pathlib import Path
from typing import Any
from quack_core.core.errors import QuackFileExistsError, QuackFileNotFoundError, QuackIOError, QuackPermissionError
from quack_core.core.fs._internal.path_utils import _normalize_path_param

def _get_unique_filename(directory: Any, filename: str, raise_if_exists: bool = False) -> Path:
    dir_path = _normalize_path_param(directory)
    if not dir_path.exists():
        raise QuackFileNotFoundError(str(directory), message="Directory does not exist")
    if not filename or not filename.strip():
        raise QuackIOError("Filename cannot be empty", str(directory))
    path = dir_path / filename
    if not path.exists():
        return path
    if raise_if_exists:
        raise QuackFileExistsError(str(path), message="File already exists")
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = dir_path / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

def _ensure_directory(path: Any, exist_ok: bool = True) -> Path:
    path_obj = _normalize_path_param(path)
    try:
        path_obj.mkdir(parents=True, exist_ok=exist_ok)
        return path_obj
    except FileExistsError as e:
        raise QuackFileExistsError(str(path_obj), original_error=e) from e
    except PermissionError as e:
        raise QuackPermissionError(str(path_obj), "create directory", original_error=e) from e
    except Exception as e:
        raise QuackIOError(f"Failed to create directory: {e}", str(path_obj), original_error=e) from e

def _atomic_write(path: Any, content: bytes) -> Path:
    target_path = _normalize_path_param(path)
    _ensure_directory(target_path.parent)
    temp_dir = target_path.parent
    temp_file = None
    existing_mode = None
    try:
        if target_path.exists():
            existing_mode = target_path.stat().st_mode
    except OSError:
        pass
    try:
        fd, temp_path_str = tempfile.mkstemp(dir=temp_dir)
        temp_file = Path(temp_path_str)
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        if existing_mode is not None:
            try:
                os.chmod(temp_file, existing_mode)
            except OSError:
                pass
        os.replace(temp_file, target_path)
        return target_path
    except Exception as e:
        if temp_file and temp_file.exists():
            try: temp_file.unlink()
            except OSError: pass
        raise QuackIOError(f"Atomic write failed: {e}", str(target_path), original_error=e) from e

def _find_files_by_content(directory: Any, text_pattern: str, recursive: bool = True) -> list[Path]:
    try:
        regex = re.compile(text_pattern)
    except re.error as e:
        raise QuackIOError(f"Invalid regex: {e}", str(directory)) from e
    dir_path = _normalize_path_param(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    matches = []
    iterator = dir_path.rglob("*") if recursive else dir_path.glob("*")
    for p in iterator:
        if not p.is_file(): continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                if regex.search(f.read()):
                    matches.append(p)
        except OSError:
            continue
    return matches