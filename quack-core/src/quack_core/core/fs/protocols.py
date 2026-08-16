# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/protocols.py
# === QV-LLM:END ===

from os import PathLike
from pathlib import Path
from typing import Any, Protocol, TypeAlias, runtime_checkable


@runtime_checkable
class HasValue(Protocol):
    def value(self) -> Any: ...  # noqa: ANN401 -- genuinely dynamic: Result-wrapper duck-type, unwrapped value type is unknowable at this boundary


@runtime_checkable
class HasUnwrap(Protocol):
    def unwrap(self) -> Any: ...  # noqa: ANN401 -- genuinely dynamic: Result-wrapper duck-type, unwrapped value type is unknowable at this boundary


@runtime_checkable
class HasPath(Protocol):
    path: Path | None


@runtime_checkable
class HasData(Protocol):
    data: Any


class BaseResult(Protocol):
    """Base protocol for result objects."""

    # ok is canonical
    ok: bool


# Standard public input type for the entire service layer
FsPathLike: TypeAlias = (
    str | Path | PathLike[str] | HasPath | HasData | HasValue | HasUnwrap | BaseResult
)
