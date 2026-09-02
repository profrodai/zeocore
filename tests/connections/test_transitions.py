"""
Contract tests for the execution state transition table.

Verifies the minimum path from the Principal's state-machine ruling
(msg_ebff3939, refined by msg_770124cc) -- CREATED -> AUTHORIZATION_VERIFIED
-> PREPARED -> DISPATCH_STARTED -> SUCCEEDED | FAILED_SAFE | AMBIGUOUS -- is
exactly what ALLOWED_TRANSITIONS encodes; that REFUSED is reachable only
before DISPATCH_STARTED; and that the ruling's "never erases it from
history" requirement for AMBIGUOUS holds: AMBIGUOUS may only move to
SUCCEEDED or FAILED_SAFE, and no terminal state has any outbound transition
at all.
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
    def test_created_moves_to_authorization_verified_refused_or_failed_safe(
        self,
    ) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.CREATED] == frozenset(
            {
                ExecutionState.AUTHORIZATION_VERIFIED,
                ExecutionState.REFUSED,
                ExecutionState.FAILED_SAFE,
            }
        )

    def test_authorization_verified_moves_to_prepared_refused_or_failed_safe(
        self,
    ) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.AUTHORIZATION_VERIFIED] == frozenset(
            {
                ExecutionState.PREPARED,
                ExecutionState.REFUSED,
                ExecutionState.FAILED_SAFE,
            }
        )

    def test_prepared_moves_to_dispatch_started_refused_or_failed_safe(self) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.PREPARED] == frozenset(
            {
                ExecutionState.DISPATCH_STARTED,
                ExecutionState.REFUSED,
                ExecutionState.FAILED_SAFE,
            }
        )

    def test_dispatch_started_moves_to_exactly_the_three_outcomes(self) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.DISPATCH_STARTED] == frozenset(
            {
                ExecutionState.SUCCEEDED,
                ExecutionState.FAILED_SAFE,
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


class TestRefusalOnlyBeforeDispatch:
    """
    Proof requirement 3: REFUSED cannot occur after provider dispatch.
    """

    def test_created_can_be_refused(self) -> None:
        assert is_allowed_transition(ExecutionState.CREATED, ExecutionState.REFUSED)

    def test_authorization_verified_can_be_refused(self) -> None:
        assert is_allowed_transition(
            ExecutionState.AUTHORIZATION_VERIFIED, ExecutionState.REFUSED
        )

    def test_prepared_can_be_refused(self) -> None:
        assert is_allowed_transition(ExecutionState.PREPARED, ExecutionState.REFUSED)

    def test_dispatch_started_cannot_be_refused(self) -> None:
        # This is the load-bearing negative: once dispatch has started,
        # REFUSED is no longer a reachable outcome anywhere in the table.
        assert not is_allowed_transition(
            ExecutionState.DISPATCH_STARTED, ExecutionState.REFUSED
        )

    def test_ambiguous_cannot_be_refused(self) -> None:
        assert not is_allowed_transition(
            ExecutionState.AMBIGUOUS, ExecutionState.REFUSED
        )

    def test_refused_appears_in_no_other_states_outbound_set(self) -> None:
        # REFUSED must be reachable ONLY from the three pre-dispatch states.
        reachable_from = {
            state
            for state, targets in ALLOWED_TRANSITIONS.items()
            if ExecutionState.REFUSED in targets
        }
        assert reachable_from == {
            ExecutionState.CREATED,
            ExecutionState.AUTHORIZATION_VERIFIED,
            ExecutionState.PREPARED,
        }


class TestEveryPreDispatchStateReachesBothRefusedAndFailedSafe:
    """
    Proof requirement 8 (msg_bcb88de0): every pre-dispatch state can reach
    BOTH REFUSED and FAILED_SAFE, and no state at or after DISPATCH_STARTED
    can reach REFUSED. This class asserts the REQUIRED edges are PRESENT --
    the positive half Sparring's own withdrawn verification (msg_ac3cd799)
    proved is not covered merely by checking forbidden edges are absent.
    """

    PRE_DISPATCH_STATES = (
        ExecutionState.CREATED,
        ExecutionState.AUTHORIZATION_VERIFIED,
        ExecutionState.PREPARED,
    )

    def test_every_pre_dispatch_state_can_reach_refused(self) -> None:
        for state in self.PRE_DISPATCH_STATES:
            assert is_allowed_transition(state, ExecutionState.REFUSED), (
                f"{state} must be able to reach REFUSED"
            )

    def test_every_pre_dispatch_state_can_reach_failed_safe(self) -> None:
        for state in self.PRE_DISPATCH_STATES:
            assert is_allowed_transition(state, ExecutionState.FAILED_SAFE), (
                f"{state} must be able to reach FAILED_SAFE"
            )

    def test_failed_safe_appears_in_exactly_the_ruled_outbound_sets(self) -> None:
        # FAILED_SAFE must be reachable from the three pre-dispatch states,
        # DISPATCH_STARTED and AMBIGUOUS -- everywhere except SUCCEEDED,
        # REFUSED and FAILED_SAFE itself (all terminal with no outbound).
        reachable_from = {
            state
            for state, targets in ALLOWED_TRANSITIONS.items()
            if ExecutionState.FAILED_SAFE in targets
        }
        assert reachable_from == {
            ExecutionState.CREATED,
            ExecutionState.AUTHORIZATION_VERIFIED,
            ExecutionState.PREPARED,
            ExecutionState.DISPATCH_STARTED,
            ExecutionState.AMBIGUOUS,
        }

    def test_no_state_at_or_after_dispatch_started_can_reach_refused(self) -> None:
        for state in (
            ExecutionState.DISPATCH_STARTED,
            ExecutionState.AMBIGUOUS,
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED_SAFE,
            ExecutionState.REFUSED,
        ):
            assert not is_allowed_transition(state, ExecutionState.REFUSED), (
                f"{state} must not be able to reach REFUSED"
            )


class TestAmbiguousNeverErased:
    """The ruling: reconciliation may resolve AMBIGUOUS but never erases it
    from history, and may only resolve it to SUCCEEDED or FAILED_SAFE."""

    def test_ambiguous_moves_only_to_succeeded_or_failed_safe(self) -> None:
        assert ALLOWED_TRANSITIONS[ExecutionState.AMBIGUOUS] == frozenset(
            {ExecutionState.SUCCEEDED, ExecutionState.FAILED_SAFE}
        )

    def test_ambiguous_can_become_succeeded(self) -> None:
        assert is_allowed_transition(ExecutionState.AMBIGUOUS, ExecutionState.SUCCEEDED)

    def test_ambiguous_can_become_failed_safe(self) -> None:
        assert is_allowed_transition(
            ExecutionState.AMBIGUOUS, ExecutionState.FAILED_SAFE
        )

    def test_ambiguous_cannot_be_skipped_back_to_created(self) -> None:
        assert not is_allowed_transition(
            ExecutionState.AMBIGUOUS, ExecutionState.CREATED
        )

    def test_ambiguous_has_no_self_transition(self) -> None:
        # An unresolved reconciliation attempt must not self-transition
        # AMBIGUOUS -> AMBIGUOUS; the graph does not even offer that edge.
        assert not is_allowed_transition(
            ExecutionState.AMBIGUOUS, ExecutionState.AMBIGUOUS
        )


class TestTerminalStatesHaveNoOutbound:
    def test_succeeded_is_terminal(self) -> None:
        assert is_terminal(ExecutionState.SUCCEEDED)
        assert ALLOWED_TRANSITIONS[ExecutionState.SUCCEEDED] == frozenset()

    def test_failed_safe_is_terminal(self) -> None:
        assert is_terminal(ExecutionState.FAILED_SAFE)
        assert ALLOWED_TRANSITIONS[ExecutionState.FAILED_SAFE] == frozenset()

    def test_refused_is_terminal(self) -> None:
        assert is_terminal(ExecutionState.REFUSED)
        assert ALLOWED_TRANSITIONS[ExecutionState.REFUSED] == frozenset()

    def test_ambiguous_is_not_terminal(self) -> None:
        # AMBIGUOUS has outbound transitions (to SUCCEEDED or FAILED_SAFE),
        # so it must not appear in TERMINAL_STATES even though it is a
        # "final" outcome of dispatch in the everyday sense.
        assert not is_terminal(ExecutionState.AMBIGUOUS)

    def test_terminal_states_are_exactly_succeeded_failed_safe_refused(self) -> None:
        assert TERMINAL_STATES == frozenset(
            {
                ExecutionState.SUCCEEDED,
                ExecutionState.FAILED_SAFE,
                ExecutionState.REFUSED,
            }
        )

    def test_no_transition_leaves_a_terminal_state(self) -> None:
        for state in TERMINAL_STATES:
            assert ALLOWED_TRANSITIONS[state] == frozenset()

    def test_reconciled_state_no_longer_exists(self) -> None:
        # The ruling removes RECONCILED entirely -- pin that no member of
        # ExecutionState carries that name, so a future re-add is a visible
        # test failure, not a silent regression.
        assert "RECONCILED" not in ExecutionState.__members__

    def test_generic_failed_state_no_longer_exists(self) -> None:
        # The ruling removes the generic FAILED entirely, replaced by
        # FAILED_SAFE. Pin the exact member name, not a substring match, so
        # this does not false-positive against FAILED_SAFE.
        assert "FAILED" not in ExecutionState.__members__
        assert "FAILED_SAFE" in ExecutionState.__members__


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
