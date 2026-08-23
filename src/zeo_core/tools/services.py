"""Generic runner-supplied services on ToolContext. Not Sovereign Agent fields."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from zeo_core.contracts.artifacts.refs import ArtifactRef


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Default wall clock. Runners may inject a frozen clock in tests."""

    def now(self) -> datetime:
        return datetime.now(UTC)


@runtime_checkable
class Cancellation(Protocol):
    def is_cancelled(self) -> bool: ...

    def deadline(self) -> datetime | None: ...


class NeverCancelled:
    def is_cancelled(self) -> bool:
        return False

    def deadline(self) -> datetime | None:
        return None


@runtime_checkable
class ArtifactSink(Protocol):
    def emit(self, ref: ArtifactRef) -> None: ...


class RecordingArtifactSink:
    """In-memory sink a runner may persist after invocation."""

    def __init__(self) -> None:
        self.refs: list[ArtifactRef] = []

    def emit(self, ref: ArtifactRef) -> None:
        self.refs.append(ref)


SERVICE_CLOCK = "clock"
SERVICE_CANCELLATION = "cancellation"
SERVICE_ARTIFACTS = "artifacts"
SERVICE_REDACTION_PATHS = "redaction_paths"
