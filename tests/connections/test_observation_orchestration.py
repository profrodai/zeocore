"""Behavioral proofs for durable, bounded read-only orchestration."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from zeo_core.connections import (
    ExactAuthorizationVerifier,
    ObservationDispatchRequest,
    ObservationDispatchResult,
    ObservationDisposition,
    ObservationOrchestrator,
    ObservationPreflightError,
    SQLiteConnectionStore,
)
from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections import (
    AuthorizationId,
    AuthorizationRefusalReason,
    BusinessOperation,
    Connection,
    ConnectionId,
    ConnectionStatus,
    ConnectorId,
    ConnectorRevision,
    ConnectorRevisionId,
    EffectAuthorization,
    IdempotencyKey,
    IdempotencyMode,
    NormalizedError,
    NormalizedErrorCode,
    ObservationArtifact,
    ObservationArtifactRef,
    ObservationId,
    ObservationState,
    ObservationStore,
    OperationId,
    OrganizationId,
    RiskClass,
    SecretRef,
)

NOW = datetime(2026, 9, 5, 14, 0, tzinfo=UTC)


class AcceptingSignatureVerifier:
    def verify_signature(self, authorization: EffectAuthorization) -> bool:
        del authorization
        return True


class RecordingDispatcher:
    def __init__(
        self,
        result: ObservationDispatchResult | Exception,
        store: SQLiteConnectionStore,
    ) -> None:
        self.result = result
        self.store = store
        self.calls: list[ObservationDispatchRequest] = []

    def observe(self, request: ObservationDispatchRequest) -> ObservationDispatchResult:
        self.calls.append(request)
        persisted = self.store.get_observation(
            organization_id=request.organization_id,
            observation_id=request.observation_id,
        )
        assert persisted is not None
        assert persisted.state is ObservationState.CLAIMED
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _surface(
    tmp_path: Path,
) -> tuple[SQLiteConnectionStore, OrganizationId, EffectAuthorization, bytes]:
    store = SQLiteConnectionStore(tmp_path / "observations.sqlite3")
    organization_id = OrganizationId(value="org-member")
    connection_id = ConnectionId(value="connection-drive")
    revision_id = ConnectorRevisionId(value="google.drive.selected-file@1")
    operation_id = OperationId(value="google.drive.file.download")
    connector_id = ConnectorId(value="google.drive")
    revision = ConnectorRevision(
        connector_id=connector_id,
        revision_id=revision_id,
        provider="google",
        authentication_profile="oauth2-selected-file",
        permitted_upstream_origins=("https://www.googleapis.com",),
        required_provider_scopes=("https://www.googleapis.com/auth/drive.file",),
        external_account_identity_probe="oauth2.userinfo.get",
        health_probe="drive.files.get",
        operations=(
            BusinessOperation(
                operation_id=operation_id,
                effect=EffectKind.READ,
                request_schema={
                    "type": "object",
                    "properties": {
                        "file_id": {"type": "string"},
                        "format": {"type": "string"},
                    },
                    "required": ["file_id"],
                    "additionalProperties": False,
                },
                response_schema={"type": "object"},
                allowed_origin="https://www.googleapis.com",
                method="GET",
                path_template="/drive/v3/files/{file_id}",
                secret_bindings=("google-oauth",),
                redaction_paths=("authorization",),
                idempotency_mode=IdempotencyMode.KERNEL_MANAGED,
                resource_argument="file_id",
            ),
        ),
        request_size_limit_bytes=1024,
        response_size_limit_bytes=128,
        timeout_seconds=10.0,
        credential_injection_point="authorization-header",
        redaction_policy="drop-provider-payload",
        risk_class=RiskClass.LOW,
        provider_error_mapping_version="google-v1",
    )
    connection = Connection(
        connection_id=connection_id,
        organization_id=organization_id,
        connector_id=connector_id,
        connector_revision=revision_id,
        provider_application_profile="zeoconnect-alpha",
        verified_external_identity="member@example.com",
        selected_business_resources=("file-selected",),
        granted_provider_scopes=("https://www.googleapis.com/auth/drive.file",),
        exposed_business_operations=(operation_id,),
        secret_handle=SecretRef(handle="zc0-kc:org-member:opaque"),
        status=ConnectionStatus.ACTIVE,
        created_at=NOW,
    )
    request_body = b'{"file_id":"file-selected"}'
    authorization = _authorization(
        organization_id=organization_id,
        connection_id=connection_id,
        revision_id=revision_id,
        operation_id=operation_id,
        request_body=request_body,
    )
    store.save_connector_revision(organization_id=organization_id, revision=revision)
    store.save_connection(organization_id=organization_id, connection=connection)
    return store, organization_id, authorization, request_body


def _authorization(
    *,
    organization_id: OrganizationId,
    connection_id: ConnectionId,
    revision_id: ConnectorRevisionId,
    operation_id: OperationId,
    request_body: bytes,
    nonce: str = "nonce-observe",
    authorization_id: str = "auth-observe",
) -> EffectAuthorization:
    return EffectAuthorization(
        authorization_id=AuthorizationId(value=authorization_id),
        organization_id=organization_id,
        seat_id="member-device",
        runtime_binding_id="device-1",
        packet_id="observation-grant",
        attempt_id="attempt-1",
        connection_id=connection_id,
        connector_revision=revision_id,
        operation_id=operation_id,
        argument_digest=_digest(request_body),
        idempotency_key=IdempotencyKey(value="idem-observe"),
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=5),
        nonce=nonce,
        audience="zeocore-observe",
        issuer="zeoconnect-member",
        signature="opaque-signature",
    )


def _orchestrator(store: SQLiteConnectionStore) -> ObservationOrchestrator:
    return ObservationOrchestrator(
        store=store,
        verifier=ExactAuthorizationVerifier(
            signature_verifier=AcceptingSignatureVerifier(),
            expected_audience="zeocore-observe",
            trusted_issuers=frozenset({"zeoconnect-member"}),
        ),
        clock=lambda: NOW,
    )


def test_observation_is_claimed_before_read_and_receipted(tmp_path: Path) -> None:
    store, organization_id, authorization, request_body = _surface(tmp_path)
    dispatcher = RecordingDispatcher(
        ObservationDispatchResult(
            disposition=ObservationDisposition.CONFIRMED,
            inline_result={"name": "selected.csv", "size": 42},
        ),
        store,
    )

    result = _orchestrator(store).observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-1"),
        request_body=request_body,
        dispatcher=dispatcher,
    )

    assert result.state is ObservationState.CONFIRMED
    assert result.receipt is not None
    assert result.receipt.inline_result == {"name": "selected.csv", "size": 42}
    assert result.receipt.result_digest == _digest(b'{"name":"selected.csv","size":42}')
    assert (
        store.get_observation_receipt(
            organization_id=organization_id,
            observation_id=ObservationId(value="observation-1"),
        )
        == result.receipt
    )
    assert len(dispatcher.calls) == 1
    assert isinstance(store, ObservationStore)


def test_absent_or_expired_authorization_refuses_without_claim(tmp_path: Path) -> None:
    store, organization_id, authorization, request_body = _surface(tmp_path)
    dispatcher = RecordingDispatcher(
        ObservationDispatchResult(
            disposition=ObservationDisposition.CONFIRMED,
            inline_result={"content": "never read"},
        ),
        store,
    )
    orchestrator = _orchestrator(store)

    absent = orchestrator.observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=None,
        observation_id=ObservationId(value="observation-absent"),
        request_body=request_body,
        dispatcher=dispatcher,
    )
    expired = orchestrator.observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization.model_copy(
            update={"expires_at": NOW - timedelta(seconds=1)}
        ),
        observation_id=ObservationId(value="observation-expired"),
        request_body=request_body,
        dispatcher=dispatcher,
    )

    assert absent.refusal_reason is AuthorizationRefusalReason.ABSENT
    assert expired.refusal_reason is AuthorizationRefusalReason.EXPIRED
    assert not dispatcher.calls


def test_identical_replay_returns_prior_receipt_without_second_read(
    tmp_path: Path,
) -> None:
    store, organization_id, authorization, request_body = _surface(tmp_path)
    dispatcher = RecordingDispatcher(
        ObservationDispatchResult(
            disposition=ObservationDisposition.CONFIRMED,
            inline_result={"text": "bounded"},
        ),
        store,
    )
    orchestrator = _orchestrator(store)
    first = orchestrator.observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-first"),
        request_body=request_body,
        dispatcher=dispatcher,
    )
    replay = orchestrator.observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-replay"),
        request_body=request_body,
        dispatcher=dispatcher,
    )

    assert replay == first
    assert len(dispatcher.calls) == 1


def test_conflicting_idempotency_reuse_refuses_without_read(tmp_path: Path) -> None:
    store, organization_id, authorization, request_body = _surface(tmp_path)
    dispatcher = RecordingDispatcher(
        ObservationDispatchResult(
            disposition=ObservationDisposition.CONFIRMED,
            inline_result={"text": "bounded"},
        ),
        store,
    )
    orchestrator = _orchestrator(store)
    orchestrator.observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-first"),
        request_body=request_body,
        dispatcher=dispatcher,
    )
    changed_body = b'{"file_id":"file-selected","format":"text"}'
    changed = _authorization(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        revision_id=authorization.connector_revision,
        operation_id=authorization.operation_id,
        request_body=changed_body,
        nonce="nonce-changed",
        authorization_id="auth-changed",
    )

    result = orchestrator.observe(
        organization_id=organization_id,
        connection_id=changed.connection_id,
        connector_revision=changed.connector_revision,
        operation_id=changed.operation_id,
        authorization=changed,
        observation_id=ObservationId(value="observation-changed"),
        request_body=changed_body,
        dispatcher=dispatcher,
    )

    assert result.refusal_reason is AuthorizationRefusalReason.REQUEST_DIGEST_MISMATCH
    assert len(dispatcher.calls) == 1


@pytest.mark.parametrize(
    "result",
    [
        ObservationDispatchResult(
            disposition=ObservationDisposition.CONFIRMED,
            inline_result={"token": "CANARY-OBSERVATION-SECRET"},
        ),
        ObservationDispatchResult(
            disposition=ObservationDisposition.CONFIRMED,
            inline_result={"content": "x" * 200},
        ),
    ],
)
def test_unbounded_or_secret_shaped_result_fails_safe_without_persisting_payload(
    tmp_path: Path, result: ObservationDispatchResult
) -> None:
    store, organization_id, authorization, request_body = _surface(tmp_path)

    outcome = _orchestrator(store).observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-rejected-result"),
        request_body=request_body,
        dispatcher=RecordingDispatcher(result, store),
    )

    assert outcome.state is ObservationState.FAILED_SAFE
    assert outcome.receipt is not None
    assert outcome.receipt.inline_result is None
    assert "CANARY-OBSERVATION-SECRET" not in (
        tmp_path / "observations.sqlite3"
    ).read_bytes().decode(errors="ignore")


def test_provider_failure_is_failed_safe_never_ambiguous(tmp_path: Path) -> None:
    store, organization_id, authorization, request_body = _surface(tmp_path)

    result = _orchestrator(store).observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-timeout"),
        request_body=request_body,
        dispatcher=RecordingDispatcher(TimeoutError("provider body"), store),
    )

    assert result.state is ObservationState.FAILED_SAFE
    assert result.receipt is not None
    assert result.receipt.normalized_error is not None
    assert result.receipt.normalized_error.code.value == "PROVIDER_UNAVAILABLE"


def test_adapter_can_return_a_sanitized_failed_safe_result(tmp_path: Path) -> None:
    store, organization_id, authorization, request_body = _surface(tmp_path)
    normalized_error = NormalizedError(
        code=NormalizedErrorCode.BUSINESS_RESOURCE_UNAVAILABLE,
        message="selected file is unavailable",
    )
    dispatcher = RecordingDispatcher(
        ObservationDispatchResult(
            disposition=ObservationDisposition.FAILED_SAFE,
            normalized_error=normalized_error,
        ),
        store,
    )

    result = _orchestrator(store).observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-missing-file"),
        request_body=request_body,
        dispatcher=dispatcher,
    )

    assert result.state is ObservationState.FAILED_SAFE
    assert result.receipt is not None
    assert result.receipt.normalized_error == normalized_error


def test_artifact_locator_is_structural_and_artifact_size_is_bounded(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError):
        ObservationArtifactRef(value="ya29.provider-token")
    store, organization_id, authorization, request_body = _surface(tmp_path)
    dispatcher = RecordingDispatcher(
        ObservationDispatchResult(
            disposition=ObservationDisposition.CONFIRMED,
            artifact=ObservationArtifact(
                artifact_ref=ObservationArtifactRef(
                    value=(
                        "zeo-observation-artifact:v1:"
                        "12345678-1234-4234-9234-123456789abc"
                    )
                ),
                content_sha256="sha256:" + "a" * 64,
                size_bytes=129,
                media_type="text/csv",
            ),
        ),
        store,
    )

    result = _orchestrator(store).observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-large-artifact"),
        request_body=request_body,
        dispatcher=dispatcher,
    )

    assert result.state is ObservationState.FAILED_SAFE
    assert result.receipt is not None
    assert result.receipt.artifact is None


def test_bounded_artifact_is_confirmed_and_digest_is_not_recomputed(
    tmp_path: Path,
) -> None:
    store, organization_id, authorization, request_body = _surface(tmp_path)
    artifact = ObservationArtifact(
        artifact_ref=ObservationArtifactRef(
            value=("zeo-observation-artifact:v1:12345678-1234-4234-9234-123456789abc")
        ),
        content_sha256="sha256:" + "b" * 64,
        size_bytes=128,
        media_type="text/csv",
    )

    result = _orchestrator(store).observe(
        organization_id=organization_id,
        connection_id=authorization.connection_id,
        connector_revision=authorization.connector_revision,
        operation_id=authorization.operation_id,
        authorization=authorization,
        observation_id=ObservationId(value="observation-artifact"),
        request_body=request_body,
        dispatcher=RecordingDispatcher(
            ObservationDispatchResult(
                disposition=ObservationDisposition.CONFIRMED,
                artifact=artifact,
            ),
            store,
        ),
    )

    assert result.state is ObservationState.CONFIRMED
    assert result.receipt is not None
    assert result.receipt.artifact == artifact
    assert result.receipt.result_digest == artifact.content_sha256


def test_unselected_resource_refuses_before_provider_call(tmp_path: Path) -> None:
    store, organization_id, authorization, _request_body = _surface(tmp_path)
    request_body = b'{"file_id":"not-selected"}'
    authorization = authorization.model_copy(
        update={"argument_digest": _digest(request_body)}
    )
    dispatcher = RecordingDispatcher(
        ObservationDispatchResult(
            disposition=ObservationDisposition.CONFIRMED,
            inline_result={"content": "should not run"},
        ),
        store,
    )

    with pytest.raises(ObservationPreflightError, match="not selected"):
        _orchestrator(store).observe(
            organization_id=organization_id,
            connection_id=authorization.connection_id,
            connector_revision=authorization.connector_revision,
            operation_id=authorization.operation_id,
            authorization=authorization,
            observation_id=ObservationId(value="observation-denied-resource"),
            request_body=request_body,
            dispatcher=dispatcher,
        )
    assert not dispatcher.calls
