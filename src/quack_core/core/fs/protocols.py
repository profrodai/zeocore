# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/protocols.py
# module: quack_core.core.fs.protocols
# role: protocols
# neighbors: __init__.py, plugin.py, results.py
# exports: HasValue, HasUnwrap, HasPath, HasData, BaseResult
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from os import PathLike
from pathlib import Path
from typing import Any, Protocol, TypeAlias, runtime_checkable

@runtime_checkable
class HasValue(Protocol):
    """Protocol for objects with a value method."""
    def value(self) -> Any: ...

@runtime_checkable
class HasUnwrap(Protocol):
    """Protocol for objects with an unwrap method."""
    def unwrap(self) -> Any: ...

@runtime_checkable
class HasPath(Protocol):
    """Protocol for objects with a path attribute."""
    path: Path | None

@runtime_checkable
class HasData(Protocol):
    """Protocol for objects with a data attribute."""
    data: Any

class BaseResult(Protocol):
    """Protocol for result objects."""
    success: bool

# Standard public input type for the entire service layer
FsPathLike: TypeAlias = str | Path | PathLike | HasPath | HasData | HasValue | HasUnwrap | BaseResult