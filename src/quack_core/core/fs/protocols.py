# quack-core/src/quack_core/fs/protocols.py
from typing import Any, Protocol


class HasValue(Protocol):
    """Protocol for objects with a value or unwrap method."""

    def value(self) -> Any:
        """Return the value inside the object."""
        ...


class HasUnwrap(Protocol):
    """Protocol for objects with an unwrap method."""

    def unwrap(self) -> Any:
        """Unwrap the value inside the object."""
        ...


class BaseResult(Protocol):
    """Protocol for result objects."""

    success: bool
