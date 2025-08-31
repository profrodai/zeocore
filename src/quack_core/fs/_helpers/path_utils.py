# quack-core/src/quack-core/fs/_helpers/path_utils.py
"""
Path utility functions that don't introduce circular dependencies.
"""
import os
from pathlib import Path
from typing import Any, TypeVar, cast

from quack_core.fs.protocols import HasUnwrap, HasValue
from quack_core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

def _normalize_path_param(path: Any) -> Path:
    """
    Normalize a path parameter to a Path object.
    
    Helper function to consistently handle different path input types,
    including DataResult and OperationResult objects.
    
    Args:
        path: Path parameter (string, Path, or any object with a 'data' attribute)
        
    Returns:
        Normalized Path object
    """
    # Check if it's a DataResult-like object with a data attribute
    if hasattr(path, "data"):
        path_content = path.data
    else:
        path_content = path

    try:
        return Path(path_content)
    except TypeError:
        return Path(str(path_content))


def _extract_path_from_result(result_obj: Any) -> str | Path:
    """
    Extract a path from any result object or path-like object.

    This function handles all types of result objects (PathResult, DataResult,
    OperationResult) and extracts the actual path component for use in path operations.

    Args:
        result_obj: Any object that might contain a path

    Returns:
        The extracted path as a string or Path object
    """
    # Handle PathResult objects (with 'path' attribute)
    if hasattr(result_obj, "path") and result_obj.path is not None:
        return result_obj.path

    # Handle DataResult objects (with 'data' attribute)
    if hasattr(result_obj, "data") and result_obj.data is not None:
        data_content = result_obj.data
        # If data itself is a path-like, return it
        if hasattr(data_content, "__fspath__") or isinstance(data_content, str):
            return data_content

    # Handle path-like objects directly
    if hasattr(result_obj, "__fspath__"):
        return result_obj

    # Handle string paths
    if isinstance(result_obj, str):
        return result_obj

    # Last resort: try string conversion
    return str(result_obj)


def _extract_path_str(obj: Any) -> str:
    """
    Extract a string path from any path-like object or result object.

    This function handles various types of objects that might be used
    as paths, including Result objects, Path objects, and strings.

    Args:
        obj: Any object that might contain or represent a path

    Returns:
        A string representation of the path

    Raises:
        TypeError: If the object cannot be converted to a path string
        ValueError: If the object is a failed Result object
    """
    # Check if it's a failed Result object
    if hasattr(obj, "success") and not getattr(obj, "success", True):
        raise ValueError(f"Cannot extract path from failed Result object: {obj}")

    # Handle Result objects with value/unwrap methods
    if hasattr(obj, "value") and callable(obj.value):
        try:
            # Recursively extract path from the unwrapped value
            return _extract_path_str(cast(HasValue, obj).value())
        except (AttributeError, TypeError, ValueError) as e:
            raise TypeError(f"Failed to extract path using value() method: {e}")

    # Alternative unwrap method naming
    if hasattr(obj, "unwrap") and callable(obj.unwrap):
        try:
            # Recursively extract path from the unwrapped value
            return _extract_path_str(cast(HasUnwrap, obj).unwrap())
        except (AttributeError, TypeError, ValueError) as e:
            raise TypeError(f"Failed to extract path using unwrap() method: {e}")

    # Handle DataResult objects with data attribute first (higher priority)
    if hasattr(obj, "data") and obj.data is not None:
        data_content = obj.data
        if isinstance(data_content, (str, Path)) or hasattr(data_content, "__fspath__"):
            return _extract_path_str(data_content)
        else:
            # Raise TypeError for non-path-like data
            raise TypeError(f"DataResult.data is not a path-like object: {type(data_content)}")

    # Handle PathResult objects with path attribute (lower priority)
    if hasattr(obj, "path") and obj.path is not None:
        return _extract_path_str(obj.path)

    # Handle os.PathLike objects (including Path)
    if hasattr(obj, "__fspath__"):
        return os.fspath(obj)

    # Handle strings
    if isinstance(obj, str):
        return obj

    # If we got here, we couldn't convert the object to a path string
    raise TypeError(
        f"Invalid path-like object: {type(obj)}. Expected str, Path, or a Result object with path data.")

def _safe_path_str(obj: Any, default: str | None = None) -> str | None :
    """
    Safely extract a string path from any object, returning a default on failure.

    This function is similar to extract_path_str, but never raises exceptions.
    Instead, it returns the default value and logs a warning when extraction fails.

    Args:
        obj: Any object that might contain or represent a path
        default: Value to return if path extraction fails

    Returns:
        The extracted path string or the default value
    """
    try:
        return _extract_path_str(obj)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to extract path: {e}. Using default: {default}")
        return default

