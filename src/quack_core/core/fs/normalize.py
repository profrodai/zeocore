# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/normalize.py
# module: quack_core.core.fs.normalize
# role: module
# neighbors: __init__.py, protocols.py, plugin.py, results.py
# exports: coerce_path, coerce_path_str, safe_path_str
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Input normalization logic.
This module is the Single Source of Truth for coercing inputs into Paths.
It does NOT depend on _internal or service.
"""
import os
from pathlib import Path
from typing import Any, Optional
from quack_core.core.fs.protocols import HasData, HasPath, HasUnwrap, HasValue, FsPathLike


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

    # Fail fast on failed Results
    if hasattr(obj, "success") and not getattr(obj, "success", True):
        raise ValueError(f"Cannot extract path from failed Result object: {obj}")

    # Explicit unwrap methods
    if isinstance(obj, HasValue):
        return _extract_path_str(obj.value())
    if isinstance(obj, HasUnwrap):
        return _extract_path_str(obj.unwrap())

    # Result attributes (HasData / HasPath)
    if isinstance(obj, HasData) and obj.data is not None:
        if obj.data is not obj:
            try:
                return _extract_path_str(obj.data)
            except (TypeError, ValueError):
                pass

    if isinstance(obj, HasPath) and obj.path is not None:
        return _extract_path_str(obj.path)

    raise TypeError(f"Could not coerce object of type {type(obj)} to path string")


def coerce_path(obj: FsPathLike, base_dir: Path | None = None) -> Path:
    """
    Strictly coerce input to a pathlib.Path and optionally anchor to base_dir.
    Raises TypeError/ValueError on failure.
    """
    try:
        s = _extract_path_str(obj)
        path = Path(s)

        if base_dir:
            # Handle user home expansion
            path = path.expanduser()

            # If path is absolute, return as is (doctrine: absolute paths override base_dir context)
            if path.is_absolute():
                return path.resolve()

            # Anchor to base_dir
            # Resolve to handle ../ backtracking if needed, but stay anchored?
            # Simple join is safest default for strict anchoring.
            return (base_dir / path).resolve()

        return path
    except (TypeError, ValueError) as e:
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