"""
EffectAuthorization, per packet section 10.2 and disposition 2.

Consumed by: execution contracts in this package; the (not-yet-built)
EffectAuthorizationVerifier protocol and orchestration layer (steps 2 and 6,
out of this step's scope).
Must NOT contain: organizational policy logic. Per section 10.2, "Zeocore
verifies mechanical execution conditions. It does not reconstruct
organizational policy" -- this model is data, not a decision engine. It also
must not carry an auth header, callback URL, or any field a caller could use
to assert its own tenant or origin; every field here is issued BY ZEO Go,
never supplied by the runtime asking to execute.

The exact wire format belongs to the ZEO Go authority contract (packet
section 10.2's own wording); this model is what Zeocore "should expect"
information equivalent to, per that section, not a claim that this is ZEO
Go's own serialization.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zeo_core.contracts.connections.identity import (
    AuthorizationId,
    ConnectionId,
    ConnectorRevisionId,
    IdempotencyKey,
    OperationId,
    OrganizationId,
)


class EffectAuthorization(BaseModel):
    """
    A signed, exact authorization for one attempted effect, per section 10.2.

    All identity and scoping fields (organization_id, connection_id,
    connector_revision, operation_id) are issued as part of the
    authorization itself -- they are read FROM this model by the execution
    layer, never supplied independently by a caller and merely checked for
    consistency against it. That is what "exact" means in disposition 2:
    the authorization is the source of truth for what may execute, not a
    token that unlocks caller-chosen parameters.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    authorization_id: AuthorizationId
    organization_id: OrganizationId
    seat_id: str = Field(..., min_length=1)
    runtime_binding_id: str = Field(..., min_length=1)
    packet_id: str = Field(..., min_length=1)
    attempt_id: str = Field(..., min_length=1)
    connection_id: ConnectionId
    connector_revision: ConnectorRevisionId
    operation_id: OperationId
    argument_digest: str = Field(..., min_length=1)
    idempotency_key: IdempotencyKey
    approval_refs: tuple[str, ...] = Field(default_factory=tuple)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    issuer: str = Field(..., min_length=1)
    signature: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _expiry_after_issue(self) -> EffectAuthorization:
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be strictly after issued_at")
        return self

    def is_expired(self, *, at: datetime) -> bool:
        """
        Return True iff this authorization is expired at the given instant.

        Takes the instant as an explicit argument rather than calling
        `datetime.now()` internally: a pure contract must not read the wall
        clock itself, both because that would make every check
        non-deterministic in tests and because it would be a step toward
        this frozen module doing verification work that belongs to the
        EffectAuthorizationVerifier protocol (step 2), not to the data model.
        """
        return at >= self.expires_at
