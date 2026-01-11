import os
import re
import tempfile
from pathlib import Path
from typing import Any
from quack_core.core.errors import QuackFileExistsError, QuackFileNotFoundError, QuackIOError
from quack_core.core.fs._internal.directory_ops import _ensure_directory

def _get_unique_filename(directory: Path, filename: str, raise_if_exists: bool = False) -> Path:
    if not directory.exists():
        raise QuackFileNotFoundError(str(directory), message="Directory does not exist")
    if not filename or not filename.strip():
        raise QuackIOError("Filename cannot be empty", str(directory))
    path = directory / filename
    if not path.exists():
        return path
    if raise_if_exists:
        raise QuackFileExistsError(str(path), message="File already exists")
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

def _atomic_write(path: Path, content: bytes) -> Path:
    _ensure_directory(path.parent)
    temp_dir = path.parent
    temp_file = None
    existing_mode = None
    try:
        if path.exists():
            existing_mode = path.stat().st_mode
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
        os.replace(temp_file, path)
        return path
    except Exception as e:
        if temp_file and temp_file.exists():
            try: temp_file.unlink()
            except OSError: pass
        raise QuackIOError(f"Atomic write failed: {e}", str(path), original_error=e) from e

def _find_files_by_content(directory: Path, text_pattern: str, recursive: bool = True) -> list[Path]:
    try:
        regex = re.compile(text_pattern)
    except re.error as e:
        raise QuackIOError(f"Invalid regex: {e}", str(directory)) from e
    if not directory.exists() or not directory.is_dir():
        return []
    matches = []
    iterator = directory.rglob("*") if recursive else directory.glob("*")
    for p in iterator:
        if not p.is_file(): continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                if regex.search(f.read()):
                    matches.append(p)
        except OSError:
            continue
    return matches