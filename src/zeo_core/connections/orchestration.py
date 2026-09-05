"""Durable, fail-closed orchestration for authorized provider effects.

This module consumes the ZC0 connection contracts instead of inventing a
parallel state machine.  Its central safety property is ordering: the
DISPATCH_STARTED snapshot is committed before provider code can run.  Once
that marker exists, loss of the provider response is AMBIGUOUS and is routed
to reconciliation; it is never converted to failure and never blindly
redispatched.
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zeo_core.connections.admission import (
    ConnectorAdmissionError,
    validate_connection_admission,
    validate_operation_request,
)
from zeo_core.connections.authorization import ExactAuthorizationVerifier
from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections import (
    AuthorizationRefusalReason,
    BrokerExecutionStore,
    ConfirmationEvidence,
    Connection,
    ConnectionId,
    ConnectionStatus,
    ConnectorRevision,
    ConnectorRevisionId,
    EffectAuthorization,
    Execution,
    ExecutionId,
    ExecutionReceipt,
    ExecutionState,
    IdempotencyKey,
    NormalizedError,
    NormalizedErrorCode,
    OperationId,
    OrganizationId,
)


class DispatchDisposition(StrEnum):
    """Facts a provider adapter may establish about one dispatch."""

    CONFIRMED = "CONFIRMED"
    FAILED_SAFE = "FAILED_SAFE"


class ReconciliationDisposition(StrEnum):
    """Facts a reconciliation adapter may establish after ambiguity."""

    CONFIRMED = "CONFIRMED"
    FAILED_SAFE = "FAILED_SAFE"
    UNRESOLVED = "UNRESOLVED"


class EffectDispatchResult(BaseModel):
    """Sanitized provider result; it cannot carry a raw provider body."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    disposition: DispatchDisposition
    confirmation_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    normalized_error: NormalizedError | None = None

    @model_validator(mode="after")
    def _shape_matches_disposition(self) -> EffectDispatchResult:
        if self.normalized_error is not None and self.normalized_error.provider_detail:
            raise ValueError(
                "provider_detail is forbidden at the orchestration boundary"
            )
        if self.disposition is DispatchDisposition.CONFIRMED:
            if self.confirmation_digest is None or self.normalized_error is not None:
                raise ValueError("confirmed dispatch requires only confirmation_digest")
        elif self.confirmation_digest is not None or self.normalized_error is None:
            raise ValueError("failed-safe dispatch requires only normalized_error")
        return self


