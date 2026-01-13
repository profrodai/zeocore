# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/file_ops.py
# module: quack_core.core.fs._internal.file_ops
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, directory_ops.py, disk.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: f4879df3
# === QV-LLM:END ===

import os
import re
import tempfile
from pathlib import Path
from quack_core.core.fs._internal.directory_ops import _ensure_directory


def _get_unique_filename(directory: Path, filename: str, raise_if_exists: bool = False) -> Path:
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty")
    path = directory / filename
    if not path.exists():
        return path
    if raise_if_exists:
        raise FileExistsError(f"File already exists: {path}")
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _read_file_text(path: Path, encoding: str = "utf-8") -> str:
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def _read_file_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _write_file_text(path: Path, content: str, encoding: str = "utf-8") -> Path:
    _ensure_directory(path.parent)
    with open(path, "w", encoding=encoding) as f:
        f.write(content)
    return path


def _write_file_bytes(path: Path, content: bytes) -> Path:
    _ensure_directory(path.parent)
    with open(path, "wb") as f:
        f.write(content)
    return path


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
            try:
                temp_file.unlink()
            except OSError:
                pass
        raise IOError(f"Atomic write failed: {e}") from e


def _find_files_by_content(directory: Path, text_pattern: str, recursive: bool = True) -> list[Path]:
    try:
        regex = re.compile(text_pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex: {e}") from e

    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    matches = []
    iterator = directory.rglob("*") if recursive else directory.glob("*")
    for p in iterator:
        if not p.is_file(): continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                if regex.search(f.read()):
                    matches.append(p)
        except OSError:
            # We skip individual file read errors (e.g. locks), but not directory errors
            continue
    return matches