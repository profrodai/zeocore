"""Durable, bounded orchestration for admitted read-only operations."""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from zeo_core.connections.admission import (
    ConnectorAdmissionError,
    validate_connection_admission,
    validate_operation_request,
)
from zeo_core.connections.authorization import ExactAuthorizationVerifier
from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections import (
    AuthorizationRefusalReason,
    Connection,
    ConnectionId,
    ConnectionStatus,
    ConnectorRevision,
    ConnectorRevisionId,
    EffectAuthorization,
    NormalizedError,
    NormalizedErrorCode,
    ObservationArtifact,
    ObservationId,
    ObservationReceipt,
    ObservationRecord,
    ObservationState,
    ObservationStore,
    OperationId,
    OrganizationId,
)

_FORBIDDEN_RESULT_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "client_secret",
        "credential",
        "credentials",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)


class ObservationDisposition(StrEnum):
    """Facts a read adapter may report without mutation-style uncertainty."""

    CONFIRMED = "CONFIRMED"
    FAILED_SAFE = "FAILED_SAFE"


class ObservationDispatchResult(BaseModel):
    """One sanitized inline result or one bounded artifact reference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    disposition: ObservationDisposition
    inline_result: JsonValue | None = None
    artifact: ObservationArtifact | None = None
    normalized_error: NormalizedError | None = None

    @model_validator(mode="after")
    def _shape_matches_disposition(self) -> ObservationDispatchResult:
        representations = int(self.inline_result is not None) + int(
            self.artifact is not None
        )
        if self.disposition is ObservationDisposition.CONFIRMED:
            if representations != 1 or self.normalized_error is not None:
                raise ValueError(
                    "confirmed observation requires exactly one result representation"
                )
        elif representations or self.normalized_error is None:
            raise ValueError("failed-safe observation requires only normalized_error")
        if self.normalized_error is not None and self.normalized_error.provider_detail:
            raise ValueError("provider detail is forbidden at observation boundary")
        return self


@dataclass(frozen=True)
class ObservationDispatchRequest:
    """Trusted context and admitted caller body passed to a read adapter."""

    organization_id: OrganizationId
    connection: Connection
    connector_revision: ConnectorRevision
    operation_id: OperationId
    observation_id: ObservationId
    request_digest: str
    request_body: bytes


class ObservationDispatcher(Protocol):
    """Provider-specific read implementation called once after durable claim."""

    def observe(
        self, request: ObservationDispatchRequest
    ) -> ObservationDispatchResult: ...


@dataclass(frozen=True)
class ObservationExecutionResult:
    """Public outcome carrying no credential or raw provider response."""

    state: ObservationState | None
    observation_id: ObservationId | None
    receipt: ObservationReceipt | None = None
    refusal_reason: AuthorizationRefusalReason | None = None


class ObservationOrchestrator:
    """Validate, claim, dispatch once, bound, sanitize, and durably receipt a read."""

    def __init__(
        self,
        *,
        store: ObservationStore,
        verifier: ExactAuthorizationVerifier,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._verifier = verifier
        self._clock = clock or (lambda: datetime.now(UTC))
        self._last_timestamp: datetime | None = None
        self._clock_lock = threading.Lock()

    def observe(
        self,
        *,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        connector_revision: ConnectorRevisionId,
        operation_id: OperationId,
        authorization: EffectAuthorization | None,
        observation_id: ObservationId,
        request_body: bytes,
        dispatcher: ObservationDispatcher,
    ) -> ObservationExecutionResult:
        """Perform at most one admitted read for one exact idempotency identity."""

        if authorization is None:
            return ObservationExecutionResult(
                state=None,
                observation_id=None,
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
            if verdict.refusal_reason is AuthorizationRefusalReason.REPLAYED:
                existing = self._store.get_observation_by_idempotency(
                    organization_id=organization_id,
                    connection_id=connection_id,
                    connector_revision=connector_revision,
                    operation_id=str(operation_id),
                    idempotency_key=authorization.idempotency_key,
                )
                if existing is not None and existing.request_digest == request_digest:
                    receipt = self._store.get_observation_receipt(
                        organization_id=organization_id,
                        observation_id=existing.observation_id,
                    )
                    return ObservationExecutionResult(
                        existing.state, existing.observation_id, receipt
                    )
            return ObservationExecutionResult(
                state=None,
                observation_id=None,
                refusal_reason=verdict.refusal_reason,
            )

        connection, revision = self._load_admitted_read(
            organization_id=organization_id,
            connection_id=connection_id,
            connector_revision=connector_revision,
            operation_id=operation_id,
            request_body=request_body,
        )
        created_at = self._now()
        observation = ObservationRecord(
            observation_id=observation_id,
            organization_id=organization_id,
            connection_id=connection_id,
            connector_revision=connector_revision,
            operation_id=operation_id,
            authorization_id=authorization.authorization_id,
            idempotency_key=authorization.idempotency_key,
            authorization_digest=_digest(authorization.model_dump_json().encode()),
            request_digest=request_digest,
            state=ObservationState.CLAIMED,
            created_at=created_at,
        )
        observation, claimed = self._store.claim_observation(
            organization_id=organization_id,
            nonce=authorization.nonce,
            nonce_recorded_at=created_at,
            observation=observation,
        )
        if not claimed:
            if observation.request_digest != request_digest:
                return ObservationExecutionResult(
                    state=None,
                    observation_id=None,
                    refusal_reason=AuthorizationRefusalReason.REQUEST_DIGEST_MISMATCH,
                )
            receipt = self._store.get_observation_receipt(
                organization_id=organization_id,
                observation_id=observation.observation_id,
            )
            return ObservationExecutionResult(
                observation.state, observation.observation_id, receipt
            )

        request = ObservationDispatchRequest(
            organization_id=organization_id,
            connection=connection,
            connector_revision=revision,
            operation_id=operation_id,
            observation_id=observation_id,
            request_digest=request_digest,
            request_body=request_body,
        )
        try:
            dispatch = dispatcher.observe(request)
            receipt = self._receipt_from_dispatch(
                observation=observation,
                dispatch=dispatch,
                response_limit=revision.response_size_limit_bytes,
            )
        except Exception:
            receipt = ObservationReceipt(
                observation_id=observation_id,
                organization_id=organization_id,
                connection_id=connection_id,
                final_state=ObservationState.FAILED_SAFE,
                request_digest=request_digest,
                normalized_error=NormalizedError(
                    code=NormalizedErrorCode.PROVIDER_UNAVAILABLE,
                    message="provider observation did not complete safely",
                ),
                recorded_at=self._now_after(created_at),
            )
        terminal = observation.model_copy(
            update={"state": receipt.final_state, "completed_at": receipt.recorded_at}
        )
        self._store.commit_observation(
            organization_id=organization_id,
            observation=terminal,
            receipt=receipt,
        )
        return ObservationExecutionResult(
            terminal.state, terminal.observation_id, receipt
        )

    def _load_admitted_read(
        self,
        *,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        connector_revision: ConnectorRevisionId,
        operation_id: OperationId,
        request_body: bytes,
    ) -> tuple[Connection, ConnectorRevision]:
        connection = self._store.get_connection(
            organization_id=organization_id, connection_id=connection_id
        )
        if connection is None or connection.status is not ConnectionStatus.ACTIVE:
            raise ObservationPreflightError("connection is not active")
        if connection.connector_revision != connector_revision:
            raise ObservationPreflightError("connection revision mismatch")
        revision = self._store.get_connector_revision(
            organization_id=organization_id, revision_id=connector_revision
        )
        if revision is None:
            raise ObservationPreflightError("connector revision is unavailable")
        if len(request_body) > revision.request_size_limit_bytes:
            raise ObservationPreflightError("request exceeds connector size limit")
        try:
            validate_connection_admission(connection=connection, revision=revision)
            validate_operation_request(
                revision=revision,
                operation_id=operation_id,
                request_body=request_body,
            )
        except ConnectorAdmissionError as error:
            raise ObservationPreflightError(
                "connector admission refused read"
            ) from error
        operation = next(
            (item for item in revision.operations if item.operation_id == operation_id),
            None,
        )
        if (
            operation is None
            or operation_id not in connection.exposed_business_operations
        ):
            raise ObservationPreflightError("read operation is not exposed")
        if operation.effect is not EffectKind.READ:
            raise ObservationPreflightError(
                "effectful operations require effect orchestration"
            )
        if operation.resource_argument is not None:
            payload = json.loads(request_body)
            resource = payload.get(operation.resource_argument)
            if not isinstance(resource, str) or resource not in set(
                connection.selected_business_resources
            ):
                raise ObservationPreflightError("business resource is not selected")
        return connection, revision

    def _receipt_from_dispatch(
        self,
        *,
        observation: ObservationRecord,
        dispatch: ObservationDispatchResult,
        response_limit: int,
    ) -> ObservationReceipt:
        recorded_at = self._now_after(observation.created_at)
        if dispatch.disposition is ObservationDisposition.FAILED_SAFE:
            return ObservationReceipt(
                observation_id=observation.observation_id,
                organization_id=observation.organization_id,
                connection_id=observation.connection_id,
                final_state=ObservationState.FAILED_SAFE,
                request_digest=observation.request_digest,
                normalized_error=dispatch.normalized_error,
                recorded_at=recorded_at,
            )
        if dispatch.inline_result is not None:
            if _has_forbidden_key(dispatch.inline_result):
                raise ValueError("observation result contains a secret-bearing field")
            encoded = _canonical_json(dispatch.inline_result)
            if len(encoded) > response_limit:
                raise ValueError("observation result exceeds connector size limit")
            digest = _digest(encoded)
        else:
            artifact = dispatch.artifact
            if artifact is None:  # model validator makes this unreachable
                raise RuntimeError("confirmed observation omitted its result")
            if artifact.size_bytes > response_limit:
                raise ValueError("observation artifact exceeds connector size limit")
            digest = artifact.content_sha256
        return ObservationReceipt(
            observation_id=observation.observation_id,
            organization_id=observation.organization_id,
            connection_id=observation.connection_id,
            final_state=ObservationState.CONFIRMED,
            request_digest=observation.request_digest,
            result_digest=digest,
            inline_result=dispatch.inline_result,
            artifact=dispatch.artifact,
            recorded_at=recorded_at,
        )

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


class ObservationPreflightError(Exception):
    """Fail-closed rejection before any read provider is called."""


def _digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _canonical_json(value: JsonValue) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _has_forbidden_key(value: JsonValue) -> bool:
    if isinstance(value, Mapping):
        if any(str(key).lower() in _FORBIDDEN_RESULT_KEYS for key in value):
            return True
        return any(_has_forbidden_key(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_has_forbidden_key(item) for item in value)
    return False


__all__ = [
    "ObservationDispatchRequest",
    "ObservationDispatchResult",
    "ObservationDispatcher",
    "ObservationDisposition",
    "ObservationExecutionResult",
    "ObservationOrchestrator",
    "ObservationPreflightError",
]
