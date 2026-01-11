# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/normalize.py
# module: quack_core.core.fs.normalize
# role: module
# neighbors: __init__.py, protocols.py, plugin.py, results.py
# exports: coerce_path, coerce_path_str, safe_path_str, coerce_path_result, extract_path_from_result
# git_branch: feat/9-make-setup-work
# git_commit: f85cce5a
# === QV-LLM:END ===

"""
Input normalization logic.
This module is the Single Source of Truth for coercing inputs into Paths.
It does NOT depend on _internal or service.
"""
import os
from pathlib import Path
from typing import Any, TypeVar
from quack_core.core.fs.protocols import FsPathLike

T = TypeVar("T")


def _extract_path_str(obj: Any) -> str:
    """Core logic to extract a string path from a polymorphic input."""
    if obj is None:
        raise TypeError("Path cannot be None")

    if isinstance(obj, str):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "__fspath__"):
        return os.fspath(obj)  # type: ignore

    # Fail fast on failed Results (check 'ok' first as canonical, then 'success')
    if hasattr(obj, "ok") and not getattr(obj, "ok", True):
        raise ValueError(f"Cannot extract path from failed Result object: {obj}")
    elif hasattr(obj, "success") and not getattr(obj, "success", True):
        raise ValueError(f"Cannot extract path from failed Result object: {obj}")

    # Explicit unwrap methods
    if hasattr(obj, "value") and callable(obj.value):
        return _extract_path_str(obj.value())
    if hasattr(obj, "unwrap") and callable(obj.unwrap):
        return _extract_path_str(obj.unwrap())

    # Result attributes (HasData / HasPath)
    # Prefer 'data' if it looks path-like, else 'path'
    if hasattr(obj, "data") and obj.data is not None:
        if obj.data is not obj:
            try:
                return _extract_path_str(obj.data)
            except (TypeError, ValueError):
                pass

    if hasattr(obj, "path") and obj.path is not None:
        return _extract_path_str(obj.path)

    raise TypeError(f"Could not coerce object of type {type(obj)} to path string")


def coerce_path(obj: FsPathLike, base_dir: Path | None = None, allow_absolute: bool = False) -> Path:
    """
    Strictly coerce input to a pathlib.Path.
    If base_dir is provided, anchors relative paths to it and prevents escape.

    Args:
        obj: The input path-like object.
        base_dir: The root directory to anchor relative paths to.
        allow_absolute: If True, absolute paths outside base_dir are allowed (unsafe).
                        If False, absolute paths must be within base_dir (if provided).

    Raises:
        TypeError/ValueError on failure or sandbox violation.
    """
    try:
        s = _extract_path_str(obj)
        path = Path(s)

        # Handle user home expansion immediately
        path = path.expanduser()

        if base_dir:
            # 1. Handle Absolute Paths
            if path.is_absolute():
                if allow_absolute:
                    return path.resolve()

                # If absolute but strict sandboxing is on, ensure it is inside base_dir
                try:
                    resolved = path.resolve()
                    resolved.relative_to(base_dir)
                    return resolved
                except ValueError:
                    raise ValueError(f"Path '{path}' is outside base directory '{base_dir}' (allow_absolute=False)")

            # 2. Handle Relative Paths (Anchor to base_dir)
            resolved_path = (base_dir / path).resolve()

            # 3. Strict Sandboxing Check (escape prevention for relative paths with ..)
            try:
                resolved_path.relative_to(base_dir)
            except ValueError:
                raise ValueError(f"Path '{path}' attempts to escape base directory '{base_dir}'")

            return resolved_path

        # No base_dir context - return as is (resolved)
        return path.resolve()

    except (TypeError, ValueError) as e:
        # Re-raise known errors or wrap unknown ones
        if isinstance(e, ValueError) and "escape" in str(e):
            raise
        if isinstance(e, ValueError) and "outside base directory" in str(e):
            raise
        raise TypeError(f"Could not coerce {type(obj)} to Path: {e}") from e


def coerce_path_str(obj: FsPathLike) -> str:
    """
    Strictly coerce input to a string path.
    Raises TypeError/ValueError on failure.
    """
    return _extract_path_str(obj)


def safe_path_str(obj: Any, default: str | None = None) -> str | None:
    """
    Safely extract a string path from any object, returning a default on failure.
    Never raises.
    """
    try:
        return _extract_path_str(obj)
    except (TypeError, ValueError, AttributeError):
        return default


def coerce_path_result(obj: FsPathLike) -> Path:
    """
    Helper for standalone wrappers to extract a Path from a Result or PathLike.
    Equivalent to coerce_path but without base_dir context (used for introspection).
    """
    return coerce_path(obj)


def extract_path_from_result(obj: Any) -> Path | None:
    """
    Best-effort extraction of a Path from a result object. Returns None on failure.
    """
    try:
        return coerce_path(obj)
    except (TypeError, ValueError):
        return None