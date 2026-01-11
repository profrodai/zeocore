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

    # Explicit unwrap methods (using hasattr for safety)
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


def coerce_path(obj: FsPathLike, base_dir: Path | None = None) -> Path:
    """
    Strictly coerce input to a pathlib.Path.
    If base_dir is provided, anchors relative paths to it and prevents escape.
    Raises TypeError/ValueError on failure.
    """
    try:
        s = _extract_path_str(obj)
        path = Path(s)

        if base_dir:
            # Handle user home expansion first
            path = path.expanduser()

            if path.is_absolute():
                # Doctrine: Absolute paths override base_dir context (use with caution)
                return path.resolve()

            # Anchor to base_dir and resolve
            resolved_path = (base_dir / path).resolve()

            # Strict Sandboxing Check
            try:
                resolved_path.relative_to(base_dir)
            except ValueError:
                raise ValueError(f"Path '{path}' attempts to escape base directory '{base_dir}'")

            return resolved_path

        return path
    except (TypeError, ValueError) as e:
        # Re-raise known errors or wrap unknown ones
        if isinstance(e, ValueError) and "escape" in str(e):
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