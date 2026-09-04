"""Immutable contracts for policy-aware capability execution."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OperationMode(StrEnum):
    """Safety class understood by the first resilient-runner tranche."""

    READ_ONLY = "read_only"
    ADVISORY = "advisory"
    EFFECTFUL = "effectful"


class FailureKind(StrEnum):
    """Normalized attempt failure classification."""

    TIMEOUT = "timeout"
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    MALFORMED_RESPONSE = "malformed_response"
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    AUTHENTICATION = "authentication"
    CANCELLED = "cancelled"
    PERMANENT = "permanent"


class AttemptOutcome(StrEnum):
    """What happened during one started attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExecutionOutcome(StrEnum):
    """Terminal result of the bounded runner."""

    SUCCEEDED = "succeeded"
    FAILED_SAFE = "failed_safe"
    EXHAUSTED = "exhausted"
    CANCELLED = "cancelled"
    REFUSED = "refused"


class ExecutionMode(StrEnum):
    """Truthful label for the target that produced a result."""

    LIVE = "live"
    SIMULATED = "simulated"
    NONE = "none"


_TARGET_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,127}$")
_NEVER_RETRY = frozenset(
    {
        FailureKind.VALIDATION,
        FailureKind.AUTHORIZATION,
        FailureKind.AUTHENTICATION,
        FailureKind.CANCELLED,
        FailureKind.PERMANENT,
    }
)


class ExecutionPolicy(BaseModel):
    """One explicit total budget and attempt plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation_mode: OperationMode = OperationMode.READ_ONLY
    total_timeout_seconds: float = Field(gt=0)
    attempt_timeout_seconds: float = Field(gt=0)
    attempt_targets: tuple[str, ...]
    backoff_seconds: tuple[float, ...] = ()
    jitter_fraction: float = Field(default=0, ge=0, le=1)
    retryable_failures: frozenset[FailureKind] = frozenset(
        {
            FailureKind.TIMEOUT,
            FailureKind.TRANSIENT,
            FailureKind.RATE_LIMIT,
        }
    )
    allow_simulated: bool = False
    cancellation_poll_seconds: float = Field(default=0.1, gt=0)

    @field_validator("attempt_targets")
    @classmethod
    def _attempt_targets(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("attempt_targets must contain at least one target")
        if any(not _TARGET_ID.fullmatch(target) for target in value):
            raise ValueError("attempt target IDs must be non-empty safe identifiers")
        return value

    @field_validator("backoff_seconds")
    @classmethod
    def _backoff_non_negative(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if any(delay < 0 for delay in value):
            raise ValueError("backoff_seconds cannot contain negative delays")
        return value

    @model_validator(mode="after")
    def _coherent(self) -> ExecutionPolicy:
        if len(self.backoff_seconds) > len(self.attempt_targets) - 1:
            raise ValueError(
                "backoff_seconds cannot exceed the number of attempt transitions"
            )
        forbidden = self.retryable_failures & _NEVER_RETRY
        if forbidden:
            names = ", ".join(sorted(kind.value for kind in forbidden))
            raise ValueError(f"failures can never be retryable: {names}")
        return self

    @property
    def max_attempts(self) -> int:
        """The explicit plan length is the declared call bound."""

        return len(self.attempt_targets)

    def backoff_after(self, attempt_number: int) -> float:
        """Return configured delay after a one-based attempt number."""

        index = attempt_number - 1
        if index >= len(self.backoff_seconds):
            return 0.0
        return self.backoff_seconds[index]


class AttemptRecord(BaseModel):
    """Sanitized evidence for one started attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attempt_number: int = Field(ge=1)
    target_id: str
    execution_mode: ExecutionMode
    started_after_seconds: float = Field(ge=0)
    ended_after_seconds: float = Field(ge=0)
    timeout_seconds: float = Field(gt=0)
    dispatch_started: bool
    outcome: AttemptOutcome
    failure_kind: FailureKind | None = None
    machine_code: str | None = None
    backoff_before_next_seconds: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _outcome_fields(self) -> AttemptRecord:
        if self.ended_after_seconds < self.started_after_seconds:
            raise ValueError("attempt cannot end before it starts")
        if self.outcome is AttemptOutcome.SUCCEEDED:
            if self.failure_kind is not None or self.machine_code is not None:
                raise ValueError("successful attempt cannot carry failure fields")
        elif self.failure_kind is None or self.machine_code is None:
            raise ValueError("failed attempt requires normalized failure fields")
        return self


class ResilientExecutionResult(BaseModel):
    """Terminal runner result with append-only attempt evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    outcome: ExecutionOutcome
    value: Any | None = None
    attempts: tuple[AttemptRecord, ...] = ()
    selected_target_id: str | None = None
    execution_mode: ExecutionMode = ExecutionMode.NONE
    failure_kind: FailureKind | None = None
    machine_code: str | None = None
    total_elapsed_seconds: float = Field(ge=0)

    @model_validator(mode="after")
    def _terminal_shape(self) -> ResilientExecutionResult:
        if self.outcome is ExecutionOutcome.SUCCEEDED:
            if self.selected_target_id is None:
                raise ValueError("success requires selected_target_id")
            if self.execution_mode is ExecutionMode.NONE:
                raise ValueError("success requires truthful execution_mode")
            if self.failure_kind is not None or self.machine_code is not None:
                raise ValueError("success cannot carry terminal failure fields")
        else:
            if self.value is not None:
                raise ValueError("non-success result cannot carry a value")
            if self.machine_code is None:
                raise ValueError("non-success result requires machine_code")
        return self