class ReconciliationResult(BaseModel):
    """Sanitized result of inspecting an already-started provider effect."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    disposition: ReconciliationDisposition
    evidence_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    confirmation_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    normalized_error: NormalizedError | None = None

    @model_validator(mode="after")
    def _shape_matches_disposition(self) -> ReconciliationResult:
        if self.normalized_error is not None and self.normalized_error.provider_detail:
            raise ValueError(
                "provider_detail is forbidden at the orchestration boundary"
            )
        if self.disposition is ReconciliationDisposition.CONFIRMED:
            if self.confirmation_digest is None or self.normalized_error is not None:
                raise ValueError(
                    "confirmed reconciliation requires confirmation_digest"
                )
        elif self.disposition is ReconciliationDisposition.FAILED_SAFE:
            if self.confirmation_digest is not None or self.normalized_error is None:
                raise ValueError("failed-safe reconciliation requires normalized_error")
        elif self.confirmation_digest is not None or self.normalized_error is not None:
            raise ValueError("unresolved reconciliation carries evidence_digest only")
        return self


@dataclass(frozen=True)
class EffectDispatchRequest:
    """Internal dispatch context.  Request bytes are deliberately repr-hidden."""

    organization_id: OrganizationId
    connection: Connection
    connector_revision: ConnectorRevision
    operation_id: OperationId
    execution_id: ExecutionId
    idempotency_key: IdempotencyKey
    request_digest: str
    request_body: bytes = field(repr=False)


class EffectDispatcher(Protocol):
    """One provider dispatch. Retry policy must remain outside this method."""

    def dispatch(self, request: EffectDispatchRequest) -> EffectDispatchResult: ...


class EffectReconciler(Protocol):
    """Inspect an ambiguous effect without issuing it again."""

    def reconcile(self, request: EffectDispatchRequest) -> ReconciliationResult: ...


@dataclass(frozen=True)
class EffectExecutionResult:
    """Secret-free orchestration result suitable for callers and logs."""

    state: ExecutionState
    execution_id: ExecutionId | None
    refusal_reason: AuthorizationRefusalReason | None = None


class EffectOrchestrator:
    """Execute one authorized effect through durable monotonic state."""

    def __init__(
        self,
        *,
        store: BrokerExecutionStore,
        verifier: ExactAuthorizationVerifier,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._verifier = verifier
        self._clock = clock or (lambda: datetime.now(UTC))
        self._last_timestamp: datetime | None = None
        self._clock_lock = threading.Lock()

    def execute(
        self,
        *,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        connector_revision: ConnectorRevisionId,
        operation_id: OperationId,
        authorization: EffectAuthorization | None,
        execution_id: ExecutionId,
        request_body: bytes,
        dispatcher: EffectDispatcher,
        reconciler: EffectReconciler,
    ) -> EffectExecutionResult:
        """Perform at most one dispatch and reconcile any uncertain outcome."""

        if authorization is None:
            return EffectExecutionResult(
                state=ExecutionState.REFUSED,
                execution_id=None,
                refusal_reason=AuthorizationRefusalReason.ABSENT,
            )
        request_digest = _digest(request_body)
        verdict = self._verifier.verify(
            authorization=authorization,
            organization_id=organization_id,
            connection_id=connection_id,
            connector_revision=connector_revision,
            operation_id=str(operation_id),
            request_digest=request_digest,
            now=self._now(),
            seen_nonces=self._store,
        )
        if not verdict.authorized:
            return self._refused_or_replayed(
                organization_id=organization_id,
                authorization=authorization,
                execution_id=execution_id,
                request_digest=request_digest,
                reason=verdict.refusal_reason,
            )

        connection, revision = self._load_admitted_surface(
            organization_id=organization_id,
            connection_id=connection_id,
            connector_revision=connector_revision,
            operation_id=operation_id,
            request_body=request_body,
            request_size=len(request_body),
        )
        execution = self._new_execution(
            organization_id=organization_id,
            authorization=authorization,
            execution_id=execution_id,
            request_digest=request_digest,
        )
        execution, claimed = self._store.claim_execution(
            organization_id=organization_id,
            nonce=authorization.nonce,
            nonce_recorded_at=self._now(),
            execution=execution,
        )
        if not claimed:
            return EffectExecutionResult(execution.state, execution.execution_id)
        execution = self._advance(execution, ExecutionState.AUTHORIZATION_VERIFIED)
        execution = self._advance(execution, ExecutionState.PREPARED)
        execution = self._advance(execution, ExecutionState.DISPATCH_STARTED)
        dispatch_started_at = execution.updated_at
        request = EffectDispatchRequest(
            organization_id=organization_id,
            connection=connection,
            connector_revision=revision,
            operation_id=authorization.operation_id,
            execution_id=execution_id,
            idempotency_key=authorization.idempotency_key,
            request_digest=request_digest,
            request_body=request_body,
        )
        try:
            dispatch_result = dispatcher.dispatch(request)
        except Exception:
            return self._record_and_reconcile(
                organization_id=organization_id,
                execution=execution,
                dispatch_started_at=dispatch_started_at,
                request=request,
                reconciler=reconciler,
            )
        if dispatch_result.disposition is DispatchDisposition.CONFIRMED:
            if dispatch_result.confirmation_digest is None:  # model invariant
                raise RuntimeError("confirmed dispatch omitted its digest")
            self._commit_success(
                organization_id=organization_id,
                execution=execution,
                dispatch_started_at=dispatch_started_at,
                confirmation_digest=dispatch_result.confirmation_digest,
            )
            return EffectExecutionResult(ExecutionState.SUCCEEDED, execution_id)
        if dispatch_result.normalized_error is None:  # model invariant
            raise RuntimeError("failed-safe dispatch omitted its error")
        self._commit_failed_safe(
            organization_id=organization_id,
            execution=execution,
            dispatch_started_at=dispatch_started_at,
            normalized_error=dispatch_result.normalized_error,
        )
        return EffectExecutionResult(ExecutionState.FAILED_SAFE, execution_id)

    def _refused_or_replayed(
        self,
        *,
        organization_id: OrganizationId,
        authorization: EffectAuthorization,
        execution_id: ExecutionId,
        request_digest: str,
        reason: AuthorizationRefusalReason | None,
    ) -> EffectExecutionResult:
        if reason is None:  # structurally unreachable by AuthorizationVerdict
            raise RuntimeError("refused verdict omitted its reason")
        if reason is AuthorizationRefusalReason.REPLAYED:
            existing = self._store.get_execution_by_idempotency(
                organization_id=organization_id,
                connection_id=authorization.connection_id,
                connector_revision=authorization.connector_revision,
                operation_id=str(authorization.operation_id),
                idempotency_key=str(authorization.idempotency_key),
            )
            if existing is not None:
                return EffectExecutionResult(existing.state, existing.execution_id)
        return self._persist_refusal(
            organization_id=organization_id,
            authorization=authorization,
            execution_id=execution_id,
            request_digest=request_digest,
            reason=reason,
        )

    def _persist_refusal(
        self,
        *,
        organization_id: OrganizationId,
        authorization: EffectAuthorization,
        execution_id: ExecutionId,
        request_digest: str,
        reason: AuthorizationRefusalReason,
    ) -> EffectExecutionResult:
        execution = self._new_execution(
            organization_id=organization_id,
            authorization=authorization,
            execution_id=execution_id,
            request_digest=request_digest,
        )
        self._store.save_execution(organization_id=organization_id, execution=execution)
        completed_at = self._now_after(execution.updated_at)
        refused = execution.model_copy(
            update={
                "state": ExecutionState.REFUSED,
                "updated_at": completed_at,
                "completed_at": completed_at,
            }
        )
        receipt = ExecutionReceipt(
            execution_id=execution_id,
            organization_id=organization_id,
            connection_id=authorization.connection_id,
            final_state=ExecutionState.REFUSED,
            normalized_error=NormalizedError(
                code=NormalizedErrorCode.REQUEST_REFUSED,
                message=f"authorization refused: {reason.value}",
            ),
            recorded_at=refused.completed_at,
        )
        self._store.commit_outcome(
            organization_id=organization_id, execution=refused, receipt=receipt
        )
        return EffectExecutionResult(ExecutionState.REFUSED, execution_id, reason)

    def _load_admitted_surface(
        self,
        *,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        connector_revision: ConnectorRevisionId,
        operation_id: OperationId,
        request_body: bytes,
        request_size: int,
    ) -> tuple[Connection, ConnectorRevision]:
        connection = self._store.get_connection(
            organization_id=organization_id,
            connection_id=connection_id,
        )
        if connection is None or connection.status is not ConnectionStatus.ACTIVE:
            raise EffectPreflightError("connection is not active in organization")
        if connection.connector_revision != connector_revision:
            raise EffectPreflightError(
                "connection revision does not match authorization"
            )
        revision = self._store.get_connector_revision(
            organization_id=organization_id,
            revision_id=connector_revision,
        )
        if revision is None:
            raise EffectPreflightError("connector revision is unavailable")
        if request_size > revision.request_size_limit_bytes:
            raise EffectPreflightError("request exceeds connector revision size limit")
        try:
            validate_connection_admission(connection=connection, revision=revision)
            validate_operation_request(
                revision=revision,
                operation_id=operation_id,
                request_body=request_body,
            )
        except ConnectorAdmissionError as error:
            raise EffectPreflightError(
                "connector admission refused execution"
            ) from error
        operation = next(
            (item for item in revision.operations if item.operation_id == operation_id),
            None,
        )
        if (
            operation is None
            or operation_id not in connection.exposed_business_operations
        ):
            raise EffectPreflightError("business operation is not exposed")
        if operation.effect is EffectKind.READ:
            raise EffectPreflightError(
                "read-only operations do not use effect orchestration"
            )
        return connection, revision

    def _new_execution(
        self,
        *,
        organization_id: OrganizationId,
        authorization: EffectAuthorization,
        execution_id: ExecutionId,
        request_digest: str,
    ) -> Execution:
        created_at = self._now()
        return Execution(
            execution_id=execution_id,
            organization_id=organization_id,
            connection_id=authorization.connection_id,
            connector_revision=authorization.connector_revision,
            operation_id=authorization.operation_id,
            authorization_id=authorization.authorization_id,
            idempotency_key=authorization.idempotency_key,
            authorization_digest=_digest(authorization.model_dump_json().encode()),
            request_digest=request_digest,
            state=ExecutionState.CREATED,
            created_at=created_at,
            updated_at=created_at,
        )

    def _advance(self, execution: Execution, state: ExecutionState) -> Execution:
        advanced = execution.model_copy(
            update={"state": state, "updated_at": self._now_after(execution.updated_at)}
        )
        self._store.save_execution(
            organization_id=execution.organization_id, execution=advanced
        )
        return advanced

    def _record_and_reconcile(
        self,
        *,
        organization_id: OrganizationId,
        execution: Execution,
        dispatch_started_at: datetime,
        request: EffectDispatchRequest,
        reconciler: EffectReconciler,
    ) -> EffectExecutionResult:
        ambiguous_at = self._now_after(execution.updated_at)
        ambiguous = execution.model_copy(
            update={"state": ExecutionState.AMBIGUOUS, "updated_at": ambiguous_at}
        )
        ambiguity_error = NormalizedError(
            code=NormalizedErrorCode.RESULT_AMBIGUOUS,
            message="provider dispatch started but positive outcome is unknown",
        )
        ambiguous_receipt = ExecutionReceipt(
            execution_id=execution.execution_id,
            organization_id=organization_id,
            connection_id=execution.connection_id,
            final_state=ExecutionState.AMBIGUOUS,
            normalized_error=ambiguity_error,
            recorded_at=ambiguous_at,
            dispatch_started_at=dispatch_started_at,
        )
        self._store.commit_outcome(
            organization_id=organization_id,
            execution=ambiguous,
            receipt=ambiguous_receipt,
        )
        try:
            reconciliation = reconciler.reconcile(request)
        except Exception:
            reconciliation = None
        if reconciliation is None:
            self._append_unresolved(
                organization_id=organization_id,
                execution=ambiguous,
                dispatch_started_at=dispatch_started_at,
                evidence_digest=hashlib.sha256(
                    b"reconciliation-unavailable"
                ).hexdigest(),
            )
            return EffectExecutionResult(
                ExecutionState.AMBIGUOUS, execution.execution_id
            )
        if reconciliation.disposition is ReconciliationDisposition.CONFIRMED:
            if reconciliation.confirmation_digest is None:  # model invariant
                raise RuntimeError("confirmed reconciliation omitted its digest")
            self._commit_success(
                organization_id=organization_id,
                execution=ambiguous,
                dispatch_started_at=dispatch_started_at,
                confirmation_digest=reconciliation.confirmation_digest,
                reconciliation_digest=reconciliation.evidence_digest,
                ambiguous_recorded_at=ambiguous_at,
            )
            return EffectExecutionResult(
                ExecutionState.SUCCEEDED, execution.execution_id
            )
        if reconciliation.disposition is ReconciliationDisposition.FAILED_SAFE:
            if reconciliation.normalized_error is None:  # model invariant
                raise RuntimeError("failed-safe reconciliation omitted its error")
            self._commit_failed_safe(
                organization_id=organization_id,
                execution=ambiguous,
                dispatch_started_at=dispatch_started_at,
                normalized_error=reconciliation.normalized_error,
                reconciliation_digest=reconciliation.evidence_digest,
                ambiguous_recorded_at=ambiguous_at,
            )
            return EffectExecutionResult(
                ExecutionState.FAILED_SAFE, execution.execution_id
            )
        self._append_unresolved(
            organization_id=organization_id,
            execution=ambiguous,
            dispatch_started_at=dispatch_started_at,
            evidence_digest=reconciliation.evidence_digest,
        )
        return EffectExecutionResult(ExecutionState.AMBIGUOUS, execution.execution_id)

    def _commit_success(
        self,
        *,
        organization_id: OrganizationId,
        execution: Execution,
        dispatch_started_at: datetime,
        confirmation_digest: str,
        reconciliation_digest: str | None = None,
        ambiguous_recorded_at: datetime | None = None,
    ) -> None:
        completed_at = self._now_after(execution.updated_at)
        succeeded = execution.model_copy(
            update={
                "state": ExecutionState.SUCCEEDED,
                "updated_at": completed_at,
                "completed_at": completed_at,
            }
        )
        evidence: ConfirmationEvidence = self._store.new_confirmation_evidence(
            organization_id=organization_id,
            execution_id=execution.execution_id,
            observed_at=completed_at,
            confirmation_digest=confirmation_digest,
        )
        receipt = ExecutionReceipt(
            execution_id=execution.execution_id,
            organization_id=organization_id,
            connection_id=execution.connection_id,
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=completed_at,
            dispatch_started_at=dispatch_started_at,
            resolved_at=completed_at if ambiguous_recorded_at is not None else None,
            confirmation_evidence_ref=evidence.evidence_ref,
            reconciliation_evidence=reconciliation_digest,
            resolves_ambiguous_recorded_at=ambiguous_recorded_at,
        )
        self._store.commit_outcome(
            organization_id=organization_id,
            execution=succeeded,
            receipt=receipt,
            evidence=evidence,
        )

    def _commit_failed_safe(
        self,
        *,
        organization_id: OrganizationId,
        execution: Execution,
        dispatch_started_at: datetime,
        normalized_error: NormalizedError,
        reconciliation_digest: str | None = None,
        ambiguous_recorded_at: datetime | None = None,
    ) -> None:
        completed_at = self._now_after(execution.updated_at)
        failed = execution.model_copy(
            update={
                "state": ExecutionState.FAILED_SAFE,
                "updated_at": completed_at,
                "completed_at": completed_at,
            }
        )
        receipt = ExecutionReceipt(
            execution_id=execution.execution_id,
            organization_id=organization_id,
            connection_id=execution.connection_id,
            final_state=ExecutionState.FAILED_SAFE,
            normalized_error=normalized_error,
            recorded_at=completed_at,
            dispatch_started_at=dispatch_started_at,
            resolved_at=completed_at if ambiguous_recorded_at is not None else None,
            reconciliation_evidence=reconciliation_digest,
            resolves_ambiguous_recorded_at=ambiguous_recorded_at,
        )
        self._store.commit_outcome(
            organization_id=organization_id, execution=failed, receipt=receipt
        )

    def _append_unresolved(
        self,
        *,
        organization_id: OrganizationId,
        execution: Execution,
        dispatch_started_at: datetime,
        evidence_digest: str,
    ) -> None:
        recorded_at = self._now_after(execution.updated_at)
        receipt = ExecutionReceipt(
            execution_id=execution.execution_id,
            organization_id=organization_id,
            connection_id=execution.connection_id,
            final_state=ExecutionState.AMBIGUOUS,
            normalized_error=NormalizedError(
                code=NormalizedErrorCode.RESULT_AMBIGUOUS,
                message="reconciliation did not establish the provider effect",
            ),
            recorded_at=recorded_at,
            dispatch_started_at=dispatch_started_at,
            reconciliation_attempt_evidence=evidence_digest,
        )
        self._store.save_receipt(organization_id=organization_id, receipt=receipt)

    def _now(self) -> datetime:
        return self._timestamp_after(None)

    def _now_after(self, previous: datetime) -> datetime:
        return self._timestamp_after(previous)

    def _timestamp_after(self, previous: datetime | None) -> datetime:
        with self._clock_lock:
            value = self._clock()
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise TypeError("clock must return a timezone-aware datetime")
            floors = tuple(
                item for item in (self._last_timestamp, previous) if item is not None
            )
            if floors and value <= max(floors):
                value = max(floors) + timedelta(microseconds=1)
            self._last_timestamp = value
            return value


class EffectPreflightError(Exception):
    """Fail-closed pre-dispatch connector or connection rejection."""


def _digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


__all__ = [
    "DispatchDisposition",
    "EffectDispatchRequest",
    "EffectDispatchResult",
    "EffectDispatcher",
    "EffectExecutionResult",
    "EffectOrchestrator",
    "EffectPreflightError",
    "EffectReconciler",
    "ReconciliationDisposition",
    "ReconciliationResult",
]
