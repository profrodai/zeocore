"""
Execution receipt, per packet sections 10.1 and 10.3-10.4, updated for the
Principal's state-machine ruling (msg_ebff3939, refined by msg_770124cc).

Consumed by: ZEO Go's organizational receipt (packet section 10.1's normal
call path ends "-> ZEO Go organizational receipt"); the (not-yet-built)
orchestration and reconciliation layers (steps 4 and 6, out of this step's
scope).
Must NOT contain: secret material, raw provider tokens, or a synthetic
canary value in any field -- a receipt is exactly the kind of durable,
serialized, long-lived record section 21.5's acceptance checks name
explicitly ("a synthetic canary secret never appears in ... receipt").

A receipt is the durable record of one execution's outcome. It is
deliberately a separate model from Execution (execution.py): Execution is
the live, evolving state-machine snapshot; ExecutionReceipt is the
append-only evidence a reconciliation pass or an auditor reads afterward,
and it carries `reconciliation_evidence` -- a field Execution has no reason
to have, since a still-running execution has nothing to reconcile yet.

There is no RECONCILED final_state. A resolved ambiguity is recorded as an
ordinary SUCCEEDED or FAILED_SAFE receipt that ALSO carries
`reconciliation_evidence` and `resolves_ambiguous_recorded_at` -- the ruled
"reference to the prior ambiguous receipt/transition event." A resolving
receipt without both of those is rejected: reconciliation evidence with no
pointer to what it resolves is exactly the "silent overwrite" the ruling
forbids, and a pointer with no evidence is an unsubstantiated resolution.
An UNRESOLVED reconciliation attempt never claims final_state SUCCEEDED or
FAILED_SAFE at all -- it is recorded as another AMBIGUOUS receipt whose
`reconciliation_attempt_evidence` holds what was tried, so the attempt is
retained as history without pretending a resolution occurred
(no self-transition, no hollow terminal).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from zeo_core.contracts.connections.enums import ExecutionState
from zeo_core.contracts.connections.errors import NormalizedError
from zeo_core.contracts.connections.identity import (
    ConnectionId,
    ExecutionId,
    OrganizationId,
)
from zeo_core.contracts.connections.transitions import is_terminal


class ExecutionReceipt(BaseModel):
    """
    Durable, append-only record of one execution's final (or currently
    ambiguous) outcome.

    `final_state` must be a state the transition table treats as terminal
    for receipt purposes -- SUCCEEDED, FAILED_SAFE, REFUSED or AMBIGUOUS are
    all valid, since the ruling requires ambiguous outcomes to be recorded
    honestly rather than withheld until resolved.

    `normalized_error` is required exactly when `final_state` is FAILED_SAFE,
    and forbidden otherwise, so a receipt can never claim success while also
    carrying error detail or claim failure with no explanation. REFUSED
    deliberately does NOT require normalized_error here: a refusal is
    recorded by admission/authorization declining to dispatch, which is a
    distinct concept from a provider-side NormalizedError (see enums.py's
    note distinguishing ExecutionState from NormalizedErrorCode) -- a future
    step MAY choose to attach diagnostic detail to a refusal, but this
    contract does not mandate it.

    Two DISTINCT things can be true of an AMBIGUOUS-adjacent receipt, and
    they use different field pairs so they can never be confused:
      * a RESOLVING receipt (final_state SUCCEEDED or FAILED_SAFE) that
        closes out a prior ambiguity carries `reconciliation_evidence` AND
        `resolves_ambiguous_recorded_at` (both required together);
      * an UNRESOLVED reconciliation ATTEMPT stays final_state AMBIGUOUS
        and carries `reconciliation_attempt_evidence` instead -- it never
        borrows the resolving pair, because it did not resolve anything.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: ExecutionId
    organization_id: OrganizationId
    connection_id: ConnectionId
    final_state: ExecutionState
    normalized_error: NormalizedError | None = None
    recorded_at: datetime
    dispatch_started_at: datetime | None = None
    resolved_at: datetime | None = None
    # Set together, ONLY on a receipt that resolves a prior AMBIGUOUS
    # outcome to SUCCEEDED or FAILED_SAFE. `resolves_ambiguous_recorded_at`
    # is the `recorded_at` of the specific prior AMBIGUOUS receipt this one
    # resolves -- the ruled "reference to the prior ambiguous
    # receipt/transition event." Append-don't-revert: this receipt does not
    # replace the AMBIGUOUS one, it points at it.
    reconciliation_evidence: str | None = None
    resolves_ambiguous_recorded_at: datetime | None = None
    # Set only on an AMBIGUOUS receipt that records a reconciliation attempt
    # which did NOT produce a trustworthy resolution -- the attempt is
    # retained as history on a still-AMBIGUOUS receipt rather than silently
    # dropped or mistaken for a state change.
    reconciliation_attempt_evidence: str | None = None

    @model_validator(mode="after")
    def _final_state_is_terminal_or_ambiguous(self) -> ExecutionReceipt:
        # AMBIGUOUS is intentionally accepted here even though it is
        # terminal in the receipt sense but NOT terminal in
        # transitions.ALLOWED_TRANSITIONS (it can still move to SUCCEEDED or
        # FAILED_SAFE). A receipt records the outcome known at write time;
        # an AMBIGUOUS receipt is exactly the honest, non-final record the
        # ruling requires, and a later resolving receipt supersedes it
        # without deleting it (append-don't-revert, not this model's job to
        # enforce -- persistence is step 4).
        if not (
            is_terminal(self.final_state)
            or self.final_state == ExecutionState.AMBIGUOUS
        ):
            raise ValueError(
                f"receipt final_state must be terminal or AMBIGUOUS, "
                f"got {self.final_state!s}"
            )
        return self

    @model_validator(mode="after")
    def _error_matches_failed_safe_state(self) -> ExecutionReceipt:
        if (
            self.final_state == ExecutionState.FAILED_SAFE
            and self.normalized_error is None
        ):
            raise ValueError("a FAILED_SAFE receipt must carry normalized_error")
        if (
            self.final_state != ExecutionState.FAILED_SAFE
            and self.normalized_error is not None
        ):
            raise ValueError(
                "normalized_error may only be set when final_state is FAILED_SAFE"
            )
        return self

    @model_validator(mode="after")
    def _attempt_and_resolution_evidence_are_mutually_exclusive(
        self,
    ) -> ExecutionReceipt:
        # Checked FIRST, ahead of the two validators below, so this rule is
        # independently reachable rather than always being pre-empted by a
        # more specific error: an unresolved attempt and a resolution are
        # mutually exclusive claims about the same receipt regardless of
        # what final_state says, and that must be rejected on its own
        # terms, not only as a side effect of some other check firing first.
        if (
            self.reconciliation_attempt_evidence is not None
            and self.reconciliation_evidence is not None
        ):
            raise ValueError(
                "a receipt must not carry both reconciliation_attempt_evidence "
                "(an unresolved attempt) and reconciliation_evidence (a "
                "resolution) -- these are mutually exclusive outcomes"
            )
        return self

    @model_validator(mode="after")
    def _resolution_requires_reconciliation_context(self) -> ExecutionReceipt:
        resolving_pair_set = (
            self.reconciliation_evidence is not None
            or self.resolves_ambiguous_recorded_at is not None
        )
        if not resolving_pair_set:
            return self
        # Both-or-neither: evidence with no pointer to what it resolves is
        # the "silent overwrite" the ruling forbids; a pointer with no
        # evidence is an unsubstantiated resolution.
        if self.reconciliation_evidence is None:
            raise ValueError(
                "a receipt resolving a prior ambiguity must carry "
                "reconciliation_evidence"
            )
        if self.resolves_ambiguous_recorded_at is None:
            raise ValueError(
                "a receipt resolving a prior ambiguity must carry "
                "resolves_ambiguous_recorded_at, referencing the prior "
                "ambiguous receipt/transition event"
            )
        if self.final_state not in (
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED_SAFE,
        ):
            raise ValueError(
                "reconciliation_evidence and resolves_ambiguous_recorded_at "
                "may only be set on a receipt resolving to SUCCEEDED or "
                "FAILED_SAFE, got final_state "
                f"{self.final_state!s}"
            )
        if self.resolved_at is None:
            raise ValueError(
                "a receipt resolving a prior ambiguity must carry resolved_at"
            )
        return self

    @model_validator(mode="after")
    def _attempt_evidence_only_on_still_ambiguous(self) -> ExecutionReceipt:
        if (
            self.reconciliation_attempt_evidence is not None
            and self.final_state != ExecutionState.AMBIGUOUS
        ):
            raise ValueError(
                "reconciliation_attempt_evidence may only be set when "
                "final_state is still AMBIGUOUS -- a resolved receipt uses "
                "reconciliation_evidence instead, never both"
            )
        return self
