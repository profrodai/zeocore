"""
Value objects returned by the step-2 protocols (SecretStore, ConnectionStore,
EffectAuthorizationVerifier), per implementation-order step 2: "SecretStore,
ConnectionStore, EffectAuthorizationVerifier protocols; NO permissive
default implementation."

Consumed by: protocols.py (this package), and the (not-yet-built) custody,
persistence and admission adapters (steps 3-6, out of this step's scope).
Must NOT contain: secret material, adapter imports, provider calls,
filesystem or database behavior -- these are frozen data shapes only.

WHY THIS MODULE EXISTS, DISTINCT FROM protocols.py: a `Protocol` has no
runtime behavior of its own to test -- it is a structural type. Bound 3
("EffectAuthorizationVerifier... absence, mismatch, expiry, or replay
refuses closed") and bound 5 ("runtime behavior tests remain mandatory")
can only be proven behaviourally if there is a concrete value the verifier
protocol's `verify()` method is typed to RETURN whose own construction
rules make an ambiguous or silent-allow outcome structurally unrepresentable
-- exactly the same move step 1 made for ConfirmationEvidenceRef (a typed
shape that makes an ordinary provider token unrepresentable, per
identity.py). AuthorizationVerdict below is that value: it cannot be
constructed as "authorized" without the checked identity fields present,
and it cannot be constructed as "refused" without a closed-taxonomy reason
-- there is no third, in-between shape a permissive implementation could
return instead.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zeo_core.contracts.connections.enums import AuthorizationRefusalReason
from zeo_core.contracts.connections.identity import (
    AuthorizationId,
    ConnectionId,
    ConnectorRevisionId,
    OperationId,
    OrganizationId,
    SecretRef,
)


class AuthorizationVerdict(BaseModel):
    """
    The exclusive, closed outcome of one EffectAuthorizationVerifier check.

    Exactly one of two shapes, enforced by the validator below -- there is
    no third state:

      * AUTHORIZED: `authorized=True`, `refusal_reason` is None, and every
        one of the five checked-identity fields
        (organization_id/connection_id/connector_revision/operation_id/
        request_digest) is present, matching AUTHORIZATION_VERIFIED's own
        binding definition (Principal decision msg_ebff3939) of what "the
        exact ZEO Go authorization matches" means. A verdict that claimed
        authorization without restating what it checked would be exactly
        the "trust me" shape disposition 2 forbids.
      * REFUSED: `authorized=False` and `refusal_reason` is a required,
        non-None AuthorizationRefusalReason. There is no default reason and
        no way to construct a refused verdict silently -- refusing without
        saying why is not a valid instance of this type.

    A verdict is never partially authorized and never carries a refusal
    reason alongside `authorized=True`. This model has no method that
    mutates it into the other shape after construction (frozen); a verifier
    implementation must decide and construct the correct shape once.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    authorized: bool
    organization_id: OrganizationId | None = None
    connection_id: ConnectionId | None = None
    connector_revision: ConnectorRevisionId | None = None
    operation_id: OperationId | None = None
    authorization_id: AuthorizationId | None = None
    request_digest: str | None = Field(default=None, min_length=1)
    checked_at: datetime
    refusal_reason: AuthorizationRefusalReason | None = None

    @model_validator(mode="after")
    def _authorized_and_refused_are_mutually_exclusive_and_complete(
        self,
    ) -> AuthorizationVerdict:
        if self.authorized:
            if self.refusal_reason is not None:
                raise ValueError(
                    "an AUTHORIZED verdict must not carry a refusal_reason"
                )
            missing = [
                name
                for name, value in (
                    ("organization_id", self.organization_id),
                    ("connection_id", self.connection_id),
                    ("connector_revision", self.connector_revision),
                    ("operation_id", self.operation_id),
                    ("authorization_id", self.authorization_id),
                    ("request_digest", self.request_digest),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    "an AUTHORIZED verdict must restate every checked "
                    f"identity field, missing: {missing}"
                )
        else:
            if self.refusal_reason is None:
                raise ValueError(
                    "a REFUSED verdict must carry a non-None refusal_reason "
                    "-- refusing without a closed-taxonomy reason is not a "
                    "valid instance of this type (refuse closed, never "
                    "silently)"
                )
        return self

    def __repr__(self) -> str:
        if self.authorized:
            return (
                "AuthorizationVerdict(authorized=True, "
                f"authorization_id={self.authorization_id!r})"
            )
        return (
            "AuthorizationVerdict(authorized=False, "
            f"refusal_reason={self.refusal_reason!s})"
        )

    def __str__(self) -> str:
        return self.__repr__()


class SecretHealth(BaseModel):
    """
    Health signal for one SecretRef, returned by SecretStore.health.

    Carries no secret material -- `ref` is the opaque SecretRef, never the
    resolved value. `reachable=False` requires `detail`; a caller must be
    told SOMETHING about why a secret is unreachable to distinguish
    "does not exist" from "custody adapter unreachable" from "rotated",
    without that explanation ever being allowed to carry the secret itself
    (a custody adapter must redact before populating this field -- outside
    this step's scope to enforce, since no adapter exists yet).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    reachable: bool
    checked_at: datetime
    detail: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _unreachable_requires_detail(self) -> SecretHealth:
        if not self.reachable and self.detail is None:
            raise ValueError("an unreachable SecretHealth must carry a non-None detail")
        return self


class SecretResolution(BaseModel):
    """
    A short-lived, broker-only resolution handle for one SecretRef, per
    step-2 bound 1: "short-lived broker-only resolution... no secret
    material appears in public results, repr, str, logs, ordinary dumps,
    receipts, or exceptions."

    This model is deliberately NOT the secret. `lease_id` is an opaque
    broker-minted handle a caller presents back to the (not-yet-built)
    custody adapter's dispatch-scoped API to actually use the material --
    exactly the same non-redeemable-outside-custody posture SecretRef
    itself already carries (identity.py). `expires_at` makes "short-lived"
    a checkable fact, not a promise in a docstring: a resolution with no
    expiry, or one where SecretStore.resolve is free to hand back a
    lease with no ceiling, is exactly a "permissive default implementation"
    of the kind this step forbids. There is no field here that could hold
    resolved material -- adding one is a domain-contract change under the
    packet's escalation boundary, not a change a later step lands quietly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ref: SecretRef
    lease_id: str = Field(..., min_length=1)
    resolved_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def _expiry_after_resolution(self) -> SecretResolution:
        if self.expires_at <= self.resolved_at:
            raise ValueError("expires_at must be strictly after resolved_at")
        return self
