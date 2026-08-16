# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/serialization.py
# === QV-LLM:END ===


"""
Shared JSON serialization utilities.

Fix #2: Single source of truth for JSON-safe validation and normalization.
Prevents drift between ToolContext metadata validation and ToolRunner output
serialization.
"""

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


_SCALAR_CONVERTERS: tuple[tuple[type, Any], ...] = (
    (Path, str),
    (datetime, lambda d: d.isoformat()),
    (Enum, lambda d: d.value),
)


def _normalize_scalar(data: Any) -> tuple[bool, Any]:
    """
    Try each safe scalar auto-conversion (Path, datetime, Enum) in order.
    Returns (True, converted_value) on the first match, else (False, None).
    Extracted from normalize_for_json for the same C901 reason as
    _normalize_sequence.
    """
    for scalar_type, convert in _SCALAR_CONVERTERS:
        if isinstance(data, scalar_type):
            return True, convert(data)
    return False, None


def _normalize_sequence(
    data: set | list | tuple,
    path: str,
    allow_pydantic: bool,
    allow_string_fallback: bool,
    logger: Any | None,
) -> list[Any]:
    """
    Recurse over a set/list/tuple, normalizing each element. Extracted from
    normalize_for_json to keep its own branch count under the C901
    threshold; behavior (including the set->list debug log) is unchanged.
    """
    if isinstance(data, set) and logger:
        logger.debug(f"Converting set to list at {path}")
    return [
        normalize_for_json(
            item, f"{path}[{i}]", allow_pydantic, allow_string_fallback, logger
        )
        for i, item in enumerate(data)
    ]


def _normalize_dict_key(
    k: Any, path: str, allow_string_fallback: bool, logger: Any | None
) -> str:
    """
    Coerce or reject a single dict key per allow_string_fallback. Extracted
    from normalize_for_json for the same C901 reason as _normalize_sequence.
    """
    if isinstance(k, str):
        return k
    if allow_string_fallback:
        if logger:
            logger.warning(
                f"Dict key {k!r} at {path} is not a string. Converting to string."
            )
        return str(k)
    raise TypeError(
        f"Dict key at {path}[{k!r}] must be string, got {type(k).__name__}. "
        f"JSON requires string keys."
    )


def _normalize_dict(
    data: dict[Any, Any],
    path: str,
    allow_pydantic: bool,
    allow_string_fallback: bool,
    logger: Any | None,
) -> dict[str, Any]:
    """
    Enforce string keys and recurse over a dict's values. Extracted from
    normalize_for_json for the same C901 reason as _normalize_sequence.
    """
    result = {}
    for k, v in data.items():
        key = _normalize_dict_key(k, path, allow_string_fallback, logger)
        result[key] = normalize_for_json(
            v, f"{path}.{key}", allow_pydantic, allow_string_fallback, logger
        )
    return result


def _normalize_unknown(
    data: Any,
    path: str,
    allow_pydantic: bool,
    allow_string_fallback: bool,
    logger: Any | None,
) -> Any:
    """
    Handle a type normalize_for_json does not otherwise recognize: reject it,
    or stringify it if allow_string_fallback permits. Extracted from
    normalize_for_json for the same C901 reason as _normalize_sequence.
    """
    if not allow_string_fallback:
        raise TypeError(
            f"Value at {path} is not JSON-serializable: "
            f"type={type(data).__name__}, value={data!r}. "
            f"Allowed: primitives, Path, datetime, Enum, lists, dicts"
            + (", Pydantic BaseModel" if allow_pydantic else "")
            + ". Convert to supported type or use allow_string_fallback=True."
        )

    if logger:
        logger.warning(
            f"Serializing {type(data).__name__} at {path} to string "
            "(may lose structure)"
        )
    try:
        return str(data)
    except Exception as e:
        raise ValueError(
            f"Cannot serialize value at {path} (type={type(data).__name__}): {e}"
        ) from e


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

    # Safe auto-conversions (common types: Path, datetime, Enum)
    converted, value = _normalize_scalar(data)
    if converted:
        return value

    # Sets/lists/tuples - recurse
    if isinstance(data, (set, list, tuple)):
        return _normalize_sequence(
            data, path, allow_pydantic, allow_string_fallback, logger
        )

    # Dicts - enforce string keys and recurse
    if isinstance(data, dict):
        return _normalize_dict(
            data, path, allow_pydantic, allow_string_fallback, logger
        )

    # Unknown type - reject or stringify
    return _normalize_unknown(data, path, allow_pydantic, allow_string_fallback, logger)


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
