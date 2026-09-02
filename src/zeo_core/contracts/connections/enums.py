"""
Controlled vocabularies for the connections domain.

Consumed by: connector, connection, execution, error and receipt contracts
in this package.
Must NOT contain: transition logic (see transitions.py), adapter code.

ExecutionState and the ALLOWED_TRANSITIONS table are grounded verbatim in
ZC0-KERNEL-SEAM-01 disposition 12 (the audited, numbered disposition in the
Principal brief's grounding addendum), which supersedes the earlier
descriptive sketch in the same brief's section 5.5. Disposition 12's chain
uses SUCCEEDED/FAILED where section 5.5 sketched CONFIRMED/REFUSED/
FAILED_SAFE; disposition 12 is the more specific, numbered, Sparring-reviewed
disposition and section 21.5's acceptance checks name DISPATCH_STARTED and
AMBIGUOUS, both present in disposition 12's chain, so this module follows
disposition 12. Recorded here rather than silently picked so a reader who
knows section 5.5's wording is not left wondering which one shipped.
"""

from __future__ import annotations

from enum import StrEnum


class ExecutionState(StrEnum):
    """
    Durable state of one execution, per ZC0-KERNEL-SEAM-01 disposition 12.

    Minimum path:
        CREATED -> AUTHORIZATION_VERIFIED -> PREPARED -> DISPATCH_STARTED
        -> SUCCEEDED | FAILED | AMBIGUOUS

    AMBIGUOUS means the provider may have applied the effect but the system
    lacks trustworthy confirmation. Reconciliation may resolve AMBIGUOUS to
    a terminal state later, but never erases it from history (disposition
    12) -- the transition table in transitions.py enforces this by refusing
    any transition that treats AMBIGUOUS as if it had never happened.
    """

    CREATED = "CREATED"
    AUTHORIZATION_VERIFIED = "AUTHORIZATION_VERIFIED"
    PREPARED = "PREPARED"
    DISPATCH_STARTED = "DISPATCH_STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"
    RECONCILED = "RECONCILED"


class NormalizedErrorCode(StrEnum):
    """
    Closed taxonomy for provider-specific failures, per packet section 5.6.

    Provider detail remains available for diagnosis (see NormalizedError's
    `provider_detail` field) but must never become the only product
    explanation, and must never carry raw credential or cross-tenant
    material -- that constraint is enforced at the NormalizedError model,
    not here.
    """

    CONNECTION_REVOKED = "CONNECTION_REVOKED"
    CONNECTION_REPAIR_REQUIRED = "CONNECTION_REPAIR_REQUIRED"
    PROVIDER_SCOPE_MISSING = "PROVIDER_SCOPE_MISSING"
    EXTERNAL_IDENTITY_CHANGED = "EXTERNAL_IDENTITY_CHANGED"
    BUSINESS_RESOURCE_UNAVAILABLE = "BUSINESS_RESOURCE_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    REQUEST_REFUSED = "REQUEST_REFUSED"
    FAILED_SAFE = "FAILED_SAFE"
    RESULT_AMBIGUOUS = "RESULT_AMBIGUOUS"
    CONNECTOR_REVISION_UNAVAILABLE = "CONNECTOR_REVISION_UNAVAILABLE"


class ConnectionStatus(StrEnum):
    """
    Lifecycle status of a connection, per packet section 5.4.

    Deliberately small and closed. A connection's fine-grained health
    signal (reachable, degraded, unknown) is ConnectionHealth, not this
    enum -- status is about lifecycle, health is about reachability, and
    packet section 5.4 lists both as separate fields on the connection
    object.
    """

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REPAIR_REQUIRED = "REPAIR_REQUIRED"
    REVOKED = "REVOKED"


class ConnectionHealth(StrEnum):
    """Reachability signal for a connection, distinct from lifecycle status."""

    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNREACHABLE = "UNREACHABLE"


class RiskClass(StrEnum):
    """
    Declared risk class of a connector revision's business operations, per
    packet section 5.1's "risk class" manifest field.
    """

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class IdempotencyMode(StrEnum):
    """
    Declared idempotency mode of one admitted business operation, per
    disposition 10.
    """

    PROVIDER_NATIVE = "PROVIDER_NATIVE"
    KERNEL_MANAGED = "KERNEL_MANAGED"
    NOT_IDEMPOTENT = "NOT_IDEMPOTENT"
