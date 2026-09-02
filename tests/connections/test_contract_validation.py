"""
Contract-level validation tests: extra-field rejection, cross-field
invariants, and identity-type separation.

Covers the part of "caller-supplied organization, origin, path, auth
header, callback URL -> REJECTED as extra fields" (SOW-01 section 3) that
is testable at the frozen-contract layer today: every public model declares
`extra="forbid"`, so an adapter that tried to accept caller JSON directly
into one of these models would already reject any field the model does not
declare -- including a caller trying to smuggle in a second `organization_id`
via serialized JSON with an unexpected alias, or any field this step's
authors did not anticipate. The actual "the runtime never reads
organization_id from request JSON" wiring is an orchestration-layer
guarantee (step 6, out of this step's scope); this file proves the
mechanical half available now.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel, ValidationError

import zeo_core.contracts.connections as connections_pkg
from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections import (
    AuthorizationId,
    BusinessOperation,
    Connection,
    ConnectionId,
    ConnectionStatus,
    ConnectorId,
    ConnectorRevision,
    ConnectorRevisionId,
    EffectAuthorization,
    Execution,
    ExecutionId,
    ExecutionReceipt,
    ExecutionState,
    IdempotencyKey,
    IdempotencyMode,
    NormalizedError,
    NormalizedErrorCode,
    OperationId,
    OrganizationId,
    RiskClass,
    SecretRef,
)


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


class TestExtraFieldsRejectedEverywhere:
    def test_every_exported_model_forbids_extra_fields(self) -> None:
        violations = []
        for name in connections_pkg.__all__:
            obj = getattr(connections_pkg, name)
            if isinstance(obj, type) and issubclass(obj, BaseModel):
                if obj.model_config.get("extra") != "forbid":
                    violations.append(name)
        assert violations == [], f"models not declaring extra='forbid': {violations}"

    def test_connection_rejects_caller_injected_extra_field(
        self, now: datetime
    ) -> None:
        base_kwargs = {
            "connection_id": ConnectionId(value="conn-1"),
            "organization_id": OrganizationId(value="org-1"),
            "connector_id": ConnectorId(value="google.drive"),
            "connector_revision": ConnectorRevisionId(value="google.drive@1"),
            "provider_application_profile": "app-1",
            "verified_external_identity": "user@example.com",
            "secret_handle": SecretRef(handle="kc-1"),
            "status": ConnectionStatus.ACTIVE,
            "created_at": now,
        }
        Connection(**base_kwargs)  # sanity: valid without the extra field

        with pytest.raises(ValidationError):
            Connection(  # type: ignore[call-arg]  # deliberate invalid kwarg, testing extra="forbid" contract
                **base_kwargs, callback_url="https://attacker.example/hook"
            )

    def test_effect_authorization_rejects_caller_injected_auth_header(
        self, now: datetime
    ) -> None:
        base_kwargs = {
            "authorization_id": AuthorizationId(value="auth-1"),
            "organization_id": OrganizationId(value="org-1"),
            "seat_id": "seat-1",
            "runtime_binding_id": "runtime-1",
            "packet_id": "packet-1",
            "attempt_id": "attempt-1",
            "connection_id": ConnectionId(value="conn-1"),
            "connector_revision": ConnectorRevisionId(value="google.drive@1"),
            "operation_id": OperationId(value="google.drive.list_files"),
            "argument_digest": "sha256:abc",
            "idempotency_key": IdempotencyKey(value="idem-1"),
            "issued_at": now,
            "expires_at": now + timedelta(minutes=5),
            "nonce": "nonce-1",
            "audience": "zeocore",
            "issuer": "zeo-go",
            "signature": "sig-1",
        }
        EffectAuthorization(**base_kwargs)  # sanity

        with pytest.raises(ValidationError):
            EffectAuthorization(  # type: ignore[call-arg]  # deliberate invalid kwarg, testing extra="forbid" contract
                **base_kwargs, auth_header="Bearer forged-token"
            )


class TestIdentityTypesAreSeparate:
    """
    Distinct wrapper types for distinct ids means a mypy-catchable error, not
    a runtime cross-tenant read, if an author swaps two ids at a call site.
    """

    def test_organization_id_and_connection_id_are_different_types(self) -> None:
        assert OrganizationId is not ConnectionId
        org = OrganizationId(value="x")
        assert not isinstance(org, ConnectionId)

    def test_connector_id_and_connector_revision_id_are_different_types(self) -> None:
        assert ConnectorId is not ConnectorRevisionId

    def test_identity_values_must_be_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            OrganizationId(value="")
        with pytest.raises(ValidationError):
            OrganizationId(value="   ")


class TestConnectionCrossFieldInvariants:
    def test_revoked_status_requires_revoked_at(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="REVOKED connection"):
            Connection(
                connection_id=ConnectionId(value="conn-1"),
                organization_id=OrganizationId(value="org-1"),
                connector_id=ConnectorId(value="google.drive"),
                connector_revision=ConnectorRevisionId(value="google.drive@1"),
                provider_application_profile="app-1",
                verified_external_identity="user@example.com",
                secret_handle=SecretRef(handle="kc-1"),
                status=ConnectionStatus.REVOKED,
                created_at=now,
            )

    def test_revoked_at_forbidden_unless_status_revoked(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="revoked_at may only be set"):
            Connection(
                connection_id=ConnectionId(value="conn-1"),
                organization_id=OrganizationId(value="org-1"),
                connector_id=ConnectorId(value="google.drive"),
                connector_revision=ConnectorRevisionId(value="google.drive@1"),
                provider_application_profile="app-1",
                verified_external_identity="user@example.com",
                secret_handle=SecretRef(handle="kc-1"),
                status=ConnectionStatus.ACTIVE,
                created_at=now,
                revoked_at=now,
            )

    def test_duplicate_exposed_operations_rejected(self, now: datetime) -> None:
        op_id = OperationId(value="google.drive.list_files")
        with pytest.raises(ValidationError, match="duplicate operation_id"):
            Connection(
                connection_id=ConnectionId(value="conn-1"),
                organization_id=OrganizationId(value="org-1"),
                connector_id=ConnectorId(value="google.drive"),
                connector_revision=ConnectorRevisionId(value="google.drive@1"),
                provider_application_profile="app-1",
                verified_external_identity="user@example.com",
                exposed_business_operations=(op_id, op_id),
                secret_handle=SecretRef(handle="kc-1"),
                status=ConnectionStatus.ACTIVE,
                created_at=now,
            )


class TestExecutionCrossFieldInvariants:
    def test_terminal_state_requires_completed_at(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="must carry completed_at"):
            Execution(
                execution_id=ExecutionId(value="exec-1"),
                organization_id=OrganizationId(value="org-1"),
                connection_id=ConnectionId(value="conn-1"),
                connector_revision=ConnectorRevisionId(value="google.drive@1"),
                operation_id=OperationId(value="google.drive.list_files"),
                authorization_id=AuthorizationId(value="auth-1"),
                idempotency_key=IdempotencyKey(value="idem-1"),
                authorization_digest="sha256:a",
                request_digest="sha256:r",
                state=ExecutionState.SUCCEEDED,
                created_at=now,
                updated_at=now,
            )

    def test_non_terminal_state_forbids_completed_at(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="must not carry completed_at"):
            Execution(
                execution_id=ExecutionId(value="exec-1"),
                organization_id=OrganizationId(value="org-1"),
                connection_id=ConnectionId(value="conn-1"),
                connector_revision=ConnectorRevisionId(value="google.drive@1"),
                operation_id=OperationId(value="google.drive.list_files"),
                authorization_id=AuthorizationId(value="auth-1"),
                idempotency_key=IdempotencyKey(value="idem-1"),
                authorization_digest="sha256:a",
                request_digest="sha256:r",
                state=ExecutionState.CREATED,
                created_at=now,
                updated_at=now,
                completed_at=now,
            )

    def test_updated_at_before_created_at_rejected(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="updated_at must not be before"):
            Execution(
                execution_id=ExecutionId(value="exec-1"),
                organization_id=OrganizationId(value="org-1"),
                connection_id=ConnectionId(value="conn-1"),
                connector_revision=ConnectorRevisionId(value="google.drive@1"),
                operation_id=OperationId(value="google.drive.list_files"),
                authorization_id=AuthorizationId(value="auth-1"),
                idempotency_key=IdempotencyKey(value="idem-1"),
                authorization_digest="sha256:a",
                request_digest="sha256:r",
                state=ExecutionState.CREATED,
                created_at=now,
                updated_at=now - timedelta(seconds=1),
            )


class TestEffectAuthorizationInvariants:
    def test_expiry_before_issue_rejected(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="expires_at must be strictly after"):
            EffectAuthorization(
                authorization_id=AuthorizationId(value="auth-1"),
                organization_id=OrganizationId(value="org-1"),
                seat_id="seat-1",
                runtime_binding_id="runtime-1",
                packet_id="packet-1",
                attempt_id="attempt-1",
                connection_id=ConnectionId(value="conn-1"),
                connector_revision=ConnectorRevisionId(value="google.drive@1"),
                operation_id=OperationId(value="google.drive.list_files"),
                argument_digest="sha256:abc",
                idempotency_key=IdempotencyKey(value="idem-1"),
                issued_at=now,
                expires_at=now - timedelta(minutes=5),
                nonce="nonce-1",
                audience="zeocore",
                issuer="zeo-go",
                signature="sig-1",
            )

    def test_is_expired_true_after_expiry(self, now: datetime) -> None:
        auth = EffectAuthorization(
            authorization_id=AuthorizationId(value="auth-1"),
            organization_id=OrganizationId(value="org-1"),
            seat_id="seat-1",
            runtime_binding_id="runtime-1",
            packet_id="packet-1",
            attempt_id="attempt-1",
            connection_id=ConnectionId(value="conn-1"),
            connector_revision=ConnectorRevisionId(value="google.drive@1"),
            operation_id=OperationId(value="google.drive.list_files"),
            argument_digest="sha256:abc",
            idempotency_key=IdempotencyKey(value="idem-1"),
            issued_at=now,
            expires_at=now + timedelta(minutes=5),
            nonce="nonce-1",
            audience="zeocore",
            issuer="zeo-go",
            signature="sig-1",
        )
        assert not auth.is_expired(at=now)
        assert auth.is_expired(at=now + timedelta(minutes=10))
        assert auth.is_expired(at=now + timedelta(minutes=5))  # boundary: >=


class TestConnectorRevisionInvariants:
    def test_effectful_operation_without_reconciliation_rejected(self) -> None:
        with pytest.raises(ValidationError, match="reconciliation_strategy"):
            ConnectorRevision(
                connector_id=ConnectorId(value="gmail"),
                revision_id=ConnectorRevisionId(value="gmail@1"),
                provider="google",
                authentication_profile="oauth2",
                permitted_upstream_origins=("https://gmail.googleapis.com",),
                external_account_identity_probe="userinfo",
                health_probe="profile.get",
                operations=(
                    BusinessOperation(
                        operation_id=OperationId(value="gmail.send_approved_quote"),
                        effect=EffectKind.EXTERNAL_COMMUNICATION,
                        request_schema={"type": "object"},
                        response_schema={"type": "object"},
                        allowed_origin="https://gmail.googleapis.com",
                        method="POST",
                        path_template="/gmail/v1/users/me/messages/send",
                        idempotency_mode=IdempotencyMode.KERNEL_MANAGED,
                        # reconciliation_strategy omitted deliberately
                    ),
                ),
                request_size_limit_bytes=1_000_000,
                response_size_limit_bytes=1_000_000,
                timeout_seconds=30.0,
                credential_injection_point="header",
                redaction_policy="strip-auth-header",
                risk_class=RiskClass.LOW,
                provider_error_mapping_version="1",
            )

    def test_read_only_operation_needs_no_reconciliation(self) -> None:
        ConnectorRevision(
            connector_id=ConnectorId(value="google.drive"),
            revision_id=ConnectorRevisionId(value="google.drive@1"),
            provider="google",
            authentication_profile="oauth2",
            permitted_upstream_origins=("https://www.googleapis.com",),
            external_account_identity_probe="userinfo",
            health_probe="about.get",
            operations=(
                BusinessOperation(
                    operation_id=OperationId(
                        value="google.drive.list_files_in_connected_folder"
                    ),
                    effect=EffectKind.READ,
                    request_schema={"type": "object"},
                    response_schema={"type": "object"},
                    allowed_origin="https://www.googleapis.com",
                    method="GET",
                    path_template="/drive/v3/files",
                    idempotency_mode=IdempotencyMode.PROVIDER_NATIVE,
                ),
            ),
            request_size_limit_bytes=1_000_000,
            response_size_limit_bytes=1_000_000,
            timeout_seconds=30.0,
            credential_injection_point="header",
            redaction_policy="strip-auth-header",
            risk_class=RiskClass.LOW,
            provider_error_mapping_version="1",
        )  # must not raise

    def test_duplicate_operation_ids_rejected(self) -> None:
        op = BusinessOperation(
            operation_id=OperationId(value="google.drive.list_files"),
            effect=EffectKind.READ,
            request_schema={"type": "object"},
            response_schema={"type": "object"},
            allowed_origin="https://www.googleapis.com",
            method="GET",
            path_template="/drive/v3/files",
            idempotency_mode=IdempotencyMode.PROVIDER_NATIVE,
        )
        with pytest.raises(ValidationError, match="duplicate operation_id"):
            ConnectorRevision(
                connector_id=ConnectorId(value="google.drive"),
                revision_id=ConnectorRevisionId(value="google.drive@1"),
                provider="google",
                authentication_profile="oauth2",
                permitted_upstream_origins=("https://www.googleapis.com",),
                external_account_identity_probe="userinfo",
                health_probe="about.get",
                operations=(op, op),
                request_size_limit_bytes=1_000_000,
                response_size_limit_bytes=1_000_000,
                timeout_seconds=30.0,
                credential_injection_point="header",
                redaction_policy="strip-auth-header",
                risk_class=RiskClass.LOW,
                provider_error_mapping_version="1",
            )


class TestExecutionReceiptInvariants:
    def test_failed_receipt_requires_normalized_error(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="FAILED receipt must carry"):
            ExecutionReceipt(
                execution_id=ExecutionId(value="exec-1"),
                organization_id=OrganizationId(value="org-1"),
                connection_id=ConnectionId(value="conn-1"),
                final_state=ExecutionState.FAILED,
                recorded_at=now,
            )

    def test_non_failed_receipt_forbids_normalized_error(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="only be set when final_state"):
            ExecutionReceipt(
                execution_id=ExecutionId(value="exec-1"),
                organization_id=OrganizationId(value="org-1"),
                connection_id=ConnectionId(value="conn-1"),
                final_state=ExecutionState.SUCCEEDED,
                normalized_error=NormalizedError(
                    code=NormalizedErrorCode.RATE_LIMITED, message="x"
                ),
                recorded_at=now,
            )

    def test_reconciled_receipt_requires_evidence_and_resolved_at(
        self, now: datetime
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="RECONCILED receipt must carry reconciliation_evidence",
        ):
            ExecutionReceipt(
                execution_id=ExecutionId(value="exec-1"),
                organization_id=OrganizationId(value="org-1"),
                connection_id=ConnectionId(value="conn-1"),
                final_state=ExecutionState.RECONCILED,
                recorded_at=now,
            )

    def test_ambiguous_receipt_is_valid_without_resolution(self, now: datetime) -> None:
        ExecutionReceipt(
            execution_id=ExecutionId(value="exec-1"),
            organization_id=OrganizationId(value="org-1"),
            connection_id=ConnectionId(value="conn-1"),
            final_state=ExecutionState.AMBIGUOUS,
            recorded_at=now,
        )  # must not raise: an honest, unresolved AMBIGUOUS receipt is valid

    def test_created_state_rejected_as_final_state(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="terminal or AMBIGUOUS"):
            ExecutionReceipt(
                execution_id=ExecutionId(value="exec-1"),
                organization_id=OrganizationId(value="org-1"),
                connection_id=ConnectionId(value="conn-1"),
                final_state=ExecutionState.CREATED,
                recorded_at=now,
            )
