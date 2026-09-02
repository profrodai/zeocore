"""
Connection object, per packet section 5.4.

Consumed by: execution and receipt contracts in this package (which pin a
ConnectionId and read `secret_handle` as an opaque reference); the
(not-yet-built) persistence and orchestration layers (steps 4 and 6, out of
this step's scope).
Must NOT contain: secret material -- `secret_handle` is a SecretRef, never
a token, password or credential of any kind (packet section 5.2,
disposition 4). This model exists specifically to be the connection object
the packet describes, and holding a raw credential here would be exactly
the class of leak ZC0 exists to close, not a minor style issue.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zeo_core.contracts.connections.enums import ConnectionHealth, ConnectionStatus
from zeo_core.contracts.connections.identity import (
    ConnectionId,
    ConnectorId,
    ConnectorRevisionId,
    OperationId,
    OrganizationId,
    SecretRef,
)


class Connection(BaseModel):
    """
    An organization's binding to one connector, per packet section 5.4.

    `secret_handle` is a SecretRef -- an opaque, non-redeemable reference.
    The packet notes the API may disclose it "only as an opaque
    non-redeemable identifier, or omit it entirely from normal responses";
    this model always carries it as a SecretRef, so an adapter that wants to
    omit it from an HTTP response does so by dropping the field at
    serialization time, never by weakening this type to something that
    could hold real material.

    `organization_id` is trusted runtime context (disposition 8): nothing in
    this package constructs a Connection from caller-supplied request JSON.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    connection_id: ConnectionId
    organization_id: OrganizationId
    connector_id: ConnectorId
    connector_revision: ConnectorRevisionId
    provider_application_profile: str = Field(..., min_length=1)
    verified_external_identity: str = Field(..., min_length=1)
    selected_business_resources: tuple[str, ...] = Field(default_factory=tuple)
    granted_provider_scopes: tuple[str, ...] = Field(default_factory=tuple)
    exposed_business_operations: tuple[OperationId, ...] = Field(default_factory=tuple)
    secret_handle: SecretRef
    status: ConnectionStatus
    health: ConnectionHealth = ConnectionHealth.UNKNOWN
    created_at: datetime
    last_verified_at: datetime | None = None
    revoked_at: datetime | None = None

    @model_validator(mode="after")
    def _revoked_status_has_revoked_at(self) -> Connection:
        if self.status == ConnectionStatus.REVOKED and self.revoked_at is None:
            raise ValueError(
                "a REVOKED connection must carry revoked_at "
                "(disposition 19: revocation must be honestly recorded, "
                "not merely flagged)"
            )
        if self.status != ConnectionStatus.REVOKED and self.revoked_at is not None:
            raise ValueError("revoked_at may only be set when status is REVOKED")
        return self

    @model_validator(mode="after")
    def _unique_exposed_operations(self) -> Connection:
        seen: set[str] = set()
        for op_id in self.exposed_business_operations:
            key = str(op_id)
            if key in seen:
                raise ValueError(
                    f"duplicate operation_id in exposed_business_operations: {key!r}"
                )
            seen.add(key)
        return self
