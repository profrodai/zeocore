from os import PathLike
from pathlib import Path
from typing import Any, Protocol, TypeAlias, runtime_checkable

@runtime_checkable
class HasValue(Protocol):
    def value(self) -> Any: ...

@runtime_checkable
class HasUnwrap(Protocol):
    def unwrap(self) -> Any: ...

@runtime_checkable
class HasPath(Protocol):
    path: Path | None

@runtime_checkable
class HasData(Protocol):
    data: Any

class BaseResult(Protocol):
    success: bool

# Standard public input type for the entire service layer
FsPathLike: TypeAlias = str | Path | PathLike | HasPath | HasData | HasValue | HasUnwrap | BaseResult