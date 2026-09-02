"""
Execution state transition table, per ZC0-KERNEL-SEAM-01 disposition 12.

Consumed by: the (not-yet-built) orchestration layer (step 6, out of this
step's scope), and this step's own contract tests.
Must NOT contain: side effects, persistence, provider calls -- this module
is a pure lookup table plus a pure predicate function.

The minimum path is:

    CREATED -> AUTHORIZATION_VERIFIED -> PREPARED -> DISPATCH_STARTED
    -> SUCCEEDED | FAILED | AMBIGUOUS

Disposition 12 requires the path to be durable and monotonic and requires
that reconciliation "may resolve AMBIGUOUS but never erases it from
history." This module expresses that second requirement as a transition
rule: AMBIGUOUS may move forward to RECONCILED (a new state recording that
reconciliation ran and produced a trustworthy answer), but nothing may
transition FROM a terminal state back into the non-terminal path, and
AMBIGUOUS is never silently overwritten by SUCCEEDED or FAILED -- only by
the explicit RECONCILED state added in enums.py for exactly this purpose.
"""

from __future__ import annotations

from zeo_core.contracts.connections.enums import ExecutionState

#: The one authoritative transition table. Each key's value set is exactly
#: the states execution may move to FROM that key. A state with an empty
#: set is terminal -- nothing may leave it.
ALLOWED_TRANSITIONS: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.CREATED: frozenset({ExecutionState.AUTHORIZATION_VERIFIED}),
    ExecutionState.AUTHORIZATION_VERIFIED: frozenset({ExecutionState.PREPARED}),
    ExecutionState.PREPARED: frozenset({ExecutionState.DISPATCH_STARTED}),
    ExecutionState.DISPATCH_STARTED: frozenset(
        {
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED,
            ExecutionState.AMBIGUOUS,
        }
    ),
    ExecutionState.AMBIGUOUS: frozenset({ExecutionState.RECONCILED}),
    ExecutionState.SUCCEEDED: frozenset(),
    ExecutionState.FAILED: frozenset(),
    ExecutionState.RECONCILED: frozenset(),
}

#: Terminal states: no outbound transition exists for any of these. Derived
#: from ALLOWED_TRANSITIONS rather than listed a second time by hand, so the
#: two can never silently disagree.
TERMINAL_STATES: frozenset[ExecutionState] = frozenset(
    state for state, targets in ALLOWED_TRANSITIONS.items() if not targets
)


def is_allowed_transition(current: ExecutionState, proposed: ExecutionState) -> bool:
    """
    Return True iff moving execution from `current` to `proposed` is
    permitted by disposition 12's state machine.

    This is a pure predicate: it does not mutate anything, does not look at
    wall-clock time, and does not know about connections, authorizations or
    providers. The orchestration layer (step 6) is expected to call this
    before persisting any state change and refuse the write if it returns
    False -- that wiring is out of this step's scope, but the predicate it
    will need already exists and is fully tested here.

    Example:
        >>> is_allowed_transition(
        ...     ExecutionState.DISPATCH_STARTED, ExecutionState.AMBIGUOUS
        ... )
        True
        >>> is_allowed_transition(
        ...     ExecutionState.AMBIGUOUS, ExecutionState.SUCCEEDED
        ... )
        False
    """
    return proposed in ALLOWED_TRANSITIONS.get(current, frozenset())


def is_terminal(state: ExecutionState) -> bool:
    """Return True iff `state` has no allowed outbound transition."""
    return state in TERMINAL_STATES
