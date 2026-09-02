"""
SecretStore, ConnectionStore and EffectAuthorizationVerifier protocols,
implementation-order step 2 (ZC0-KERNEL-SEAM-01, released by Principal
decision msg_1a0afe96): "add the SecretStore, ConnectionStore, and
EffectAuthorizationVerifier protocols, with no permissive default
implementation. This is pure contract work."

Consumed by: the (not-yet-built) custody adapter (step 3: macOS Keychain),
persistence adapter (step 4: SQLite), and admission/orchestration layers
(steps 5-6) -- each of those implements one or more of these protocols;
none of that implementation exists yet and none of it is authorized by
this step.

Must NOT contain, per the step-two lease's contract bounds and the packet's
own step-1 posture carried forward: a production fake, an environment
bypass, a default-allow branch, an adapter import, a provider call, a
filesystem write, or database behavior. Every method below is `...` --
structural typing only. A `Protocol` class has no method BODY to make
permissive; "no permissive default implementation" is satisfied by there
being no implementation at all, which is what distinguishes a Protocol
from an ABC with concrete fallback methods (an ABC with a `return True`
default IS a permissive default implementation; nothing here is an ABC).

WHY runtime_checkable: each protocol is decorated `@runtime_checkable` so
`isinstance(obj, SecretStore)` works structurally, matching the existing
house style at `zeo_core.integrations.core.protocols` (AuthProviderProtocol
et al.). `runtime_checkable` checks method PRESENCE only (not signatures,
not behavior) -- this is a deliberate, well-known Python typing limitation,
not a gap introduced here; a conforming shape can still violate a bound
behaviourally (e.g. by writing to disk), which is exactly why every bound
below is provable only against a concrete implementation, and no concrete
implementation exists until step 3+.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from zeo_core.contracts.connections.authorization import EffectAuthorization
from zeo_core.contracts.connections.connection import Connection
from zeo_core.contracts.connections.connector import ConnectorRevision
from zeo_core.contracts.connections.execution import Execution
from zeo_core.contracts.connections.identity import (
    ConfirmationEvidenceRef,
    ConnectionId,
    ConnectorRevisionId,
    ExecutionId,
    OrganizationId,
    SecretRef,
)
from zeo_core.contracts.connections.receipt import ExecutionReceipt
from zeo_core.contracts.connections.verdicts import (
    AuthorizationVerdict,
    SecretHealth,
    SecretResolution,
)


@runtime_checkable
class SecretStore(Protocol):
    """
    Custody boundary for secret material, per step-two contract bound 1:
    "SecretStore exposes put, short-lived broker-only resolution, rotate,
    delete, and health through SecretRef; no secret material appears in
    public results, repr, str, logs, ordinary dumps, receipts, or
    exceptions."

    Every method's PUBLIC signature carries only SecretRef, SecretResolution
    or SecretHealth -- never a bare `str` that could hold raw material, and
    never an `Any`/`object` escape hatch a caller could smuggle a token
    through. `put` returns the SecretRef the caller must use afterward; it
    does not return or echo back the material it was given, so a caller
    inspecting only this protocol's return values can never observe what
    it just stored. Concrete custody (Keychain, step 3) implements this
    later; nothing here writes to a keychain, a file, or a database --
    this is a structural type only.
    """

    def put(self, *, organization_id: OrganizationId, material: str) -> SecretRef:
        """
        Store `material` under custody scoped to `organization_id` and
        return the opaque SecretRef minted for it. The returned SecretRef
        never carries `material` back to the caller in any accidental
        channel (identity.py's SecretRef already guarantees this for its
        own type); this method's OWN exceptions must not embed `material`
        either -- an implementation that raises `ValueError(material)` on
        a validation failure would violate this bound just as much as a
        leaky return value would.
        """
        ...

    def resolve(
        self, *, ref: SecretRef, organization_id: OrganizationId
    ) -> SecretResolution:
        """
        Return a short-lived, broker-only SecretResolution lease for `ref`,
        scoped to `organization_id`. This is deliberately NOT a method that
        returns the material itself -- "broker-only resolution" means a
        caller holding a SecretResolution still cannot read the secret from
        it; only a future, still-unauthorized custody-adapter-internal path
        (out of this step's scope) may exchange a lease for material,
        strictly inside a short-lived provider dispatch window. Every
        implementation must reject a `ref` from a different organization
        than `organization_id` rather than silently resolving it --
        cross-organization resolution is exactly the "callers cannot
        supply or override trusted organization context" failure bound 2
        forbids on ConnectionStore, and it applies with equal force here.
        """
        ...

    def rotate(
        self, *, ref: SecretRef, organization_id: OrganizationId, material: str
    ) -> SecretRef:
        """
        Replace the material behind `ref` with `material` and return the
        SecretRef to use going forward (which may be `ref` itself, reused
        in place, or a newly minted one -- that choice belongs to the
        custody adapter, not this protocol). As with `put`, no accidental
        channel -- return value, exception, log -- may carry `material` or
        the material previously behind `ref`.
        """
        ...

    def delete(self, *, ref: SecretRef, organization_id: OrganizationId) -> None:
        """
        Irrecoverably remove the material behind `ref` from custody.
        Deletion must not delete or alter any historical execution or
        receipt evidence that merely references `ref` -- those records
        remain valid append-only history even after their secret is gone
        (this is the packet's own acceptance check: "Keychain deletion ->
        resolution fails closed WITHOUT deleting historical execution
        evidence"). This protocol has no method that reads back "was this
        deleted" other than `health`, deliberately: a store that could be
        asked "is `ref` still present" via a direct query is a second,
        redundant existence-disclosure channel the packet's checks do not
        require and this step does not add.
        """
        ...

    def health(
        self, *, ref: SecretRef, organization_id: OrganizationId
    ) -> SecretHealth:
        """
        Report whether `ref` is currently reachable, without resolving it.
        `SecretHealth.reachable=False` must be returned, never raised as an
        exception that could carry a stack trace referencing internal
        custody state -- callers integrating a connection's `health` field
        (Connection.health, enums.ConnectionHealth) need a value they can
        read, not an exception they must catch defensively.
        """
        ...


@runtime_checkable
class ConnectionStore(Protocol):
    """
    Organization-scoped persistence boundary for connections, connector
    revisions, executions, receipts and evidence references, per step-two
    contract bound 2: "ConnectionStore persists and retrieves typed
    connection, connector-revision, execution, receipt, and
    evidence-reference records behind organization-scoped methods; callers
    cannot supply or override trusted organization context through generic
    payload data."

    "Organization-scoped" is enforced at the SIGNATURE level, not by
    convention: every method that reads or writes exactly one organization's
    data takes `organization_id: OrganizationId` as its OWN explicit,
    separate keyword parameter -- never bundled inside the stored record as
    the only source of truth for which organization it belongs to. This
    means an implementation is STRUCTURALLY unable to honor a call whose
    `organization_id` argument disagrees with the record it is about to
    read or write without an explicit mismatch check -- the caller cannot
    make that check unreachable by putting a different value in a generic
    payload field, because there is no generic payload parameter anywhere
    on this protocol: every argument is a specific, typed domain model or
    a specific, typed id, never a `dict[str, object]` a caller could stuff
    an organization override into.

    Nothing here writes to SQLite, a file, or any other durable store --
    concrete persistence is step 4's job, out of this step's scope.
    """

    def save_connection(
        self, *, organization_id: OrganizationId, connection: Connection
    ) -> None:
        """
        Persist `connection`. An implementation must reject a `connection`
        whose own `connection.organization_id` disagrees with the
        `organization_id` argument rather than silently trusting one over
        the other -- the two must independently agree, which is exactly
        what "callers cannot supply or override trusted organization
        context through generic payload data" requires when the trusted
        context (the argument) and the payload (`connection`) both name an
        organization.
        """
        ...

    def get_connection(
        self, *, organization_id: OrganizationId, connection_id: ConnectionId
    ) -> Connection | None:
        """
        Return the connection identified by `connection_id` IF it belongs
        to `organization_id`, else None. Never returns a connection
        belonging to a different organization than the one requested --
        this is the concrete cross-tenant-read acceptance check ("two
        organizations sharing a caller key -> no collision, no
        cross-reads") stated as this method's own contract.
        """
        ...

    def save_connector_revision(
        self, *, organization_id: OrganizationId, revision: ConnectorRevision
    ) -> None:
        """
        Persist `revision`. `organization_id` scopes the WRITE (who is
        allowed to register this revision for their own use), not a field
        on ConnectorRevision itself -- connector revisions have no
        organization_id field (connector.py) because a connector revision
        is a shared, connector-level artifact, not a per-organization one;
        scoping here governs write authorization, never record ownership.
        """
        ...

    def get_connector_revision(
        self,
        *,
        organization_id: OrganizationId,
        revision_id: ConnectorRevisionId,
    ) -> ConnectorRevision | None:
        """
        Return the connector revision identified by `revision_id` if
        `organization_id` is authorized to read it, else None.
        """
        ...

    def save_execution(
        self, *, organization_id: OrganizationId, execution: Execution
    ) -> None:
        """
        Persist `execution`. As with `save_connection`, an implementation
        must reject an `execution` whose own `execution.organization_id`
        disagrees with the `organization_id` argument.
        """
        ...

    def get_execution(
        self, *, organization_id: OrganizationId, execution_id: ExecutionId
    ) -> Execution | None:
        """
        Return the execution identified by `execution_id` IF it belongs to
        `organization_id`, else None -- same cross-tenant-read guarantee as
        `get_connection`.
        """
        ...

    def save_receipt(
        self, *, organization_id: OrganizationId, receipt: ExecutionReceipt
    ) -> None:
        """
        Persist `receipt`, append-only. This protocol has no `update_
        receipt` or `delete_receipt` method -- a receipt is durable
        history (receipt.py's own docstring: "durable, append-only record
        of one execution's final (or currently ambiguous) outcome"); a
        resolving receipt is saved as a NEW receipt via this same method,
        never as a mutation of the AMBIGUOUS one it resolves. An
        implementation must reject a `receipt` whose own
        `receipt.organization_id` disagrees with the `organization_id`
        argument, matching `save_connection`/`save_execution`.
        """
        ...

    def get_receipts_for_execution(
        self, *, organization_id: OrganizationId, execution_id: ExecutionId
    ) -> tuple[ExecutionReceipt, ...]:
        """
        Return every receipt recorded for `execution_id`, IF that execution
        belongs to `organization_id`, else an empty tuple -- never a
        receipt belonging to a different organization's execution. Plural
        and ordered by recording, not a single "latest receipt" accessor:
        an AMBIGUOUS execution may have more than one receipt (the original
        AMBIGUOUS one plus a later resolving SUCCEEDED/FAILED_SAFE one),
        and the append-don't-revert history must remain fully readable, not
        collapsed to only the newest row.
        """
        ...

    def save_evidence_reference(
        self,
        *,
        organization_id: OrganizationId,
        execution_id: ExecutionId,
        evidence_ref: ConfirmationEvidenceRef,
    ) -> None:
        """
        Record that `evidence_ref` (a typed, kernel-minted locator per
        identity.py's ConfirmationEvidenceRef) belongs to `execution_id`
        within `organization_id`. This method exists separately from
        `save_receipt` because provenance (which execution, which
        organization, minted when) is a persistence-layer fact about the
        evidence store reference itself, independent of any one receipt
        that happens to carry the same ref value -- the packet's own
        deferred item is "evidence-store provenance," named as a
        still-unpassed acceptance target in the step-one acceptance
        record, and this method is the persistence seam that provenance
        enforcement will later be built against, not the enforcement
        itself.
        """
        ...

    def get_evidence_references_for_execution(
        self, *, organization_id: OrganizationId, execution_id: ExecutionId
    ) -> tuple[ConfirmationEvidenceRef, ...]:
        """
        Return every evidence reference recorded for `execution_id`, IF
        that execution belongs to `organization_id`, else an empty tuple.
        """
        ...


@runtime_checkable
class EffectAuthorizationVerifier(Protocol):
    """
    Verification boundary for one attempted effect's ZEO Go authorization,
    per step-two contract bound 3: "EffectAuthorizationVerifier validates
    exact organization, connection, connector revision, business operation,
    normalized request digest, expiry and replay identity; absence,
    mismatch, expiry, or replay refuses closed."

    This is the single method whose return type structurally enforces
    "refuses closed": `verify` returns AuthorizationVerdict
    (verdicts.py), a frozen model whose own validator makes an
    ambiguous or silently-permissive outcome unrepresentable -- either
    every checked identity field is present and `authorized=True` with no
    refusal_reason, or `authorized=False` with a required, closed-taxonomy
    AuthorizationRefusalReason (ABSENT / *_MISMATCH / EXPIRED / REPLAYED).
    There is no third return shape, and there is no boolean-only overload
    a caller could branch on without also learning why a refusal happened.

    `verify` never raises on an ordinary refusal (absence, mismatch,
    expiry, replay are ALL modeled as REFUSED verdicts, not exceptions) --
    per disposition 2, Zeocore verifies mechanical conditions, it does not
    reconstruct organizational policy, and an exception-per-refusal-reason
    design would push callers toward catching exceptions as control flow
    for an entirely expected outcome. An implementation may still raise for
    a genuine internal error (e.g. the connector revision needed to check
    against is itself unreadable) -- that is not a refusal, it is a
    verifier that cannot complete its check at all, and this protocol does
    not forbid surfacing that distinctly.
    """

    def verify(
        self,
        *,
        authorization: EffectAuthorization | None,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        connector_revision: ConnectorRevisionId,
        operation_id: str,
        request_digest: str,
        now: object,
        seen_nonces: object,
    ) -> AuthorizationVerdict:
        """
        Check `authorization` (which may be None -- the ABSENCE case bound
        3 names explicitly) against the five caller-asserted expectations
        (`organization_id`, `connection_id`, `connector_revision`,
        `operation_id`, `request_digest`) plus expiry (checked against
        `now`, an explicit argument for the same determinism reason
        EffectAuthorization.is_expired takes one -- see authorization.py)
        and replay (checked against `seen_nonces`, an explicit, caller-
        supplied view of prior nonces/idempotency identity rather than a
        verifier-internal cache this protocol would otherwise have to
        smuggle in as hidden state).

        `now` and `seen_nonces` are typed `object` at the protocol level
        deliberately: the concrete shape of a nonce-replay store belongs to
        the persistence layer (ConnectionStore, step 4 concretely wires it),
        which does not exist yet in this step, and a Protocol method must
        not import or presuppose that adapter's shape. A concrete verifier
        implementation (later step) narrows these to real types in its own
        signature; `Protocol` structural conformance is checked on names
        and arity, not on this narrowing, so callers written against this
        protocol already pass a `datetime` and a real replay-check
        structure -- the `object` annotation here does not license passing
        anything less specific in the concrete call sites this protocol
        exists to constrain.

        Returns an AUTHORIZED verdict only when EVERY one of the five
        exact-match checks and both expiry and replay checks pass; returns
        a REFUSED verdict with the single most specific applicable
        AuthorizationRefusalReason otherwise. `authorization is None` must
        produce `refusal_reason=ABSENT`; any of the five mismatches must
        produce the corresponding `*_MISMATCH` reason; an expired
        authorization must produce `EXPIRED`; a previously-seen replay
        identity must produce `REPLAYED`. Never a bare `authorized=False`
        with no reason -- AuthorizationVerdict's own validator makes that
        unconstructable, so a conforming implementation cannot express it
        even by mistake.
        """
        ...
