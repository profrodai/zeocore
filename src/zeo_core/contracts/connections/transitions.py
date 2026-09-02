"""
Execution state transition table, per the Principal's state-machine ruling
(msg_ebff3939, refined by msg_770124cc), superseding disposition 12.

Consumed by: the (not-yet-built) orchestration layer (step 6, out of this
step's scope), and this step's own contract tests.
Must NOT contain: side effects, persistence, provider calls -- this module
is a pure lookup table plus a pure predicate function.

The minimum path is:

    CREATED -> AUTHORIZATION_VERIFIED -> PREPARED -> DISPATCH_STARTED
    -> SUCCEEDED | FAILED_SAFE | AMBIGUOUS

Any pre-dispatch state (CREATED, AUTHORIZATION_VERIFIED, PREPARED) may
instead move to REFUSED or FAILED_SAFE, per the authoritative table in
msg_ebff3939 (re-affirmed against a prior omission by msg_bcb88de0):

    CREATED                -> AUTHORIZATION_VERIFIED | REFUSED | FAILED_SAFE
    AUTHORIZATION_VERIFIED -> PREPARED | REFUSED | FAILED_SAFE
    PREPARED               -> DISPATCH_STARTED | REFUSED | FAILED_SAFE
    DISPATCH_STARTED       -> SUCCEEDED | FAILED_SAFE | AMBIGUOUS
    AMBIGUOUS              -> SUCCEEDED | FAILED_SAFE

REFUSED means the kernel deliberately made zero provider calls -- admission
or authorization declined to dispatch at all. REFUSED is reachable ONLY
before DISPATCH_STARTED: once dispatch has started, refusal is no longer a
possible outcome (proof requirement 3), so DISPATCH_STARTED's outbound set
does not include REFUSED. FAILED_SAFE from a pre-dispatch state means a
known-no-effect OPERATIONAL failure occurred before any provider call was
attempted (e.g. custody or normalization failed outright) -- distinct from
REFUSED's deliberate zero-dispatch rejection, and distinct from a
post-dispatch FAILED_SAFE, which instead proves a definitive provider
response showing no effect occurred.

The ruling requires the path to be durable and monotonic and requires that
reconciliation "may resolve AMBIGUOUS but never erases it from history."
This module expresses that requirement as a transition rule: AMBIGUOUS may
move forward to SUCCEEDED or FAILED_SAFE ONLY -- never directly from
DISPATCH_STARTED's other outcomes, always through AMBIGUOUS's own two-target
set -- and nothing may transition FROM a terminal state back into the
non-terminal path. There is no RECONCILED state: a resolved ambiguity is an
ordinary SUCCEEDED or FAILED_SAFE, distinguished from a direct dispatch
outcome only by the receipt evidence it carries (receipt.py), not by a
fourth terminal shape. An unresolved reconciliation attempt is not a
transition at all -- see receipt.py's reconciliation_attempts for how that
history is retained without moving current state.
"""

from __future__ import annotations

from zeo_core.contracts.connections.enums import ExecutionState

#: The one authoritative transition table. Each key's value set is exactly
#: the states execution may move to FROM that key. A state with an empty
#: set is terminal -- nothing may leave it.
ALLOWED_TRANSITIONS: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.CREATED: frozenset(
        {
            ExecutionState.AUTHORIZATION_VERIFIED,
            ExecutionState.REFUSED,
            ExecutionState.FAILED_SAFE,
        }
    ),
    ExecutionState.AUTHORIZATION_VERIFIED: frozenset(
        {
            ExecutionState.PREPARED,
            ExecutionState.REFUSED,
            ExecutionState.FAILED_SAFE,
        }
    ),
    ExecutionState.PREPARED: frozenset(
        {
            ExecutionState.DISPATCH_STARTED,
            ExecutionState.REFUSED,
            ExecutionState.FAILED_SAFE,
        }
    ),
    ExecutionState.DISPATCH_STARTED: frozenset(
        {
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED_SAFE,
            ExecutionState.AMBIGUOUS,
        }
    ),
    ExecutionState.AMBIGUOUS: frozenset(
        {ExecutionState.SUCCEEDED, ExecutionState.FAILED_SAFE}
    ),
    ExecutionState.SUCCEEDED: frozenset(),
    ExecutionState.FAILED_SAFE: frozenset(),
    ExecutionState.REFUSED: frozenset(),
}

#: Terminal states: no outbound transition exists for any of these. Derived
#: from ALLOWED_TRANSITIONS rather than listed a second time by hand, so the
#: two can never silently disagree.
TERMINAL_STATES: frozenset[ExecutionState] = frozenset(
    state for state, targets in ALLOWED_TRANSITIONS.items() if not targets
)


def is_allowed_transition(current: ExecutionState, proposed: ExecutionState) -> bool:
    """
    Return True iff moving execution from `current` to `proposed` is a
    permitted STATE-GRAPH edge under the Principal's ruling.

    This is a pure predicate over states only: it does not mutate anything,
    does not look at wall-clock time, and does not know about connections,
    authorizations, providers, or reconciliation evidence. In particular,
    `is_allowed_transition(AMBIGUOUS, SUCCEEDED)` being True means that edge
    EXISTS in the graph -- it does NOT mean a given resolution is valid.
    The ruling's "AMBIGUOUS requires reconciliation evidence and a reference
    to the prior ambiguous event to resolve" is a stronger, evidence-bearing
    requirement enforced at the receipt layer (receipt.py's
    `_resolution_requires_reconciliation_context` validator), not here --
    this module has no evidence parameter to check it against. The
    orchestration layer (step 6) is expected to call this graph predicate
    before persisting any state change AND to require the receipt-level
    evidence check before treating an AMBIGUOUS execution as resolved --
    that wiring is out of this step's scope, but both predicates it will
    need already exist and are fully tested here and in receipt.py.

    Example:
        >>> is_allowed_transition(
        ...     ExecutionState.DISPATCH_STARTED, ExecutionState.AMBIGUOUS
        ... )
        True
        >>> is_allowed_transition(
        ...     ExecutionState.AMBIGUOUS, ExecutionState.SUCCEEDED
        ... )
        True
        >>> is_allowed_transition(
        ...     ExecutionState.PREPARED, ExecutionState.REFUSED
        ... )
        True
        >>> is_allowed_transition(
        ...     ExecutionState.DISPATCH_STARTED, ExecutionState.REFUSED
        ... )
        False
    """
    return proposed in ALLOWED_TRANSITIONS.get(current, frozenset())


def is_terminal(state: ExecutionState) -> bool:
    """Return True iff `state` has no allowed outbound transition."""
    return state in TERMINAL_STATES
