"""
Frozen identity value objects for the connections domain.

Consumed by: connection, authorization, execution and receipt contracts in
this package; the (not-yet-built) connections domain and its adapters.
Must NOT contain: secret material, adapter imports, mutation.

Every id here is a frozen Pydantic model wrapping a non-empty string, not a
bare `str` alias -- this is deliberate. A bare `str` lets a `connection_id`
and an `organization_id` be swapped at a call site with no type error; a
distinct frozen wrapper makes that swap a mypy failure instead of a runtime
cross-tenant read. See ZC0-KERNEL-SEAM-01 disposition 8: organization
identity is trusted runtime context, never caller JSON, and giving it its
own type is part of making that hold mechanically rather than by convention.

SecretRef is the one type in this module that is not an identity in the
usual sense: it is the opaque, non-redeemable reference every public
connections contract uses in place of credential material (packet section
5.2, disposition 4). It carries a handle string and nothing else -- no
token, no password, no raw credential of any kind. Only a custody adapter
(step 3, out of this step's scope) may resolve a SecretRef to material, and
only inside a short-lived provider dispatch lease.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _NonEmptyIdentity(BaseModel):
    """
    Shared shape for a frozen identity wrapping one non-empty string value.

    Not exported. Concrete id types below inherit this so every id gets the
    same non-empty validation and the same frozen/extra-forbid posture
    without repeating the boilerplate five times.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str = Field(..., min_length=1)

    @field_validator("value")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("identity value must be non-empty")
        return v

    def __str__(self) -> str:
        return self.value


class OrganizationId(_NonEmptyIdentity):
    """
    Identity of the organization that owns a connection and its executions.

    Trusted runtime context only (disposition 8). Nothing in this package
    constructs an OrganizationId from caller-supplied request JSON; that
    wiring, if it exists at all, belongs to an adapter outside contracts.
    """


class ConnectorId(_NonEmptyIdentity):
    """Identity of a connector (a provider integration family, e.g. google.drive)."""


class ConnectorRevisionId(_NonEmptyIdentity):
    """
    Identity of one immutable revision of a connector.

    Distinct from ConnectorId: a connector accumulates revisions over time,
    but a given revision's declared operations, schemas and origins never
    change once minted (disposition 9). Executions pin a ConnectorRevisionId,
    never a bare ConnectorId, so a later revision update cannot change the
    meaning of a historical execution.
    """


class ConnectionId(_NonEmptyIdentity):
    """Identity of one connection (an organization's binding to a connector)."""


class OperationId(_NonEmptyIdentity):
    """Identity of one admitted business operation declared by a connector revision."""


class AuthorizationId(_NonEmptyIdentity):
    """Identity of one ZEO Go EffectAuthorization (packet section 10.2)."""


class ExecutionId(_NonEmptyIdentity):
    """Identity of one durable execution of an admitted business operation."""


class IdempotencyKey(_NonEmptyIdentity):
    """
    Caller-scoped idempotency identity for one attempted effect.

    Scoped by organization, connection, connector revision and operation at
    the persistence layer (disposition 13) -- this type is only the key
    value itself, not the composite uniqueness constraint, which is a
    storage-layer concern outside contracts.
    """


class SecretRef(BaseModel):
    """
    Opaque, non-redeemable reference to secret material held by a custody
    adapter.

    This is the ONLY way secret material may appear anywhere in a public
    connections contract. `handle` is an opaque string minted by a
    SecretStore implementation (step 2, out of this step's scope) -- it is
    not the secret, cannot be exchanged for the secret by anything reading
    this model, and this type deliberately has no other field. Adding a
    second field to this class is the kind of change that should return for
    a ruling under the packet's escalation boundary (domain-contract change),
    not land quietly.

    Must NOT contain: token, password, secret_value, an auth header, or any
    field a resolver could use to reconstruct the secret without going
    through the custody adapter.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    handle: str = Field(..., min_length=1)

    @field_validator("handle")
    @classmethod
    def _non_empty_handle(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("SecretRef handle must be non-empty")
        return v

    def __repr__(self) -> str:
        # A SecretRef's handle is opaque, not secret -- but redacting the
        # repr anyway means a future reader can never mistake this type for
        # one that is safe to relax, and grep for "REDACTED" finds every
        # place in the codebase making that same promise.
        return "SecretRef(handle=<redacted>)"
