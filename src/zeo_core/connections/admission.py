"""Fail-closed admission for immutable connector revisions and connections."""

from __future__ import annotations

import ipaddress
import json
from urllib.parse import urlsplit

from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections import (
    BusinessOperation,
    Connection,
    ConnectorRevision,
    OperationId,
)

_ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
_CALLER_CONTROLLED_TRANSPORT_FIELDS = frozenset(
    {
        "auth_header",
        "authorization",
        "callback",
        "callback_url",
        "cookie",
        "cookies",
        "headers",
        "origin",
        "path",
        "redirect",
        "redirect_url",
        "url",
    }
)


class ConnectorAdmissionError(ValueError):
    """A connector surface is too broad or internally inconsistent."""


def validate_connector_revision(revision: ConnectorRevision) -> None:
    """Reject a revision that could become arbitrary authenticated HTTP."""

    permitted = set(revision.permitted_upstream_origins)
    if len(permitted) != len(revision.permitted_upstream_origins):
        raise ConnectorAdmissionError("permitted upstream origins must be unique")
    for origin in permitted:
        _validate_origin(origin)
    if revision.follow_redirects:
        raise ConnectorAdmissionError("connector admission forbids redirects")
    for operation in revision.operations:
        _validate_operation(operation, permitted)


def _validate_operation(operation: BusinessOperation, permitted: set[str]) -> None:
    if operation.allowed_origin not in permitted:
        raise ConnectorAdmissionError(
            "operation origin is outside permitted upstream origins"
        )
    if operation.method not in _ALLOWED_METHODS:
        raise ConnectorAdmissionError(
            "operation method must be explicit uppercase HTTP"
        )
    _validate_path_template(operation.path_template)
    _validate_request_schema(operation.request_schema)
    _validate_resource_argument(operation)
    if operation.effect is EffectKind.READ:
        return
    if not operation.secret_bindings:
        raise ConnectorAdmissionError(
            "effectful operation must declare its secret binding"
        )
    bindings_are_invalid = len(set(operation.secret_bindings)) != len(
        operation.secret_bindings
    ) or any(not binding.strip() for binding in operation.secret_bindings)
    if bindings_are_invalid:
        raise ConnectorAdmissionError(
            "operation secret bindings must be non-empty and unique"
        )
    if not operation.redaction_paths:
        raise ConnectorAdmissionError(
            "effectful operation must declare redaction paths"
        )
    if not operation.reconciliation_strategy:
        raise ConnectorAdmissionError("effectful operation must declare reconciliation")


def _validate_resource_argument(operation: BusinessOperation) -> None:
    if operation.resource_argument is None:
        return
    properties = operation.request_schema["properties"]
    if not isinstance(properties, dict):  # defended by _validate_request_schema
        raise ConnectorAdmissionError("resource argument has no properties map")
    resource_schema = properties.get(operation.resource_argument)
    if not isinstance(resource_schema, dict) or resource_schema.get("type") != "string":
        raise ConnectorAdmissionError(
            "resource argument must name a declared string request property"
        )


def validate_connection_admission(
    *, connection: Connection, revision: ConnectorRevision
) -> None:
    """Prove a connection exposes only operations from its pinned revision."""

    validate_connector_revision(revision)
    if connection.connector_id != revision.connector_id:
        raise ConnectorAdmissionError("connection connector does not match revision")
    if connection.connector_revision != revision.revision_id:
        raise ConnectorAdmissionError("connection does not pin this revision")
    declared = {operation.operation_id for operation in revision.operations}
    exposed = set(connection.exposed_business_operations)
    if not exposed.issubset(declared):
        raise ConnectorAdmissionError("connection exposes an undeclared operation")
    if not set(revision.required_provider_scopes).issubset(
        connection.granted_provider_scopes
    ):
        raise ConnectorAdmissionError("connection is missing a required provider scope")


def validate_operation_request(
    *, revision: ConnectorRevision, operation_id: OperationId, request_body: bytes
) -> None:
    """Reject undeclared or transport-controlling top-level request fields."""

    operation = next(
        (item for item in revision.operations if item.operation_id == operation_id),
        None,
    )
    if operation is None:
        raise ConnectorAdmissionError("operation is absent from connector revision")
    try:
        payload = json.loads(request_body, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConnectorAdmissionError("operation request must be valid JSON") from error
    if not isinstance(payload, dict):
        raise ConnectorAdmissionError("operation request must be a JSON object")
    keys = set(payload)
    if keys & _CALLER_CONTROLLED_TRANSPORT_FIELDS:
        raise ConnectorAdmissionError(
            "operation request contains caller-controlled transport fields"
        )
    properties = operation.request_schema.get("properties")
    if not isinstance(properties, dict):
        raise ConnectorAdmissionError("admitted request schema has no properties map")
    if not keys.issubset(properties):
        raise ConnectorAdmissionError("operation request contains undeclared fields")


def _validate_origin(origin: str) -> None:
    parsed = urlsplit(origin)
    try:
        port = parsed.port
    except ValueError as error:
        raise ConnectorAdmissionError("upstream origin has an invalid port") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or port not in {None, 443}
    ):
        raise ConnectorAdmissionError("upstream origin must be an HTTPS origin only")
    hostname = parsed.hostname
    if hostname == "localhost" or hostname.endswith(".local"):
        raise ConnectorAdmissionError("upstream origin must not be local")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not address.is_global:
        raise ConnectorAdmissionError("upstream origin address must be global")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ConnectorAdmissionError("operation request contains duplicate fields")
        result[key] = value
    return result


def _validate_path_template(path: str) -> None:
    if (
        not path.startswith("/")
        or path.startswith("//")
        or "://" in path
        or "*" in path
        or ".." in path
        or "?" in path
        or "#" in path
    ):
        raise ConnectorAdmissionError("operation path template is unconstrained")


def _validate_request_schema(schema: dict[str, object]) -> None:
    if (
        schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
    ):
        raise ConnectorAdmissionError(
            "request schema must be a closed object with additionalProperties=false"
        )
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ConnectorAdmissionError("request schema must declare a properties map")
    if set(properties) & _CALLER_CONTROLLED_TRANSPORT_FIELDS:
        raise ConnectorAdmissionError(
            "request schema must not admit caller-controlled transport fields"
        )


__all__ = [
    "ConnectorAdmissionError",
    "validate_connection_admission",
    "validate_connector_revision",
    "validate_operation_request",
]
