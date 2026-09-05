"""Frozen contracts for governed, durable read-only observations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from zeo_core.contracts.connections.errors import NormalizedError
from zeo_core.contracts.connections.identity import (
    AuthorizationId,
    ConnectionId,
    ConnectorRevisionId,
    IdempotencyKey,
    ObservationArtifactRef,
    ObservationId,
    OperationId,
    OrganizationId,
)


class ObservationState(StrEnum):
    """A read is claimed before dispatch and then finishes without ambiguity."""

    CLAIMED = "CLAIMED"
    CONFIRMED = "CONFIRMED"
    FAILED_SAFE = "FAILED_SAFE"


class ObservationArtifact(BaseModel):
    """Secret-free metadata for bounded bytes stored outside the receipt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_ref: ObservationArtifactRef
    content_sha256: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(..., ge=0)
    media_type: str = Field(..., min_length=1, max_length=200)


class ObservationRecord(BaseModel):
    """Durable idempotency claim for one admitted read operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: ObservationId
    organization_id: OrganizationId
    connection_id: ConnectionId
    connector_revision: ConnectorRevisionId
    operation_id: OperationId
    authorization_id: AuthorizationId
    idempotency_key: IdempotencyKey
    authorization_digest: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    request_digest: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    state: ObservationState
    created_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def _completion_matches_state(self) -> ObservationRecord:
        if self.state is ObservationState.CLAIMED and self.completed_at is not None:
            raise ValueError("a claimed observation must not be completed")
        if self.state is not ObservationState.CLAIMED and self.completed_at is None:
            raise ValueError("a terminal observation must carry completed_at")
        if self.completed_at is not None and self.completed_at < self.created_at:
            raise ValueError("completed_at must not precede created_at")
        return self


class ObservationReceipt(BaseModel):
    """Immutable, bounded, sanitized result of one read operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: ObservationId
    organization_id: OrganizationId
    connection_id: ConnectionId
    final_state: ObservationState
    request_digest: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    result_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    inline_result: JsonValue | None = None
    artifact: ObservationArtifact | None = None
    normalized_error: NormalizedError | None = None
    recorded_at: datetime

    @model_validator(mode="after")
    def _shape_matches_state(self) -> ObservationReceipt:
        has_inline = self.inline_result is not None
        has_artifact = self.artifact is not None
        if self.final_state is ObservationState.CLAIMED:
            raise ValueError("a receipt cannot represent an in-flight observation")
        if self.final_state is ObservationState.CONFIRMED:
            if has_inline == has_artifact:
                raise ValueError(
                    "a confirmed observation requires exactly one result representation"
                )
            if self.result_digest is None or self.normalized_error is not None:
                raise ValueError(
                    "a confirmed observation requires a digest and forbids an error"
                )
        elif (
            has_inline
            or has_artifact
            or self.result_digest is not None
            or self.normalized_error is None
        ):
            raise ValueError(
                "a failed-safe observation requires only a normalized error"
            )
        if self.normalized_error is not None and self.normalized_error.provider_detail:
            raise ValueError("provider detail is forbidden on observation receipts")
        return self


__all__ = [
    "ObservationArtifact",
    "ObservationReceipt",
    "ObservationRecord",
    "ObservationState",
]
