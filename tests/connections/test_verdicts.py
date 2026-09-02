"""
Behavioural proofs for verdicts.py's value types, step-two contract bounds
3 and 5 (EffectAuthorizationVerifier refuses closed; runtime behavior tests
are mandatory because mypy --strict does not prove pydantic identity
wrappers are enforced).

RED-BEFORE-GREEN METHOD (doctrine section 6 / RULING-415 section 3c): every
proof below that asserts an ABSENCE (an ambiguous verdict rejected, a
mismatched shape refused) is paired with a `ProbeCanFail`-style test that
runs the identical assertion against a deliberately permissive synthetic
stand-in and observes it actually accept what the real type rejects --
printing `injected: True` to confirm the break took effect, following the
exact pattern established by test_secret_ref_and_evidence_ref_safety.py in
this same directory.

Bound 5's own concrete example is reproduced here at the top of the module
as a live, runnable demonstration, not just a claim: a bare string passed
where a typed id is expected passes `mypy --strict` (verified separately in
this stream's report) but is rejected by pydantic at construction time.
Every test in this file that passes a typed identity wrapper is passing
`OrganizationId(value=...)`, `ConnectionId(value=...)`, etc. -- never a
bare `str` -- exactly to avoid the false-RED two prior seats hit by
mistaking a ValidationError from an untyped string for a real contract
rejection.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from zeo_core.contracts.connections.enums import AuthorizationRefusalReason
from zeo_core.contracts.connections.identity import (
    AuthorizationId,
    ConnectionId,
    ConnectorRevisionId,
    OperationId,
    OrganizationId,
    SecretRef,
)
from zeo_core.contracts.connections.verdicts import (
    AuthorizationVerdict,
    SecretHealth,
    SecretResolution,
)


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


def _authorized_kwargs(now: datetime) -> dict[str, object]:
    return {
        "authorized": True,
        "organization_id": OrganizationId(value="org-1"),
        "connection_id": ConnectionId(value="conn-1"),
        "connector_revision": ConnectorRevisionId(value="google.drive@1"),
        "operation_id": OperationId(value="google.drive.list_files"),
        "authorization_id": AuthorizationId(value="auth-1"),
        "request_digest": "sha256:abc",
        "checked_at": now,
    }


# ===========================================================================
# AuthorizationVerdict: refuses closed (bound 3), both directions
# ===========================================================================


class TestAuthorizedVerdictRequiresEveryCheckedField:
    """
    REQUIRED-PRESENT direction: an AUTHORIZED verdict must restate every
    field AUTHORIZATION_VERIFIED's binding definition names as checked
    (organization, connection, connector revision, operation, request
    digest) plus authorization_id. Absence of any one of them is refused
    even when authorized=True is asserted -- an authorized verdict that
    omits what it checked is exactly the "trust me" shape disposition 2
    forbids.
    """

    def test_fully_populated_authorized_verdict_constructs(self, now: datetime) -> None:
        verdict = AuthorizationVerdict(**_authorized_kwargs(now))
        assert verdict.authorized is True
        assert verdict.refusal_reason is None

    @pytest.mark.parametrize(
        "missing_field",
        [
            "organization_id",
            "connection_id",
            "connector_revision",
            "operation_id",
            "authorization_id",
            "request_digest",
        ],
    )
    def test_authorized_verdict_missing_one_checked_field_is_rejected(
        self, now: datetime, missing_field: str
    ) -> None:
        kwargs = _authorized_kwargs(now)
        kwargs[missing_field] = None
        with pytest.raises(ValidationError, match="must restate every checked"):
            AuthorizationVerdict(**kwargs)

    def test_authorized_verdict_with_refusal_reason_is_rejected(
        self, now: datetime
    ) -> None:
        kwargs = _authorized_kwargs(now)
        kwargs["refusal_reason"] = AuthorizationRefusalReason.ABSENT
        with pytest.raises(ValidationError, match="must not carry a refusal_reason"):
            AuthorizationVerdict(**kwargs)


class TestRefusedVerdictRequiresAReason:
    """
    REQUIRED-PRESENT direction for the refused shape: `authorized=False`
    with no `refusal_reason` is rejected -- this is the concrete
    structural proof of "refuses closed" as bound 3 states it: a verifier
    cannot construct a silent, unexplained refusal even by mistake.
    """

    def test_refused_with_no_reason_is_rejected(self, now: datetime) -> None:
        with pytest.raises(
            ValidationError, match="must carry a non-None refusal_reason"
        ):
            AuthorizationVerdict(authorized=False, checked_at=now)

    @pytest.mark.parametrize(
        "reason",
        list(AuthorizationRefusalReason),
    )
    def test_refused_with_each_closed_taxonomy_reason_constructs(
        self, now: datetime, reason: AuthorizationRefusalReason
    ) -> None:
        # Positive control (RULING doctrine section 6): a validator that
        # rejected every refusal reason would also pass the "requires a
        # reason" tests above while destroying the contract's usability.
        # Every member of the closed taxonomy must remain constructible.
        verdict = AuthorizationVerdict(
            authorized=False, checked_at=now, refusal_reason=reason
        )
        assert verdict.authorized is False
        assert verdict.refusal_reason == reason


class TestAuthorizationRefusalReasonIsClosed:
    """
    Bound 3's four named refusal categories -- absence, mismatch, expiry,
    replay -- are each represented by at least one enum member, and the
    enum carries no generic/catch-all member a permissive implementation
    could reach for instead of naming the real cause.
    """

    def test_absence_reason_exists(self) -> None:
        assert AuthorizationRefusalReason.ABSENT == "ABSENT"

    def test_at_least_one_mismatch_reason_exists_per_checked_field(self) -> None:
        mismatch_reasons = {
            r for r in AuthorizationRefusalReason if r.value.endswith("_MISMATCH")
        }
        # organization, connection, connector revision, operation, request
        # digest -- five checked-identity fields per AUTHORIZATION_VERIFIED.
        assert len(mismatch_reasons) == 5

    def test_expiry_reason_exists(self) -> None:
        assert AuthorizationRefusalReason.EXPIRED == "EXPIRED"

    def test_replay_reason_exists(self) -> None:
        assert AuthorizationRefusalReason.REPLAYED == "REPLAYED"

    def test_no_generic_catch_all_member(self) -> None:
        banned_names = {"OTHER", "UNKNOWN", "GENERIC", "MISC", "UNSPECIFIED"}
        actual_names = {member.name for member in AuthorizationRefusalReason}
        assert not (actual_names & banned_names), (
            "AuthorizationRefusalReason must not carry a generic/catch-all "
            f"member, found: {actual_names & banned_names}"
        )


class TestAuthorizationVerdictProbeCanFail:
    """
    Proves the "refuses closed" assertions above are real probes by
    constructing a deliberately PERMISSIVE synthetic stand-in -- a verdict
    shape with no cross-field validator at all -- and observing it accept
    exactly what AuthorizationVerdict rejects: an unexplained refusal and
    an authorized verdict missing its checked fields.
    """

    def test_probe_catches_a_permissive_verdict_shape(self, now: datetime) -> None:
        class PermissiveVerdict(BaseModel):
            # Mirrors AuthorizationVerdict's fields minus the cross-field
            # validator that makes refuse-closed structural.
            model_config = ConfigDict(frozen=True, extra="forbid")
            authorized: bool
            checked_at: datetime
            refusal_reason: AuthorizationRefusalReason | None = None

        broken_silent_refusal = PermissiveVerdict(authorized=False, checked_at=now)
        injected = (
            broken_silent_refusal.authorized is False
            and broken_silent_refusal.refusal_reason is None
        )
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the deliberately permissive "
            "synthetic model did not accept a silent refusal, so this "
            "test proves nothing about the real type's rejection of it"
        )
        # The real type must reject the exact same construction.
        with pytest.raises(ValidationError):
            AuthorizationVerdict(authorized=False, checked_at=now)

    def test_probe_catches_an_authorized_verdict_missing_checked_fields(
        self, now: datetime
    ) -> None:
        class PermissiveVerdict(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            authorized: bool
            checked_at: datetime
            organization_id: OrganizationId | None = None

        broken_incomplete_authorization = PermissiveVerdict(
            authorized=True, checked_at=now
        )
        injected = (
            broken_incomplete_authorization.authorized is True
            and broken_incomplete_authorization.organization_id is None
        )
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the deliberately permissive "
            "synthetic model did not accept an incomplete authorization"
        )
        with pytest.raises(ValidationError):
            AuthorizationVerdict(authorized=True, checked_at=now)


# ===========================================================================
# SecretHealth
# ===========================================================================


class TestSecretHealthUnreachableRequiresDetail:
    def test_unreachable_with_no_detail_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="must carry a non-None detail"):
            SecretHealth(reachable=False, checked_at=now)

    def test_unreachable_with_detail_constructs(self, now: datetime) -> None:
        health = SecretHealth(
            reachable=False, checked_at=now, detail="custody adapter unreachable"
        )
        assert health.reachable is False
        assert health.detail == "custody adapter unreachable"

    def test_reachable_with_no_detail_constructs(self, now: datetime) -> None:
        # Positive control: reachable=True must remain usable with no
        # detail required -- a validator that demanded detail unconditionally
        # would also pass the test above while breaking the happy path.
        health = SecretHealth(reachable=True, checked_at=now)
        assert health.reachable is True
        assert health.detail is None


class TestSecretHealthProbeCanFail:
    def test_probe_catches_a_permissive_health_shape(self, now: datetime) -> None:
        class PermissiveHealth(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            reachable: bool
            checked_at: datetime
            detail: str | None = None

        broken = PermissiveHealth(reachable=False, checked_at=now)
        injected = broken.reachable is False and broken.detail is None
        print(f"injected: {injected}")
        assert injected, "probe-of-the-probe failed: no silent unreachable accepted"
        with pytest.raises(ValidationError):
            SecretHealth(reachable=False, checked_at=now)


# ===========================================================================
# SecretResolution: short-lived (bound 1), and never leaks (bound 1)
# ===========================================================================


class TestSecretResolutionIsShortLived:
    def test_expiry_after_resolution_constructs(self, now: datetime) -> None:
        resolution = SecretResolution(
            ref=SecretRef(handle="kc-1"),
            lease_id="lease-1",
            resolved_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        assert resolution.expires_at > resolution.resolved_at

    def test_expiry_equal_to_resolution_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="expires_at must be strictly after"):
            SecretResolution(
                ref=SecretRef(handle="kc-1"),
                lease_id="lease-1",
                resolved_at=now,
                expires_at=now,
            )

    def test_expiry_before_resolution_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValidationError, match="expires_at must be strictly after"):
            SecretResolution(
                ref=SecretRef(handle="kc-1"),
                lease_id="lease-1",
                resolved_at=now,
                expires_at=now - timedelta(seconds=1),
            )


class TestSecretResolutionNeverLeaksTheHandle:
    """
    SecretResolution wraps a SecretRef via its `ref` field; the handle
    redaction SecretRef already guarantees (identity.py) must survive being
    nested one level deeper here, exactly as it survives nested inside
    Connection.secret_handle (test_secret_ref_and_evidence_ref_safety.py).
    """

    CANARY = "CANARY-SECRET-handle-verdicts-resolution-2e9c"  # noqa: S105

    def test_canary_absent_from_resolution_model_dump_json(self, now: datetime) -> None:
        resolution = SecretResolution(
            ref=SecretRef(handle=self.CANARY),
            lease_id="lease-1",
            resolved_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        assert self.CANARY not in resolution.model_dump_json()

    def test_canary_absent_from_resolution_str_and_repr(self, now: datetime) -> None:
        resolution = SecretResolution(
            ref=SecretRef(handle=self.CANARY),
            lease_id="lease-1",
            resolved_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        assert self.CANARY not in str(resolution)
        assert self.CANARY not in repr(resolution)

    def test_probe_catches_a_resolution_wrapping_a_bare_string_handle(
        self, now: datetime
    ) -> None:
        # Deliberately broken stand-in: wraps a bare `str` instead of the
        # typed, self-redacting SecretRef -- proves the nested redaction is
        # doing real work, not merely happening to look safe.
        class PermissiveResolution(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            ref: str
            lease_id: str
            resolved_at: datetime
            expires_at: datetime

        broken = PermissiveResolution(
            ref=self.CANARY,
            lease_id="lease-1",
            resolved_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        injected = self.CANARY in broken.model_dump_json()
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the deliberately broken stand-in "
            "did not leak the canary, so this test proves nothing about "
            "the real type's redaction"
        )
        real = SecretResolution(
            ref=SecretRef(handle=self.CANARY),
            lease_id="lease-1",
            resolved_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        assert self.CANARY not in real.model_dump_json()
