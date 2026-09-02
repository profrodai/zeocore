"""
Execution receipt, per packet sections 10.1 and 10.3-10.4.

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
    for receipt purposes -- SUCCEEDED, FAILED, AMBIGUOUS or RECONCILED are
    all valid, since disposition 12 requires ambiguous outcomes to be
    recorded honestly rather than withheld until resolved.
    `normalized_error` is required exactly when `final_state` is FAILED, and
    forbidden otherwise, so a receipt can never claim success while also
    carrying error detail or claim failure with no explanation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: ExecutionId
    organization_id: OrganizationId
    connection_id: ConnectionId
    final_state: ExecutionState
    normalized_error: NormalizedError | None = None
    reconciliation_evidence: str | None = None
    recorded_at: datetime
    dispatch_started_at: datetime | None = None
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def _final_state_is_terminal_or_ambiguous(self) -> ExecutionReceipt:
        # AMBIGUOUS is intentionally accepted here even though it is
        # terminal in the receipt sense but NOT terminal in
        # transitions.ALLOWED_TRANSITIONS (it can still move to RECONCILED).
        # A receipt records the outcome known at write time; an AMBIGUOUS
        # receipt is exactly the honest, non-final record disposition 14
        # requires, and a later RECONCILED receipt supersedes it without
        # deleting it (append-don't-revert, not this model's job to
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
    def _error_matches_failed_state(self) -> ExecutionReceipt:
        if self.final_state == ExecutionState.FAILED and self.normalized_error is None:
            raise ValueError("a FAILED receipt must carry normalized_error")
        if (
            self.final_state != ExecutionState.FAILED
            and self.normalized_error is not None
        ):
            raise ValueError(
                "normalized_error may only be set when final_state is FAILED"
            )
        return self

    @model_validator(mode="after")
    def _resolved_requires_reconciliation_context(self) -> ExecutionReceipt:
        if self.final_state == ExecutionState.RECONCILED:
            if self.reconciliation_evidence is None:
                raise ValueError(
                    "a RECONCILED receipt must carry reconciliation_evidence"
                )
            if self.resolved_at is None:
                raise ValueError("a RECONCILED receipt must carry resolved_at")
        return self
