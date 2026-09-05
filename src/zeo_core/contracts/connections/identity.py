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

SecretRef redaction (Principal decision msg_54b0e295, 2026-09-02): a
SecretRef handle is not credential material and is not independently
redeemable outside custody, but it is a sensitive, capability-adjacent
locator, so it is safe-by-default across every ACCIDENTAL disclosure
channel -- repr, str, f-string formatting, percent-s logging, model_dump
and model_dump_json (including when nested inside Connection.secret_handle)
all show a redacted placeholder, never the raw handle. This is NOT a
persistence round-trip: the field shape is retained (a reader always sees
a `handle` key), only its value is redacted by default. `.handle` direct
attribute access is the one DELIBERATE channel and continues to return the
exact raw value -- future trusted ConnectionStore/SecretStore adapter code
reads it there, never by generic model dumping. No general-purpose reveal
method (`reveal()`, `unwrap()`, `get_secret()` or similar) is added; `.handle`
is the only sanctioned deliberate-access path and it already existed.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

#: Canonical shape for a ConfirmationEvidenceRef, per Principal decision
#: msg_54b0e295: `zeo-evidence:v1:<lowercase UUIDv4>`. The UUID group is
#: matched against RFC 4122 version-4 layout (version nibble literally "4",
#: variant nibble one of 8/9/a/b) so a syntactically UUID-shaped but
#: non-v4 value, or an uppercase-hex value, is rejected by the pattern
#: itself rather than by a separate parse step.
#: `\Z` (not `$`) anchors the END strictly: Python's `re` module lets a bare
#: `$` match immediately before a trailing "\n" as well as true end-of-
#: string, which would silently accept a canonical value plus a trailing
#: newline -- exactly the kind of copy-paste-with-newline input a caller
#: could plausibly send. `\A`/`\Z` have no such exception.
_CONFIRMATION_EVIDENCE_REF_PATTERN = re.compile(
    r"\Azeo-evidence:v1:"
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)
_OBSERVATION_ARTIFACT_REF_PATTERN = re.compile(
    r"\Azeo-observation-artifact:v1:"
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)


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


class ObservationId(_NonEmptyIdentity):
    """Identity of one durable execution of an admitted read operation."""


class ObservationArtifactRef(_NonEmptyIdentity):
    """Opaque locator for bounded observation bytes held by an artifact store."""

    @field_validator("value")
    @classmethod
    def _matches_canonical_shape(cls, value: str) -> str:
        if not _OBSERVATION_ARTIFACT_REF_PATTERN.match(value):
            raise ValueError(
                "ObservationArtifactRef must be a kernel-shaped UUIDv4 locator"
            )
        return value


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

    Safe-by-default across every ACCIDENTAL disclosure channel (Principal
    decision msg_54b0e295): repr, str, f-string formatting, percent-s
    logging, model_dump and model_dump_json (including nested inside
    Connection.secret_handle) all show `<redacted>`, never the raw handle.
    `.handle` direct attribute access is the one sanctioned DELIBERATE
    channel and always returns the exact raw value -- it is not a
    persistence round-trip, and no general-purpose reveal method is added.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    handle: str = Field(..., min_length=1)

    @field_validator("handle")
    @classmethod
    def _non_empty_handle(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("SecretRef handle must be non-empty")
        return v

    @field_serializer("handle")
    def _redact_handle_on_dump(self, _value: str) -> str:
        # Fires for both model_dump() and model_dump_json(), and for a
        # containing model's dump too (Connection.secret_handle), since
        # pydantic serializes nested models field-by-field through their
        # own serializers. `.handle` attribute access does NOT go through
        # this method -- it reads the stored value directly -- so this is
        # the accidental-channel redaction only, never the deliberate one.
        return "<redacted>"

    def __repr__(self) -> str:
        # A SecretRef's handle is opaque, not secret -- but redacting the
        # repr anyway means a future reader can never mistake this type for
        # one that is safe to relax, and grep for "REDACTED" finds every
        # place in the codebase making that same promise.
        return "SecretRef(handle=<redacted>)"

    def __str__(self) -> str:
        # str(secret_ref) and f"{secret_ref}" both route through __str__;
        # without this override pydantic's BaseModel.__str__ default prints
        # every field's raw value (`handle='<the actual handle>'`), which is
        # exactly the accidental-disclosure channel the ruling closes.
        return "SecretRef(handle=<redacted>)"


class ConfirmationEvidenceRef(BaseModel):
    """
    Typed, kernel-minted locator into the (not-yet-built) evidence store,
    per Principal decision msg_54b0e295.

    Replaces the prior bare `str | None` on
    ExecutionReceipt.confirmation_evidence_ref. The evidence store (a later
    step, out of this step's scope) mints this identifier; provider output
    never supplies it, and this type's ONLY job is to make an ordinary
    provider token or arbitrary payload structurally unrepresentable here --
    it is shape validation, not content classification. It does not and
    cannot prove that no caller encoded a secret as a syntactically valid
    UUID; provenance enforcement (accepting only references minted by and
    found in the authorized evidence store for the same organization and
    execution) is explicitly a LATER step's job, per the ruling's boundary.

    Canonical shape: `zeo-evidence:v1:<lowercase UUIDv4>` -- exactly the
    literal prefix, then a lowercase RFC 4122 version-4 UUID. No other
    prefix, no uppercase hex, no non-v4 UUID version/variant nibble, no
    surrounding whitespace. `value` is the only field: this is a pure
    locator, never a carrier for the sanitized confirmation content itself
    (that content lives behind this reference in the evidence store and is
    never copied here).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str = Field(..., min_length=1)

    @field_validator("value")
    @classmethod
    def _matches_canonical_shape(cls, v: str) -> str:
        if not _CONFIRMATION_EVIDENCE_REF_PATTERN.match(v):
            raise ValueError(
                "ConfirmationEvidenceRef value must match the canonical "
                "shape 'zeo-evidence:v1:<lowercase UUIDv4>', got "
                f"{v!r}"
            )
        return v

    def __str__(self) -> str:
        return self.value
