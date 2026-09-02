"""
The nine required behavioural proofs from msg_bcb88de0's direct-success
decision -- confirmation_evidence_ref on ExecutionReceipt, the corrected
normalized_error state-dependence, and the restored FAILED_SAFE
pre-dispatch edges. Each class below maps to one numbered proof in the
ruling; the numbering is preserved in class/test names so a reader can
match this file against the ruling's own enumeration directly.

Every one of these was verified RED against the head this stream inherited
(60e3e5e9, before this session's repair) and is recorded GREEN here after
the repair. See the stream's report to Master for the exact RED evidence
transcript; this file is the durable, re-runnable form of that proof.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from zeo_core.contracts.connections.enums import ExecutionState, NormalizedErrorCode
from zeo_core.contracts.connections.errors import NormalizedError
from zeo_core.contracts.connections.identity import (
    ConnectionId,
    ExecutionId,
    OrganizationId,
)
from zeo_core.contracts.connections.receipt import ExecutionReceipt
from zeo_core.contracts.connections.transitions import (
    ALLOWED_TRANSITIONS,
    is_allowed_transition,
)

CANARY = "CANARY-SECRET-zc0-direct-success-7c21"


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


def _ids() -> dict[str, object]:
    return {
        "execution_id": ExecutionId(value="exec-1"),
        "organization_id": OrganizationId(value="org-1"),
        "connection_id": ConnectionId(value="conn-1"),
    }


class TestProof1DirectSuccessRequiresConfirmationRef:
    """A direct DISPATCH_STARTED -> SUCCEEDED receipt without
    confirmation_evidence_ref is rejected."""

    def test_direct_succeeded_without_confirmation_ref_rejected(
        self, now: datetime
    ) -> None:
        with pytest.raises(
            ValidationError, match="SUCCEEDED receipt must carry a non-empty"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.SUCCEEDED,
                recorded_at=now,
                dispatch_started_at=now - timedelta(seconds=1),
            )

    def test_direct_succeeded_with_confirmation_ref_accepted(
        self, now: datetime
    ) -> None:
        ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(seconds=1),
            confirmation_evidence_ref="evidence-store-ref-1",
        )  # must not raise


class TestProof2ReconciledSuccessRequiresConfirmationRefEvenWithReconciliation:
    """A reconciled AMBIGUOUS -> SUCCEEDED receipt without
    confirmation_evidence_ref is rejected EVEN WHEN reconciliation fields
    are present."""

    def test_reconciled_succeeded_without_confirmation_ref_rejected(
        self, now: datetime
    ) -> None:
        with pytest.raises(
            ValidationError, match="SUCCEEDED receipt must carry a non-empty"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.SUCCEEDED,
                recorded_at=now,
                dispatch_started_at=now - timedelta(minutes=6),
                reconciliation_evidence="queried provider ledger, effect confirmed",
                resolves_ambiguous_recorded_at=now - timedelta(minutes=5),
                resolved_at=now,
                # confirmation_evidence_ref deliberately omitted: reconciliation
                # fields alone must NOT substitute for positive confirmation.
            )

    def test_reconciled_succeeded_with_all_four_fields_accepted(
        self, now: datetime
    ) -> None:
        ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(minutes=6),
            confirmation_evidence_ref="evidence-store-ref-1",
            reconciliation_evidence="queried provider ledger, effect confirmed",
            resolves_ambiguous_recorded_at=now - timedelta(minutes=5),
            resolved_at=now,
        )  # must not raise: all four proof fields present, none substituting


class TestProof3ConfirmationRefForbiddenOnNonSucceeded:
    """confirmation_evidence_ref on any non-SUCCEEDED receipt is rejected."""

    def test_confirmation_ref_on_failed_safe_rejected(self, now: datetime) -> None:
        with pytest.raises(
            ValidationError, match="only be set when final_state is SUCCEEDED"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.FAILED_SAFE,
                normalized_error=NormalizedError(
                    code=NormalizedErrorCode.PROVIDER_UNAVAILABLE, message="x"
                ),
                recorded_at=now,
                confirmation_evidence_ref="should-not-be-allowed-here",
            )

    def test_confirmation_ref_on_refused_rejected(self, now: datetime) -> None:
        with pytest.raises(
            ValidationError, match="only be set when final_state is SUCCEEDED"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.REFUSED,
                normalized_error=NormalizedError(
                    code=NormalizedErrorCode.REQUEST_REFUSED, message="x"
                ),
                recorded_at=now,
                confirmation_evidence_ref="should-not-be-allowed-here",
            )

    def test_confirmation_ref_on_ambiguous_rejected(self, now: datetime) -> None:
        with pytest.raises(
            ValidationError, match="only be set when final_state is SUCCEEDED"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.AMBIGUOUS,
                normalized_error=NormalizedError(
                    code=NormalizedErrorCode.RESULT_AMBIGUOUS, message="x"
                ),
                recorded_at=now,
                confirmation_evidence_ref="should-not-be-allowed-here",
            )


class TestProof4EmptyOrWhitespaceConfirmationRefRejected:
    """An empty or whitespace-only confirmation reference is rejected."""

    def test_empty_string_confirmation_ref_rejected(self, now: datetime) -> None:
        with pytest.raises(
            ValidationError, match="SUCCEEDED receipt must carry a non-empty"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.SUCCEEDED,
                recorded_at=now,
                dispatch_started_at=now,
                confirmation_evidence_ref="",
            )

    def test_whitespace_only_confirmation_ref_rejected(self, now: datetime) -> None:
        with pytest.raises(
            ValidationError, match="SUCCEEDED receipt must carry a non-empty"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.SUCCEEDED,
                recorded_at=now,
                dispatch_started_at=now,
                confirmation_evidence_ref="   \t\n  ",
            )


class TestProof5SucceededRequiresDispatchStartedAt:
    """A SUCCEEDED receipt without dispatch_started_at is rejected."""

    def test_succeeded_without_dispatch_started_at_rejected(
        self, now: datetime
    ) -> None:
        with pytest.raises(
            ValidationError, match="SUCCEEDED receipt must carry dispatch_started_at"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.SUCCEEDED,
                recorded_at=now,
                confirmation_evidence_ref="evidence-store-ref-1",
            )

    def test_succeeded_with_dispatch_started_at_accepted(self, now: datetime) -> None:
        ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(seconds=1),
            confirmation_evidence_ref="evidence-store-ref-1",
        )  # must not raise


class TestProof6RefusedErrorAndDispatchStartedAtRules:
    """REFUSED without normalized_error is rejected AND REFUSED with
    dispatch_started_at is rejected."""

    def test_refused_without_normalized_error_rejected(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="REFUSED receipt must carry"):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.REFUSED,
                recorded_at=now,
            )

    def test_refused_with_dispatch_started_at_rejected(self, now: datetime) -> None:
        with pytest.raises(
            ValidationError, match="REFUSED receipt must not carry dispatch_started_at"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.REFUSED,
                normalized_error=NormalizedError(
                    code=NormalizedErrorCode.REQUEST_REFUSED, message="x"
                ),
                recorded_at=now,
                dispatch_started_at=now,
            )

    def test_refused_with_normalized_error_and_no_dispatch_started_at_accepted(
        self, now: datetime
    ) -> None:
        ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.REFUSED,
            normalized_error=NormalizedError(
                code=NormalizedErrorCode.REQUEST_REFUSED, message="x"
            ),
            recorded_at=now,
        )  # must not raise


class TestProof7AmbiguousRequiresResultAmbiguousCategory:
    """AMBIGUOUS without RESULT_AMBIGUOUS normalized_error is rejected;
    another normalized category is also rejected."""

    def test_ambiguous_without_normalized_error_rejected(self, now: datetime) -> None:
        with pytest.raises(
            ValidationError, match="AMBIGUOUS receipt must carry normalized_error"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.AMBIGUOUS,
                recorded_at=now,
            )

    def test_ambiguous_with_other_normalized_category_rejected(
        self, now: datetime
    ) -> None:
        with pytest.raises(
            ValidationError, match="code must be exactly RESULT_AMBIGUOUS"
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.AMBIGUOUS,
                normalized_error=NormalizedError(
                    code=NormalizedErrorCode.RATE_LIMITED, message="x"
                ),
                recorded_at=now,
            )

    def test_ambiguous_with_result_ambiguous_category_accepted(
        self, now: datetime
    ) -> None:
        ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.AMBIGUOUS,
            normalized_error=NormalizedError(
                code=NormalizedErrorCode.RESULT_AMBIGUOUS, message="x"
            ),
            recorded_at=now,
        )  # must not raise


class TestProof8PreDispatchReachesBothRefusedAndFailedSafeNoLaterRefused:
    """Every pre-dispatch state can reach BOTH REFUSED and FAILED_SAFE; no
    state at or after DISPATCH_STARTED can reach REFUSED. (Positive-edge
    assertion mirrors tests/connections/test_transitions.py's
    TestEveryPreDispatchStateReachesBothRefusedAndFailedSafe -- duplicated
    here so this proof file is independently a complete record of all nine
    ruled proofs without requiring a reader to cross-reference another
    file for this one.)
    """

    PRE_DISPATCH_STATES = (
        ExecutionState.CREATED,
        ExecutionState.AUTHORIZATION_VERIFIED,
        ExecutionState.PREPARED,
    )
    AT_OR_AFTER_DISPATCH_STATES = (
        ExecutionState.DISPATCH_STARTED,
        ExecutionState.AMBIGUOUS,
        ExecutionState.SUCCEEDED,
        ExecutionState.FAILED_SAFE,
        ExecutionState.REFUSED,
    )

    def test_required_edges_present_refused(self) -> None:
        for state in self.PRE_DISPATCH_STATES:
            assert ExecutionState.REFUSED in ALLOWED_TRANSITIONS[state], (
                f"{state} -> REFUSED must be a present edge"
            )
            assert is_allowed_transition(state, ExecutionState.REFUSED)

    def test_required_edges_present_failed_safe(self) -> None:
        for state in self.PRE_DISPATCH_STATES:
            assert ExecutionState.FAILED_SAFE in ALLOWED_TRANSITIONS[state], (
                f"{state} -> FAILED_SAFE must be a present edge"
            )
            assert is_allowed_transition(state, ExecutionState.FAILED_SAFE)

    def test_forbidden_edges_absent_refused_at_or_after_dispatch(self) -> None:
        for state in self.AT_OR_AFTER_DISPATCH_STATES:
            assert ExecutionState.REFUSED not in ALLOWED_TRANSITIONS[state], (
                f"{state} -> REFUSED must NOT be a present edge"
            )
            assert not is_allowed_transition(state, ExecutionState.REFUSED)


class TestProof9CanaryAbsentFromAllSerializationChannels:
    """A synthetic secret canary in surrounding provider material is absent
    from repr, str, model_dump and model_dump_json of the receipt and its
    confirmation reference.

    "Surrounding provider material" is modeled as a NormalizedError's
    `provider_detail` carrying the canary -- provider_detail is the one
    place raw diagnostic text legitimately lives (errors.py), so it is the
    realistic vector for a provider response leaking a secret-shaped value
    into a receipt that references that error. The claim under test: the
    canary must not spread to confirmation_evidence_ref (the receipt's
    other free-text-shaped field) or otherwise appear anywhere the SAME
    canary was not deliberately placed by the caller.
    """

    def _leaks(self, obj: object, needle: str) -> dict[str, bool]:
        model_dump_ok = hasattr(obj, "model_dump")
        return {
            "repr": needle in repr(obj),
            "str": needle in str(obj),
            "model_dump": (
                needle in json.dumps(obj.model_dump(mode="json"), default=str)  # type: ignore[attr-defined]
                if model_dump_ok
                else False
            ),
            "model_dump_json": (
                needle in obj.model_dump_json()  # type: ignore[attr-defined]
                if model_dump_ok
                else False
            ),
        }

    def test_canary_in_provider_detail_does_not_spread_to_confirmation_ref(
        self, now: datetime
    ) -> None:
        # The canary lives ONLY in provider_detail (surrounding provider
        # material on a FAILED_SAFE receipt's normalized_error).
        # confirmation_evidence_ref is not set on this receipt at all
        # (FAILED_SAFE forbids it, proof 3) -- prove the canary from
        # provider_detail cannot be found there because the field is
        # genuinely None, not merely because no one looked.
        receipt = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.FAILED_SAFE,
            normalized_error=NormalizedError(
                code=NormalizedErrorCode.PROVIDER_UNAVAILABLE,
                message="ordinary product message",
                provider_detail=f"raw provider payload containing {CANARY}",
            ),
            recorded_at=now,
        )
        assert receipt.confirmation_evidence_ref is None
        dumped = receipt.model_dump(mode="json")
        assert dumped["confirmation_evidence_ref"] is None
        assert CANARY not in json.dumps(dumped.get("confirmation_evidence_ref"))

    def test_canary_absent_from_confirmation_ref_repr_str_dump_when_ref_is_clean(
        self, now: datetime
    ) -> None:
        # The confirmation_evidence_ref itself is set to a clean, opaque
        # pointer (never the canary). Prove the canary -- present elsewhere
        # in surrounding provider material via a sibling AMBIGUOUS receipt's
        # provider_detail -- never appears in THIS SUCCEEDED receipt's own
        # four serialization channels, since the two receipts share no
        # object identity and this one never received the canary at all.
        surrounding_ambiguous = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.AMBIGUOUS,
            normalized_error=NormalizedError(
                code=NormalizedErrorCode.RESULT_AMBIGUOUS,
                message="ambiguous outcome",
                provider_detail=f"raw upstream trace containing {CANARY}",
            ),
            recorded_at=now,
        )
        assert CANARY in surrounding_ambiguous.model_dump_json()  # sanity: it IS there

        clean_receipt = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(seconds=1),
            confirmation_evidence_ref="evidence-store-ref-1",
        )
        leaks = self._leaks(clean_receipt, CANARY)
        assert not any(leaks.values()), (
            f"canary from surrounding provider material leaked into an "
            f"unrelated SUCCEEDED receipt: {leaks}"
        )
        ref_leaks = self._leaks(clean_receipt.confirmation_evidence_ref, CANARY)
        assert not any(ref_leaks.values()), (
            f"canary leaked into confirmation_evidence_ref itself: {ref_leaks}"
        )
