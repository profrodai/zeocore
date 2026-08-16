# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/serialization.py
# === QV-LLM:END ===


"""
Shared JSON serialization utilities.

Fix #2: Single source of truth for JSON-safe validation and normalization.
Prevents drift between ToolContext metadata validation and ToolRunner output serialization.
"""

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


def normalize_for_json(
    data: Any,
    path: str = "value",
    allow_pydantic: bool = True,
    allow_string_fallback: bool = False,
    logger: Any | None = None,
) -> Any:
    """
    Normalize data to JSON-serializable form.

    Single source of truth for JSON serialization (Fix #2).
    Used by both ToolContext metadata validation and ToolRunner output serialization.

    Args:
        data: Value to normalize
        path: Current path for error messages (e.g., "metadata.user.name")
        allow_pydantic: If True, accept Pydantic BaseModel instances
        allow_string_fallback: If True, stringify unknown objects (use carefully)
        logger: Optional logger for warnings

    Returns:
        JSON-safe value

    Raises:
        TypeError: If data is not JSON-serializable and allow_string_fallback=False

    Examples:
        >>> normalize_for_json(Path("/tmp"))
        '/tmp'

        >>> normalize_for_json(datetime(2025, 1, 1))
        '2025-01-01T00:00:00'

        >>> class Status(Enum):
        ...     ACTIVE = "active"
        >>> normalize_for_json(Status.ACTIVE)
        'active'
    """
    # Primitives - already JSON-safe
    if isinstance(data, (str, int, float, bool, type(None))):
        return data

    # Pydantic models (Fix #3 - strict isinstance check)
    if allow_pydantic:
        # Import here to avoid circular dependency
        try:
            from pydantic import BaseModel

            if isinstance(data, BaseModel):
                return data.model_dump()
        except ImportError:
            pass  # Pydantic not available, continue

    # Dataclasses
    if is_dataclass(data):
        return asdict(data)

    # Safe auto-conversions (common types)
    if isinstance(data, Path):
        return str(data)

    if isinstance(data, datetime):
        return data.isoformat()

    if isinstance(data, Enum):
        return data.value

    # Sets → lists
    if isinstance(data, set):
        if logger:
            logger.debug(f"Converting set to list at {path}")
        return [
            normalize_for_json(
                item, f"{path}[{i}]", allow_pydantic, allow_string_fallback, logger
            )
            for i, item in enumerate(data)
        ]

    # Lists/tuples - recurse
    if isinstance(data, (list, tuple)):
        return [
            normalize_for_json(
                item, f"{path}[{i}]", allow_pydantic, allow_string_fallback, logger
            )
            for i, item in enumerate(data)
        ]

    # Dicts - enforce string keys and recurse
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if not isinstance(k, str):
                if allow_string_fallback:
                    if logger:
                        logger.warning(
                            f"Dict key {k!r} at {path} is not a string. Converting to string."
                        )
                    k = str(k)
                else:
                    raise TypeError(
                        f"Dict key at {path}[{k!r}] must be string, got {type(k).__name__}. "
                        f"JSON requires string keys."
                    )
            result[k] = normalize_for_json(
                v, f"{path}.{k}", allow_pydantic, allow_string_fallback, logger
            )
        return result

    # Unknown type - reject or stringify
    if not allow_string_fallback:
        raise TypeError(
            f"Value at {path} is not JSON-serializable: "
            f"type={type(data).__name__}, value={data!r}. "
            f"Allowed: primitives, Path, datetime, Enum, lists, dicts"
            + (", Pydantic BaseModel" if allow_pydantic else "")
            + ". Convert to supported type or use allow_string_fallback=True."
        )

    # Fallback: stringify (only if explicitly allowed)
    if logger:
        logger.warning(
            f"Serializing {type(data).__name__} at {path} to string (may lose structure)"
        )
    try:
        return str(data)
    except Exception as e:
        raise ValueError(
            f"Cannot serialize value at {path} (type={type(data).__name__}): {e}"
        ) from e


def is_json_safe(data: Any, allow_pydantic: bool = True) -> bool:
    """
    Check if data is JSON-serializable without modifying it.

    Args:
        data: Value to check
        allow_pydantic: If True, accept Pydantic BaseModel instances

    Returns:
        True if JSON-safe, False otherwise

    Example:
        >>> is_json_safe({"name": "test", "count": 42})
        True

        >>> is_json_safe({"path": Path("/tmp")})
        True  # Path is auto-converted

        >>> is_json_safe({"obj": object()})
        False
    """
    try:
        normalize_for_json(
            data, allow_pydantic=allow_pydantic, allow_string_fallback=False
        )
        return True
    except (TypeError, ValueError):
        return False
