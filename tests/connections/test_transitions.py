"""
Contract tests for the execution state transition table.

Verifies the minimum path from disposition 12
(CREATED -> AUTHORIZATION_VERIFIED -> PREPARED -> DISPATCH_STARTED ->
SUCCEEDED | FAILED | AMBIGUOUS) is exactly what ALLOWED_TRANSITIONS encodes,
and that disposition 12's "never erases it from history" requirement for
AMBIGUOUS holds: AMBIGUOUS may only move to RECONCILED, and no terminal
state has any outbound transition at all.
"""

from __future__ import annotations

import itertools

from zeo_core.contracts.connections.enums import ExecutionState
from zeo_core.contracts.connections.transitions import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    is_allowed_transition,
    is_terminal,
)


class TestMinimumPath:
    def test_created_moves_only_to_authorization_verified(self) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.CREATED] == frozenset(
            {ExecutionState.AUTHORIZATION_VERIFIED}
        )

    def test_authorization_verified_moves_only_to_prepared(self) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.AUTHORIZATION_VERIFIED] == frozenset(
            {ExecutionState.PREPARED}
        )

    def test_prepared_moves_only_to_dispatch_started(self) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.PREPARED] == frozenset(
            {ExecutionState.DISPATCH_STARTED}
        )

    def test_dispatch_started_moves_to_exactly_the_three_outcomes(self) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.DISPATCH_STARTED] == frozenset(
            {
                ExecutionState.SUCCEEDED,
                ExecutionState.FAILED,
                ExecutionState.AMBIGUOUS,
            }
        )

    def test_full_happy_path_is_allowed_step_by_step(self) -> None:
        path = [
            ExecutionState.CREATED,
            ExecutionState.AUTHORIZATION_VERIFIED,
            ExecutionState.PREPARED,
            ExecutionState.DISPATCH_STARTED,
            ExecutionState.SUCCEEDED,
        ]
        for current, nxt in itertools.pairwise(path):
            assert is_allowed_transition(current, nxt), f"{current} -> {nxt}"


class TestAmbiguousNeverErased:
    """Disposition 12: reconciliation may resolve AMBIGUOUS but never erases
    it from history."""

    def test_ambiguous_moves_only_to_reconciled(self) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.AMBIGUOUS] == frozenset(
            {ExecutionState.RECONCILED}
        )

    def test_ambiguous_cannot_become_succeeded(self) -> None:
        assert not is_allowed_transition(
            ExecutionState.AMBIGUOUS, ExecutionState.SUCCEEDED
        )

    def test_ambiguous_cannot_become_failed(self) -> None:
        assert not is_allowed_transition(
            ExecutionState.AMBIGUOUS, ExecutionState.FAILED
        )

    def test_ambiguous_cannot_be_skipped_back_to_created(self) -> None:
        assert not is_allowed_transition(
            ExecutionState.AMBIGUOUS, ExecutionState.CREATED
        )


class TestTerminalStatesHaveNoOutbound:
    def test_succeeded_is_terminal(self) -> None:
        assert is_terminal(ExecutionState.SUCCEEDED)
        assert ALLOWED_TRANSITIONS[ExecutionState.SUCCEEDED] == frozenset()

    def test_failed_is_terminal(self) -> None:
        assert is_terminal(ExecutionState.FAILED)
        assert ALLOWED_TRANSITIONS[ExecutionState.FAILED] == frozenset()

    def test_reconciled_is_terminal(self) -> None:
        assert is_terminal(ExecutionState.RECONCILED)
        assert ALLOWED_TRANSITIONS[ExecutionState.RECONCILED] == frozenset()

    def test_ambiguous_is_not_terminal(self) -> None:
        # AMBIGUOUS has an outbound transition (to RECONCILED), so it must
        # not appear in TERMINAL_STATES even though it is a "final" outcome
        # of dispatch in the everyday sense.
        assert not is_terminal(ExecutionState.AMBIGUOUS)

    def test_terminal_states_are_exactly_succeeded_failed_reconciled(self) -> None:
        assert TERMINAL_STATES == frozenset(
            {
                ExecutionState.SUCCEEDED,
                ExecutionState.FAILED,
                ExecutionState.RECONCILED,
            }
        )

    def test_no_transition_leaves_a_terminal_state(self) -> None:
        for state in TERMINAL_STATES:
            assert ALLOWED_TRANSITIONS[state] == frozenset()


class TestNoSkippingOrBackwardTransitions:
    def test_cannot_skip_authorization_verified(self) -> None:
        assert not is_allowed_transition(
            ExecutionState.CREATED, ExecutionState.PREPARED
        )

    def test_cannot_skip_directly_to_dispatch_started(self) -> None:
        assert not is_allowed_transition(
            ExecutionState.CREATED, ExecutionState.DISPATCH_STARTED
        )

    def test_cannot_go_backward_from_prepared_to_created(self) -> None:
        assert not is_allowed_transition(
            ExecutionState.PREPARED, ExecutionState.CREATED
        )

    def test_every_state_is_a_key_in_the_table(self) -> None:
        # Every ExecutionState must have an entry (even if the value is an
        # empty set for terminal states) so a lookup miss can never be
        # mistaken for "anything is allowed from here".
        for state in ExecutionState:
            assert state in ALLOWED_TRANSITIONS

    def test_no_self_transitions(self) -> None:
        for state, targets in ALLOWED_TRANSITIONS.items():
            assert state not in targets, f"{state} must not transition to itself"


class TestProbeCanFail:
    """
    Proves is_allowed_transition is a real predicate, not one that always
    returns True, by checking it against a value pair chosen specifically
    because it must be rejected -- and showing the direct dict lookup
    (bypassing the function) would already disagree with an incorrectly
    "permissive" implementation, i.e. this pins the exact boundary rather
    than a property that a stub `return True` could also satisfy.
    """

    def test_is_allowed_transition_returns_false_for_unlisted_pair(self) -> None:
        result = is_allowed_transition(
            ExecutionState.SUCCEEDED, ExecutionState.DISPATCH_STARTED
        )
        assert result is False

    def test_is_allowed_transition_returns_true_for_listed_pair(self) -> None:
        result = is_allowed_transition(
            ExecutionState.DISPATCH_STARTED, ExecutionState.AMBIGUOUS
        )
        assert result is True
