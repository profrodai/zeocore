# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/protocols.py
# module: quack_core.core.fs.protocols
# role: protocols
# neighbors: __init__.py, plugin.py, results.py
# exports: HasValue, HasUnwrap, BaseResult
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

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
