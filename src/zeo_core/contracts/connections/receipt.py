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

RECEIPT INVARIANTS, per the durable ruling (msg_ebff3939) and its
completion (msg_bcb88de0, which corrected two inversions present in an
earlier revision of this file):
  * SUCCEEDED forbids `normalized_error`.
  * REFUSED and FAILED_SAFE both REQUIRE `normalized_error` -- REFUSED is a
    deliberate zero-provider-call rejection and its normalized_error is the
    refusal reason; there is deliberately no separate `refusal_reason`
    field, because that would duplicate this one (msg_bcb88de0 is explicit
    that a parallel field must not be added).
  * AMBIGUOUS REQUIRES `normalized_error` whose `code` is exactly
    RESULT_AMBIGUOUS -- no other normalized category is valid on an
    AMBIGUOUS receipt.
  * Every SUCCEEDED receipt -- not only one resolving a prior AMBIGUOUS --
    requires a non-empty, opaque `confirmation_evidence_ref` pointing at
    durable, sanitized confirmation evidence, and requires
    `dispatch_started_at`. `confirmation_evidence_ref` is forbidden on
    REFUSED, FAILED_SAFE and AMBIGUOUS. A reconciled success requires this
    ref IN ADDITION TO `reconciliation_evidence`,
    `resolves_ambiguous_recorded_at` and `resolved_at` -- each proves a
    different fact (positive confirmation vs. the reconciliation act vs.
    the pointer to what was resolved vs. when) and none substitutes for
    another.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from zeo_core.contracts.connections.enums import ExecutionState, NormalizedErrorCode
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

    `normalized_error` requirements are STATE-DEPENDENT, per msg_bcb88de0's
    correction of an earlier inversion:
      * SUCCEEDED FORBIDS it (a positively-confirmed success has no error).
      * REFUSED REQUIRES it -- the refusal reason IS the structured
        normalized_error; there is deliberately no separate
        `refusal_reason` field duplicating it.
      * FAILED_SAFE REQUIRES it.
      * AMBIGUOUS REQUIRES it, and further requires its `code` be exactly
        RESULT_AMBIGUOUS -- no other normalized category is valid here.

    `confirmation_evidence_ref` is required exactly when `final_state` is
    SUCCEEDED (direct or reconciled) and forbidden otherwise. It is a
    non-empty, opaque pointer to durable, sanitized confirmation evidence --
    it must NEVER carry a raw provider response, token, credential or any
    secret-bearing payload. A SUCCEEDED receipt also requires
    `dispatch_started_at`: positive confirmation without a record of when
    dispatch began is not a complete success proof.

    Two DISTINCT things can be true of an AMBIGUOUS-adjacent receipt, and
    they use different field pairs so they can never be confused:
      * a RESOLVING receipt (final_state SUCCEEDED or FAILED_SAFE) that
        closes out a prior ambiguity carries `reconciliation_evidence` AND
        `resolves_ambiguous_recorded_at` (both required together); if it
        resolves to SUCCEEDED it ALSO requires `confirmation_evidence_ref`
        and `dispatch_started_at` like any other SUCCEEDED receipt --
        reconciliation evidence proves the reconciliation act, it does not
        substitute for positive confirmation of the effect itself;
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
    # Non-empty, opaque pointer to durable, sanitized confirmation evidence.
    # Required exactly when final_state is SUCCEEDED (direct or reconciled),
    # forbidden otherwise (msg_bcb88de0's direct-success decision). Must
    # NEVER carry a raw provider response, token, credential or any
    # secret-bearing payload -- callers construct this from a sanitized
    # evidence store (out of this step's scope), never from provider output
    # directly.
    confirmation_evidence_ref: str | None = None
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
    def _error_matches_final_state(self) -> ExecutionReceipt:
        # State-dependent normalized_error requirement, per the durable
        # ruling (msg_ebff3939) as completed by msg_bcb88de0, which
        # corrected an earlier revision's inversion (that revision required
        # an error only for FAILED_SAFE and forbade one on REFUSED and
        # AMBIGUOUS -- backwards for two of the four states):
        #   SUCCEEDED   -> FORBIDDEN
        #   REFUSED     -> REQUIRED (the refusal reason IS normalized_error;
        #                  no parallel refusal_reason field is added)
        #   FAILED_SAFE -> REQUIRED
        #   AMBIGUOUS   -> REQUIRED, and code must be exactly RESULT_AMBIGUOUS
        if self.final_state == ExecutionState.SUCCEEDED:
            if self.normalized_error is not None:
                raise ValueError(
                    "normalized_error may only be set when final_state is "
                    "REFUSED, FAILED_SAFE or AMBIGUOUS -- SUCCEEDED forbids it"
                )
            return self
        if self.final_state == ExecutionState.REFUSED:
            if self.normalized_error is None:
                raise ValueError("a REFUSED receipt must carry normalized_error")
            return self
        if self.final_state == ExecutionState.FAILED_SAFE:
            if self.normalized_error is None:
                raise ValueError("a FAILED_SAFE receipt must carry normalized_error")
            return self
        if self.final_state == ExecutionState.AMBIGUOUS:
            if self.normalized_error is None:
                raise ValueError(
                    "an AMBIGUOUS receipt must carry normalized_error with "
                    "code RESULT_AMBIGUOUS"
                )
            if self.normalized_error.code != NormalizedErrorCode.RESULT_AMBIGUOUS:
                raise ValueError(
                    "an AMBIGUOUS receipt's normalized_error.code must be "
                    "exactly RESULT_AMBIGUOUS, got "
                    f"{self.normalized_error.code!s}"
                )
            return self
        # final_state is CREATED or another non-terminal, non-AMBIGUOUS
        # value -- already rejected by _final_state_is_terminal_or_ambiguous,
        # but keep this branch inert rather than assuming unreachability.
        return self

    @model_validator(mode="after")
    def _confirmation_evidence_ref_matches_succeeded_state(
        self,
    ) -> ExecutionReceipt:
        # msg_bcb88de0's direct-success decision: EVERY SUCCEEDED receipt,
        # not only one resolving a prior AMBIGUOUS outcome, requires a
        # non-empty confirmation_evidence_ref and is forbidden from carrying
        # one otherwise.
        if self.final_state == ExecutionState.SUCCEEDED:
            if (
                self.confirmation_evidence_ref is None
                or not self.confirmation_evidence_ref.strip()
            ):
                raise ValueError(
                    "a SUCCEEDED receipt must carry a non-empty "
                    "confirmation_evidence_ref"
                )
            if self.dispatch_started_at is None:
                raise ValueError("a SUCCEEDED receipt must carry dispatch_started_at")
        elif self.confirmation_evidence_ref is not None:
            raise ValueError(
                "confirmation_evidence_ref may only be set when final_state "
                "is SUCCEEDED"
            )
        return self

    @model_validator(mode="after")
    def _refused_forbids_dispatch_started_at(self) -> ExecutionReceipt:
        # REFUSED is reachable only before DISPATCH_STARTED (transitions.py);
        # a REFUSED receipt carrying dispatch_started_at would claim a
        # provider dispatch began on a zero-dispatch rejection, which is a
        # contradiction the transition table itself rules out.
        if (
            self.final_state == ExecutionState.REFUSED
            and self.dispatch_started_at is not None
        ):
            raise ValueError(
                "a REFUSED receipt must not carry dispatch_started_at -- "
                "REFUSED means zero provider calls were made"
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
