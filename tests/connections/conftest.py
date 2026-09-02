"""
Shared fixtures for connections contract tests.

Builds one minimal, valid instance of each connections contract so
individual test modules can mutate a copy rather than re-deriving valid
construction arguments from scratch in every test.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

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
    ExecutionState,
    IdempotencyKey,
    IdempotencyMode,
    OperationId,
    OrganizationId,
    RiskClass,
    SecretRef,
)


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def business_operation() -> BusinessOperation:
    return BusinessOperation(
        operation_id=OperationId(value="google.drive.list_files_in_connected_folder"),
        effect=EffectKind.READ,
        request_schema={"type": "object"},
        response_schema={"type": "object"},
        allowed_origin="https://www.googleapis.com",
        method="GET",
        path_template="/drive/v3/files",
        idempotency_mode=IdempotencyMode.PROVIDER_NATIVE,
    )


@pytest.fixture
def effectful_business_operation() -> BusinessOperation:
    return BusinessOperation(
        operation_id=OperationId(value="gmail.send_approved_quote"),
        effect=EffectKind.EXTERNAL_COMMUNICATION,
        request_schema={"type": "object"},
        response_schema={"type": "object"},
        allowed_origin="https://gmail.googleapis.com",
        method="POST",
        path_template="/gmail/v1/users/me/messages/send",
        idempotency_mode=IdempotencyMode.KERNEL_MANAGED,
        reconciliation_strategy="query_sent_folder_by_digest",
    )


@pytest.fixture
def connector_revision(business_operation: BusinessOperation) -> ConnectorRevision:
    return ConnectorRevision(
        connector_id=ConnectorId(value="google.drive"),
        revision_id=ConnectorRevisionId(value="google.drive@1"),
        provider="google",
        authentication_profile="oauth2",
        permitted_upstream_origins=("https://www.googleapis.com",),
        external_account_identity_probe="userinfo",
        health_probe="about.get",
        operations=(business_operation,),
        request_size_limit_bytes=1_000_000,
        response_size_limit_bytes=1_000_000,
        timeout_seconds=30.0,
        credential_injection_point="header",
        redaction_policy="strip-auth-header",
        risk_class=RiskClass.LOW,
        provider_error_mapping_version="1",
    )


@pytest.fixture
def secret_ref() -> SecretRef:
    return SecretRef(handle="kc-handle-1")


@pytest.fixture
def connection(now: datetime, secret_ref: SecretRef) -> Connection:
    return Connection(
        connection_id=ConnectionId(value="conn-1"),
        organization_id=OrganizationId(value="org-1"),
        connector_id=ConnectorId(value="google.drive"),
        connector_revision=ConnectorRevisionId(value="google.drive@1"),
        provider_application_profile="app-1",
        verified_external_identity="user@example.com",
        secret_handle=secret_ref,
        status=ConnectionStatus.ACTIVE,
        created_at=now,
    )


@pytest.fixture
def effect_authorization(now: datetime) -> EffectAuthorization:
    return EffectAuthorization(
        authorization_id=AuthorizationId(value="auth-1"),
        organization_id=OrganizationId(value="org-1"),
        seat_id="seat-1",
        runtime_binding_id="runtime-1",
        packet_id="packet-1",
        attempt_id="attempt-1",
        connection_id=ConnectionId(value="conn-1"),
        connector_revision=ConnectorRevisionId(value="google.drive@1"),
        operation_id=OperationId(value="google.drive.list_files_in_connected_folder"),
        argument_digest="sha256:abc",
        idempotency_key=IdempotencyKey(value="idem-1"),
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce="nonce-1",
        audience="zeocore",
        issuer="zeo-go",
        signature="sig-1",
    )


@pytest.fixture
def created_execution(now: datetime) -> Execution:
    return Execution(
        execution_id=ExecutionId(value="exec-1"),
        organization_id=OrganizationId(value="org-1"),
        connection_id=ConnectionId(value="conn-1"),
        connector_revision=ConnectorRevisionId(value="google.drive@1"),
        operation_id=OperationId(value="google.drive.list_files_in_connected_folder"),
        authorization_id=AuthorizationId(value="auth-1"),
        idempotency_key=IdempotencyKey(value="idem-1"),
        authorization_digest="sha256:auth-digest",
        request_digest="sha256:req-digest",
        state=ExecutionState.CREATED,
        created_at=now,
        updated_at=now,
    )
