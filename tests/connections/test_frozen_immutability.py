"""
Must-NOT: no public model in contracts/connections is mutable after
construction.

SOW-01's step 1 requirement: "Frozen means frozen -- immutable value
objects, not mutable dataclasses." Pydantic v2's `model_config =
ConfigDict(frozen=True)` raises `pydantic.ValidationError` on any attribute
assignment after construction; this test asserts that behavior directly
against every public model this package exports, by attempting to mutate
one field on a real instance and catching the raised error.

`TestProbeCanFail` proves the assertion technique is a real probe (not a
tautology that would pass against anything) by running the identical
mutation-attempt logic against a deliberately UNFROZEN synthetic model
built in-test and observing it fail because the mutation actually succeeds.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import zeo_core.contracts.connections as connections_pkg
from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections import (
    AuthorizationId,
    BusinessOperation,
    ConfirmationEvidenceRef,
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


def assert_immutable(instance: BaseModel, field_name: str) -> None:
    """
    Attempt to mutate `field_name` on `instance` and assert it is refused.

    Pure assertion helper: raises AssertionError (via pytest.fail) if the
    mutation is NOT refused, so it can be reused unchanged in both the real
    test and TestProbeCanFail's deliberately-broken counter-case.
    """
    try:
        setattr(instance, field_name, getattr(instance, field_name))
    except ValidationError:
        return  # refused, as expected of a frozen model
    else:
        pytest.fail(
            f"{type(instance).__name__}.{field_name} was mutated without "
            "raising -- model is not actually frozen"
        )


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


class TestFrozenToday:
    """Runs the real probe against a live instance of every public model."""

    def test_secret_ref_is_frozen(self) -> None:
        instance = SecretRef(handle="kc-1")
        assert_immutable(instance, "handle")

    def test_organization_id_is_frozen(self) -> None:
        assert_immutable(OrganizationId(value="org-1"), "value")

    def test_connector_revision_is_frozen(self, now: datetime) -> None:
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
        assert_immutable(op, "allowed_origin")

        revision = ConnectorRevision(
            connector_id=ConnectorId(value="google.drive"),
            revision_id=ConnectorRevisionId(value="google.drive@1"),
            provider="google",
            authentication_profile="oauth2",
            permitted_upstream_origins=("https://www.googleapis.com",),
            external_account_identity_probe="userinfo",
            health_probe="about.get",
            operations=(op,),
            request_size_limit_bytes=1_000_000,
            response_size_limit_bytes=1_000_000,
            timeout_seconds=30.0,
            credential_injection_point="header",
            redaction_policy="strip-auth-header",
            risk_class=RiskClass.LOW,
            provider_error_mapping_version="1",
        )
        assert_immutable(revision, "provider")

    def test_connection_is_frozen(self, now: datetime) -> None:
        connection = Connection(
            connection_id=ConnectionId(value="conn-1"),
            organization_id=OrganizationId(value="org-1"),
            connector_id=ConnectorId(value="google.drive"),
            connector_revision=ConnectorRevisionId(value="google.drive@1"),
            provider_application_profile="app-1",
            verified_external_identity="user@example.com",
            secret_handle=SecretRef(handle="kc-1"),
            status=ConnectionStatus.ACTIVE,
            created_at=now,
        )
        assert_immutable(connection, "status")
        assert_immutable(connection, "secret_handle")

    def test_effect_authorization_is_frozen(self, now: datetime) -> None:
        from datetime import timedelta

        authorization = EffectAuthorization(
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
        assert_immutable(authorization, "signature")

    def test_execution_is_frozen(self, now: datetime) -> None:
        execution = Execution(
            execution_id=ExecutionId(value="exec-1"),
            organization_id=OrganizationId(value="org-1"),
            connection_id=ConnectionId(value="conn-1"),
            connector_revision=ConnectorRevisionId(value="google.drive@1"),
            operation_id=OperationId(value="google.drive.list_files"),
            authorization_id=AuthorizationId(value="auth-1"),
            idempotency_key=IdempotencyKey(value="idem-1"),
            authorization_digest="sha256:auth-digest",
            request_digest="sha256:req-digest",
            state=ExecutionState.CREATED,
            created_at=now,
            updated_at=now,
        )
        assert_immutable(execution, "state")

    def test_normalized_error_is_frozen(self) -> None:
        error = NormalizedError(
            code=NormalizedErrorCode.RATE_LIMITED,
            message="rate limited",
        )
        assert_immutable(error, "code")

    def test_execution_receipt_is_frozen(self, now: datetime) -> None:
        receipt = ExecutionReceipt(
            execution_id=ExecutionId(value="exec-1"),
            organization_id=OrganizationId(value="org-1"),
            connection_id=ConnectionId(value="conn-1"),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now,
            confirmation_evidence_ref=ConfirmationEvidenceRef(
                value="zeo-evidence:v1:8f14e45f-ceea-4d4c-b90a-a4d1a4e1c5a1"
            ),
        )
        assert_immutable(receipt, "final_state")

    def test_confirmation_evidence_ref_is_frozen(self) -> None:
        ref = ConfirmationEvidenceRef(
            value="zeo-evidence:v1:8f14e45f-ceea-4d4c-b90a-a4d1a4e1c5a1"
        )
        assert_immutable(ref, "value")

    def test_every_exported_model_declares_frozen_config(self) -> None:
        # Belt-and-suspenders static check alongside the behavioral ones
        # above: every public BaseModel export must declare frozen=True in
        # its model_config, not merely happen to behave as frozen today.
        violations = []
        for name in connections_pkg.__all__:
            obj = getattr(connections_pkg, name)
            if isinstance(obj, type) and issubclass(obj, BaseModel):
                if not obj.model_config.get("frozen"):
                    violations.append(name)
        assert violations == [], f"models missing frozen=True: {violations}"


class TestProbeCanFail:
    """
    Proves assert_immutable is a real probe by running it against a
    deliberately UNFROZEN synthetic model and observing the mutation
    actually succeed, which pytest.raises below turns into an observed
    AssertionError from assert_immutable itself.
    """

    def test_probe_fails_against_mutable_model(self) -> None:
        class NotActuallyFrozen(BaseModel):
            model_config = ConfigDict(extra="forbid")  # frozen deliberately omitted
            value: str

        instance = NotActuallyFrozen(value="original")

        # assert_immutable calls pytest.fail() on an unrefused mutation,
        # which raises pytest's own _pytest.outcomes.Failed (a BaseException
        # subclass), not a plain AssertionError -- pytest.raises must match
        # the actual exception type or this probe-of-the-probe would itself
        # report a false pass/fail.
        with pytest.raises(pytest.fail.Exception, match="was mutated without raising"):
            assert_immutable(instance, "value")

        # Confirm directly that the mutation this stream's real models
        # refuse was, in this deliberately-broken case, allowed through --
        # this is the RED half of the RED-then-GREEN evidence.
        instance.value = "mutated"
        assert instance.value == "mutated"
