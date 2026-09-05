"""Fail-closed connector and request admission proofs."""

from __future__ import annotations

import pytest

from zeo_core.connections import (
    ConnectorAdmissionError,
    validate_connection_admission,
    validate_connector_revision,
    validate_operation_request,
)
from zeo_core.contracts.connections import (
    BusinessOperation,
    Connection,
    ConnectorId,
    ConnectorRevision,
    ConnectorRevisionId,
    OperationId,
    RiskClass,
)


@pytest.fixture
def admitted_revision(
    effectful_business_operation: BusinessOperation,
) -> ConnectorRevision:
    operation = effectful_business_operation.model_copy(
        update={
            "request_schema": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "additionalProperties": False,
            },
            "secret_bindings": ("oauth-access",),
            "redaction_paths": ("authorization",),
        }
    )
    return ConnectorRevision(
        connector_id=ConnectorId(value="google.gmail"),
        revision_id=ConnectorRevisionId(value="google.gmail@1"),
        provider="google",
        authentication_profile="oauth2",
        permitted_upstream_origins=("https://gmail.googleapis.com",),
        required_provider_scopes=("gmail.send",),
        external_account_identity_probe="userinfo",
        health_probe="profile.get",
        operations=(operation,),
        request_size_limit_bytes=4096,
        response_size_limit_bytes=4096,
        timeout_seconds=10,
        credential_injection_point="authorization-header",
        redaction_policy="drop-provider-payload",
        risk_class=RiskClass.HIGH,
        reconciliation_method="query_sent_folder_by_digest",
        provider_error_mapping_version="1",
    )


def test_valid_revision_and_connection_are_admitted(
    admitted_revision: ConnectorRevision, connection: Connection
) -> None:
    operation_id = admitted_revision.operations[0].operation_id
    admitted_connection = connection.model_copy(
        update={
            "connector_id": admitted_revision.connector_id,
            "connector_revision": admitted_revision.revision_id,
            "granted_provider_scopes": ("gmail.send", "openid"),
            "exposed_business_operations": (operation_id,),
        }
    )

    validate_connector_revision(admitted_revision)
    validate_connection_admission(
        connection=admitted_connection, revision=admitted_revision
    )
    validate_operation_request(
        revision=admitted_revision,
        operation_id=operation_id,
        request_body=b'{"message":"approved"}',
    )


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"allowed_origin": "https://outside.example"}, "outside permitted"),
        ({"path_template": "*"}, "unconstrained"),
        ({"path_template": "https://evil.example/send"}, "unconstrained"),
        ({"secret_bindings": ()}, "secret binding"),
        ({"redaction_paths": ()}, "redaction paths"),
        ({"reconciliation_strategy": None}, "reconciliation"),
        ({"method": "post"}, "uppercase HTTP"),
        (
            {"request_schema": {"type": "object", "properties": {}}},
            "closed object",
        ),
        (
            {
                "request_schema": {
                    "type": "object",
                    "properties": {"callback_url": {"type": "string"}},
                    "additionalProperties": False,
                }
            },
            "transport fields",
        ),
    ],
)
def test_revision_admission_rejects_broad_operation_surfaces(
    admitted_revision: ConnectorRevision,
    update: dict[str, object],
    message: str,
) -> None:
    operation = admitted_revision.operations[0].model_copy(update=update)
    revision = admitted_revision.model_copy(update={"operations": (operation,)})

    with pytest.raises(ConnectorAdmissionError, match=message):
        validate_connector_revision(revision)


def test_revision_admission_rejects_redirects(
    admitted_revision: ConnectorRevision,
) -> None:
    revision = admitted_revision.model_copy(update={"follow_redirects": True})
    with pytest.raises(ConnectorAdmissionError, match="forbids redirects"):
        validate_connector_revision(revision)


@pytest.mark.parametrize(
    "request_body",
    [
        b'{"callback_url":"https://evil.example"}',
        b'{"headers":{"authorization":"secret"}}',
        b'{"undeclared":"value"}',
        b'{"message":"first","message":"second"}',
        b"[]",
        b"not-json",
    ],
)
def test_runtime_request_rejects_transport_and_undeclared_fields(
    admitted_revision: ConnectorRevision, request_body: bytes
) -> None:
    with pytest.raises(ConnectorAdmissionError):
        validate_operation_request(
            revision=admitted_revision,
            operation_id=admitted_revision.operations[0].operation_id,
            request_body=request_body,
        )


def test_connection_cannot_expose_undeclared_operation_or_missing_scope(
    admitted_revision: ConnectorRevision, connection: Connection
) -> None:
    base = connection.model_copy(
        update={
            "connector_id": admitted_revision.connector_id,
            "connector_revision": admitted_revision.revision_id,
            "granted_provider_scopes": (),
            "exposed_business_operations": (
                OperationId(value="caller.selected.operation"),
            ),
        }
    )
    with pytest.raises(ConnectorAdmissionError, match="undeclared operation"):
        validate_connection_admission(connection=base, revision=admitted_revision)

    missing_scope = base.model_copy(
        update={
            "exposed_business_operations": (
                admitted_revision.operations[0].operation_id,
            )
        }
    )
    with pytest.raises(ConnectorAdmissionError, match="required provider scope"):
        validate_connection_admission(
            connection=missing_scope, revision=admitted_revision
        )
