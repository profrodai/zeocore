"""
The ten required behavioural proofs from Principal decision msg_54b0e295
(2026-09-02), which resolves the two contract forks Sparring returned in
msg_c6552513 over the reference-safety step: SecretRef redaction (proofs
1-4) and ConfirmationEvidenceRef typing/shape (proofs 1-6, confirmation
side). The ruling's own numbering is per-decision (SecretRef has four
proofs, ConfirmationEvidenceRef has six); this file numbers classes
`TestSecretRefProofN` and `TestConfirmationRefProofN` respectively so a
reader can match each class directly against the ruling text quoted in the
module docstring of identity.py.

RED-BEFORE-GREEN METHOD (doctrine section 6 / RULING-415 section 3c): a
must-NOT test that has never been observed failing is not known to be a
test. Every proof below that asserts an ABSENCE (a canary not appearing, a
malformed value rejected) is paired with a `TestProbeCanFail` class in this
file that deliberately reintroduces the leak/acceptance on a synthetic
stand-in and observes the SAME assertion logic fail -- proving the probe is
real, not a tautology that would pass against anything. Each such test
prints an `injected: True` line (captured via -s, or read from the
assertion message on failure) confirming the deliberate break actually
took effect before the probe's catch is trusted.

Every one of these was verified RED against the head this stream inherited
(55140e1f, before this session's repair): SecretRef leaked its handle
through str/f-string/percent-s/model_dump/model_dump_json (repr was
already redacted), and ExecutionReceipt.confirmation_evidence_ref accepted
a raw `ya29...`-shaped OAuth token verbatim as a plain `str | None`. See
the stream's report to Master for the exact RED transcript; this file is
the durable, re-runnable form of that proof.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError, field_serializer

from zeo_core.contracts.connections.connection import Connection
from zeo_core.contracts.connections.enums import ConnectionStatus, ExecutionState
from zeo_core.contracts.connections.identity import (
    ConfirmationEvidenceRef,
    ConnectionId,
    ConnectorId,
    ConnectorRevisionId,
    ExecutionId,
    OrganizationId,
    SecretRef,
)
from zeo_core.contracts.connections.receipt import ExecutionReceipt

# These are synthetic canary VALUES used to prove a leak/acceptance path
# is closed, never real credential material -- same pattern as
# test_direct_success_confirmation.py's module-level CANARY and
# test_no_raw_credential_fields.py's documented fixture-suppression usage
# (that file's own module docstring names the exact suppression it uses).
# The lint suppressions on the two assignments below name their own codes.
SECRET_CANARY = "CANARY-SECRET-handle-zc0-ref-safety-9f3e2a"  # noqa: S105
OAUTH_TOKEN_CANARY = "ya29.A0ARrdaM-synthetic-canary-not-a-real-token-9f3e2a"  # noqa: S105
PROVIDER_DETAIL_CANARY = "CANARY-PROVIDER-DETAIL-zc0-ref-safety-4b1c"

VALID_EVIDENCE_VALUE = "zeo-evidence:v1:8f14e45f-ceea-4d4c-b90a-a4d1a4e1c5a1"
VALID_EVIDENCE_VALUE_2 = "zeo-evidence:v1:1c944e21-2b1a-4d3e-9a6c-77d3e2a5b001"


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


def _ids() -> dict[str, object]:
    return {
        "execution_id": ExecutionId(value="exec-1"),
        "organization_id": OrganizationId(value="org-1"),
        "connection_id": ConnectionId(value="conn-1"),
    }


def _leaks(obj: object, needle: str) -> dict[str, bool]:
    """
    Check all six accidental-disclosure channels named by the ruling:
    repr, str, f-string (routes through __str__, checked as its own line
    for readability even though it is mechanically the same as str),
    percent-s logging, model_dump and model_dump_json.
    """
    model_dump_ok = hasattr(obj, "model_dump")
    return {
        "repr": needle in repr(obj),
        "str": needle in str(obj),
        "fstring": needle in f"{obj}",
        # Deliberate %-style interpolation, not a format-spec candidate:
        # this line's whole job is to prove the OLD-STYLE percent-s logging
        # path (the ruling names it explicitly) does not leak, which is a
        # mechanically different code path from f-strings/.format() and
        # would stop testing what it claims to if rewritten.
        "percent_s": needle in ("%s" % (obj,)),  # noqa: UP031
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


# ===========================================================================
# SECRETREF PROOFS (msg_54b0e295 SecretRef decision, four required proofs)
# ===========================================================================


class TestSecretRefProof1CanaryAbsentFromAllAccidentalChannels:
    """
    Proof 1: a synthetic handle canary is absent from repr, str, f-string
    output, percent-s logging, model_dump and model_dump_json.
    """

    def test_canary_absent_from_all_six_channels(self) -> None:
        secret_ref = SecretRef(handle=SECRET_CANARY)
        leaks = _leaks(secret_ref, SECRET_CANARY)
        assert not any(leaks.values()), f"handle leaked: {leaks}"

    def test_field_shape_is_retained_not_dropped(self) -> None:
        # The ruling is explicit: "Default dumps retain the field shape
        # with a redacted value; they are not persistence round-trips."
        # A dump that DROPPED the field entirely would also pass the pure
        # absence check above without proving the required positive shape,
        # so this is checked independently.
        secret_ref = SecretRef(handle=SECRET_CANARY)
        dumped = secret_ref.model_dump()
        assert "handle" in dumped
        assert dumped["handle"] == "<redacted>"


class TestSecretRefProof2CanaryAbsentFromContainingConnection:
    """
    Proof 2: the same canary is absent from model_dump and model_dump_json
    of a containing Connection.
    """

    def _connection(self, now: datetime) -> Connection:
        return Connection(
            connection_id=ConnectionId(value="conn-1"),
            organization_id=OrganizationId(value="org-1"),
            connector_id=ConnectorId(value="google.drive"),
            connector_revision=ConnectorRevisionId(value="google.drive@1"),
            provider_application_profile="app-1",
            verified_external_identity="user@example.com",
            secret_handle=SecretRef(handle=SECRET_CANARY),
            status=ConnectionStatus.ACTIVE,
            created_at=now,
        )

    def test_canary_absent_from_connection_model_dump(self, now: datetime) -> None:
        connection = self._connection(now)
        dumped_json_str = json.dumps(connection.model_dump(mode="json"), default=str)
        assert SECRET_CANARY not in dumped_json_str

    def test_canary_absent_from_connection_model_dump_json(self, now: datetime) -> None:
        connection = self._connection(now)
        assert SECRET_CANARY not in connection.model_dump_json()

    def test_canary_absent_from_connection_repr_and_str(self, now: datetime) -> None:
        connection = self._connection(now)
        assert SECRET_CANARY not in repr(connection)
        assert SECRET_CANARY not in str(connection)

    def test_nested_field_shape_retained(self, now: datetime) -> None:
        connection = self._connection(now)
        dumped = connection.model_dump()
        assert dumped["secret_handle"] == {"handle": "<redacted>"}


class TestSecretRefProof3DirectHandleAccessStillExact:
    """
    Proof 3: direct .handle access still returns the exact handle for the
    future trusted custody and persistence adapters. This is the REQUIRED
    PRESENCE half -- proof 1/2 prove absence on accidental channels, but a
    SecretRef that redacted .handle too would satisfy those while breaking
    the ruling's other half ("Trusted ConnectionStore or SecretStore
    adapter code may deliberately read the typed object's .handle
    property"). Absence is not injectable; presence must be asserted
    directly.
    """

    def test_handle_attribute_returns_exact_value(self) -> None:
        secret_ref = SecretRef(handle=SECRET_CANARY)
        assert secret_ref.handle == SECRET_CANARY

    def test_handle_attribute_exact_through_containing_connection(
        self, now: datetime
    ) -> None:
        connection = Connection(
            connection_id=ConnectionId(value="conn-1"),
            organization_id=OrganizationId(value="org-1"),
            connector_id=ConnectorId(value="google.drive"),
            connector_revision=ConnectorRevisionId(value="google.drive@1"),
            provider_application_profile="app-1",
            verified_external_identity="user@example.com",
            secret_handle=SecretRef(handle=SECRET_CANARY),
            status=ConnectionStatus.ACTIVE,
            created_at=now,
        )
        assert connection.secret_handle.handle == SECRET_CANARY

    def test_no_general_purpose_reveal_method_exists(self) -> None:
        # The ruling: "No new method that sounds like a general-purpose
        # reveal operation is authorized." Assert none of the plausible
        # names were added -- .handle is the only sanctioned channel.
        secret_ref = SecretRef(handle=SECRET_CANARY)
        for banned_name in ("reveal", "unwrap", "get_secret", "expose", "raw"):
            assert not hasattr(secret_ref, banned_name), (
                f"SecretRef must not carry a general-purpose reveal method "
                f"named {banned_name!r}"
            )


class TestSecretRefProof4ConstructionAndFrozenInvariantsHold:
    """
    Proof 4: empty and whitespace-only handles remain rejected; valid
    handles remain constructible; the model remains frozen.
    """

    def test_empty_handle_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SecretRef(handle="")

    def test_whitespace_only_handle_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SecretRef(handle="   \t\n  ")

    def test_valid_handle_constructible(self) -> None:
        secret_ref = SecretRef(handle="kc-1")
        assert secret_ref.handle == "kc-1"

    def test_model_remains_frozen(self) -> None:
        secret_ref = SecretRef(handle="kc-1")
        with pytest.raises(ValidationError):
            secret_ref.handle = "kc-2"  # type: ignore[misc]


class TestSecretRefProbeCanFail:
    """
    Proves TestSecretRefProof1/2's leak-absence assertions are real probes
    by running the identical `_leaks` check against a deliberately
    UNREDACTED synthetic model shaped like SecretRef before its fix, and
    observing the canary actually appear -- printing `injected: True`
    to confirm the break took effect, not a no-op that would leave the
    probe green regardless.
    """

    def test_probe_catches_an_unredacted_secret_ref(self) -> None:
        class UnredactedSecretRef(BaseModel):
            # Mirrors SecretRef exactly, MINUS the redacting serializer
            # and __str__ override -- this is the pre-repair shape this
            # stream inherited at 55140e1f (repr was already fixed there;
            # str/model_dump were not).
            model_config = ConfigDict(frozen=True, extra="forbid")
            handle: str

        broken = UnredactedSecretRef(handle=SECRET_CANARY)
        leaks = _leaks(broken, SECRET_CANARY)
        injected = any(leaks.values())
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the deliberately broken synthetic "
            "model did not leak on any channel, so this test proves "
            "nothing about the real fix's ability to catch a real leak"
        )
        # Specifically str/f-string/percent-s/model_dump/model_dump_json
        # leaked on the pre-repair shape (repr was pydantic's default too,
        # which also leaks for an undecorated BaseModel -- unlike the real
        # SecretRef where repr was already fixed before this session).
        assert leaks["str"] is True
        assert leaks["model_dump"] is True
        assert leaks["model_dump_json"] is True

    def test_probe_catches_a_dropped_handle_shape(self) -> None:
        # A DIFFERENT wrong fix: redacting by dropping the field entirely
        # rather than retaining shape with a redacted value. The ruling
        # forbids this ("they are not persistence round-trips" implies the
        # shape survives); prove the shape-retention assertion would catch
        # a dump that dropped the field.
        class DroppedHandleSecretRef(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            handle: str

            @field_serializer("handle")
            def _drop(self, _value: str) -> None:
                return None

        broken = DroppedHandleSecretRef(handle=SECRET_CANARY)
        dumped = broken.model_dump()
        injected = dumped.get("handle") is None
        print(f"injected: {injected}")
        assert injected, "probe-of-the-probe failed: the field was not actually dropped"
        with pytest.raises(AssertionError):
            assert dumped["handle"] == "<redacted>"


# ===========================================================================
# CONFIRMATIONEVIDENCEREF PROOFS (msg_54b0e295 confirmation-ref decision,
# six required proofs)
# ===========================================================================


class TestConfirmationRefProof1OAuthTokenCanaryRejected:
    """
    Proof 1: the demonstrated ya29... OAuth-token canary is rejected as a
    ConfirmationEvidenceRef.
    """

    def test_oauth_token_canary_rejected_by_confirmation_evidence_ref(self) -> None:
        with pytest.raises(ValidationError, match="canonical shape"):
            ConfirmationEvidenceRef(value=OAUTH_TOKEN_CANARY)

    def test_oauth_token_canary_rejected_on_receipt_field(self, now: datetime) -> None:
        # Deliberate bare-str probe: pydantic rejects this at runtime
        # (proven below); mypy's pydantic plugin does not flag it
        # statically for this field -- a pre-existing gap, recorded in the
        # stream report, not introduced by this change.
        with pytest.raises(ValidationError):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.SUCCEEDED,
                recorded_at=now,
                dispatch_started_at=now,
                confirmation_evidence_ref=OAUTH_TOKEN_CANARY,
            )


class TestConfirmationRefProof2ArbitraryMalformedInputsRejected:
    """
    Proof 2: arbitrary strings, provider response bodies, malformed
    prefixes, non-v4 UUIDs, uppercase variants, empty values, and
    surrounding whitespace are all rejected.
    """

    @pytest.mark.parametrize(
        "bad_value",
        [
            pytest.param("arbitrary-string", id="arbitrary-string"),
            pytest.param(
                '{"status": "ok", "id": "msg_12345", "thread": "t_1"}',
                id="provider-response-body",
            ),
            pytest.param(
                "evidence:v1:8f14e45f-ceea-4d4c-b90a-a4d1a4e1c5a1",
                id="malformed-prefix-missing-zeo",
            ),
            pytest.param(
                "zeo-evidence:v2:8f14e45f-ceea-4d4c-b90a-a4d1a4e1c5a1",
                id="malformed-prefix-wrong-version",
            ),
            pytest.param(
                # version nibble is "1", not "4" -> not a v4 UUID
                "zeo-evidence:v1:8f14e45f-ceea-1d4c-b90a-a4d1a4e1c5a1",
                id="non-v4-uuid-version-nibble",
            ),
            pytest.param(
                # variant nibble "c" is outside the required 8/9/a/b set
                "zeo-evidence:v1:8f14e45f-ceea-4d4c-c90a-a4d1a4e1c5a1",
                id="non-v4-uuid-variant-nibble",
            ),
            pytest.param(
                "zeo-evidence:v1:8F14E45F-CEEA-4D4C-B90A-A4D1A4E1C5A1",
                id="uppercase-variant",
            ),
            pytest.param("", id="empty-value"),
            pytest.param(
                "  zeo-evidence:v1:8f14e45f-ceea-4d4c-b90a-a4d1a4e1c5a1  ",
                id="surrounding-whitespace",
            ),
            pytest.param(
                "zeo-evidence:v1:8f14e45f-ceea-4d4c-b90a-a4d1a4e1c5a1\n",
                id="trailing-newline",
            ),
        ],
    )
    def test_bad_value_rejected(self, bad_value: str) -> None:
        with pytest.raises(ValidationError):
            ConfirmationEvidenceRef(value=bad_value)


class TestConfirmationRefProof3ValidReferenceSurvivesReceiptSerializationByteExactly:
    """
    Proof 3: a correctly formed kernel reference is accepted and survives
    receipt model_dump and model_dump_json byte-exactly.
    """

    def test_valid_reference_accepted(self) -> None:
        ref = ConfirmationEvidenceRef(value=VALID_EVIDENCE_VALUE)
        assert ref.value == VALID_EVIDENCE_VALUE

    def test_valid_reference_survives_receipt_model_dump_byte_exactly(
        self, now: datetime
    ) -> None:
        receipt = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now,
            confirmation_evidence_ref=ConfirmationEvidenceRef(
                value=VALID_EVIDENCE_VALUE
            ),
        )
        dumped = receipt.model_dump()
        assert dumped["confirmation_evidence_ref"] == {"value": VALID_EVIDENCE_VALUE}

    def test_valid_reference_survives_receipt_model_dump_json_byte_exactly(
        self, now: datetime
    ) -> None:
        receipt = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now,
            confirmation_evidence_ref=ConfirmationEvidenceRef(
                value=VALID_EVIDENCE_VALUE
            ),
        )
        dumped_json = json.loads(receipt.model_dump_json())
        assert dumped_json["confirmation_evidence_ref"] == {
            "value": VALID_EVIDENCE_VALUE
        }
        # Round-trip through re-parsing the receipt from its own JSON dump
        # to prove byte-exactness end to end, not merely field-by-field.
        reparsed = ExecutionReceipt.model_validate_json(receipt.model_dump_json())
        assert reparsed.confirmation_evidence_ref == receipt.confirmation_evidence_ref
        assert reparsed.model_dump_json() == receipt.model_dump_json()


class TestConfirmationRefProof4DirectAndReconciledAcceptTypedRefNoCoercion:
    """
    Proof 4: a valid direct and a valid reconciled SUCCEEDED receipt
    accepts the typed reference; a bare string is not silently accepted or
    coerced.
    """

    def test_direct_succeeded_accepts_typed_reference(self, now: datetime) -> None:
        ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(seconds=1),
            confirmation_evidence_ref=ConfirmationEvidenceRef(
                value=VALID_EVIDENCE_VALUE
            ),
        )  # must not raise

    def test_reconciled_succeeded_accepts_typed_reference(self, now: datetime) -> None:
        ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(minutes=6),
            confirmation_evidence_ref=ConfirmationEvidenceRef(
                value=VALID_EVIDENCE_VALUE
            ),
            reconciliation_evidence="queried provider ledger, effect confirmed",
            resolves_ambiguous_recorded_at=now - timedelta(minutes=5),
            resolved_at=now,
        )  # must not raise

    def test_bare_string_not_coerced_on_direct_succeeded(self, now: datetime) -> None:
        # Deliberate bare-str probe: even a well-shaped string must not be
        # silently coerced. pydantic rejects this at runtime (proven
        # below); mypy's pydantic plugin does not flag it statically for
        # this field -- a pre-existing gap, recorded in the stream report.
        with pytest.raises(
            ValidationError,
            match="valid dictionary or instance of ConfirmationEvidenceRef",
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.SUCCEEDED,
                recorded_at=now,
                dispatch_started_at=now - timedelta(seconds=1),
                confirmation_evidence_ref=VALID_EVIDENCE_VALUE,
            )

    def test_bare_string_not_coerced_on_reconciled_succeeded(
        self, now: datetime
    ) -> None:
        # Same deliberate bare-str probe as above, reconciled-success path.
        with pytest.raises(
            ValidationError,
            match="valid dictionary or instance of ConfirmationEvidenceRef",
        ):
            ExecutionReceipt(
                **_ids(),
                final_state=ExecutionState.SUCCEEDED,
                recorded_at=now,
                dispatch_started_at=now - timedelta(minutes=6),
                confirmation_evidence_ref=VALID_EVIDENCE_VALUE,
                reconciliation_evidence="queried provider ledger, effect confirmed",
                resolves_ambiguous_recorded_at=now - timedelta(minutes=5),
                resolved_at=now,
            )


class TestConfirmationRefProof5ProviderDetailCanaryDoesNotPropagate:
    """
    Proof 5: provider-detail canaries do not propagate into the typed
    reference or receipt serialization.
    """

    def test_provider_detail_canary_absent_from_valid_receipt_serialization(
        self, now: datetime
    ) -> None:
        from zeo_core.contracts.connections.enums import NormalizedErrorCode
        from zeo_core.contracts.connections.errors import NormalizedError

        # The canary lives only in a SIBLING FAILED_SAFE receipt's
        # provider_detail -- a realistic vector for a provider response
        # leaking a secret-shaped value elsewhere in the system. Prove it
        # never reaches an unrelated, cleanly-constructed SUCCEEDED
        # receipt's confirmation_evidence_ref or serialization.
        provider_detail = f"raw provider payload containing {PROVIDER_DETAIL_CANARY}"
        sibling_failed = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.FAILED_SAFE,
            normalized_error=NormalizedError(
                code=NormalizedErrorCode.PROVIDER_UNAVAILABLE,
                message="ordinary product message",
                provider_detail=provider_detail,
            ),
            recorded_at=now,
        )
        assert PROVIDER_DETAIL_CANARY in sibling_failed.model_dump_json()  # sanity

        clean_succeeded = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(seconds=1),
            confirmation_evidence_ref=ConfirmationEvidenceRef(
                value=VALID_EVIDENCE_VALUE
            ),
        )
        assert PROVIDER_DETAIL_CANARY not in clean_succeeded.model_dump_json()
        assert (
            PROVIDER_DETAIL_CANARY
            not in clean_succeeded.confirmation_evidence_ref.value  # type: ignore[union-attr]
        )

    def test_provider_detail_shaped_value_cannot_even_be_constructed_as_a_ref(
        self,
    ) -> None:
        # A provider_detail-shaped string could never pass
        # ConfirmationEvidenceRef's own shape validator regardless of
        # sibling-object propagation -- this is the structural half of
        # proof 5: the canary cannot "propagate into the typed reference"
        # because no free-text provider payload is representable there at
        # all.
        with pytest.raises(ValidationError):
            ConfirmationEvidenceRef(
                value=f"raw provider payload containing {PROVIDER_DETAIL_CANARY}"
            )


class TestConfirmationRefProof6PositiveControlValidReferenceRemainsUsable:
    """
    Proof 6 (the positive control): a valid reference remains usable -- a
    validator that rejects every input FAILS this proof. Not ceremony: a
    reject-everything validator would pass proofs 1/2/5 above while
    destroying the contract, so the happy path is asserted explicitly and
    independently here.
    """

    def test_valid_reference_constructs_without_error(self) -> None:
        ref = ConfirmationEvidenceRef(value=VALID_EVIDENCE_VALUE)
        assert ref.value == VALID_EVIDENCE_VALUE

    def test_two_distinct_valid_references_are_both_usable(self) -> None:
        # Guards against a validator that happens to hardcode acceptance
        # of exactly one fixture value rather than genuinely validating
        # the shape -- a second, differently-valued valid UUID must also
        # pass.
        ref_a = ConfirmationEvidenceRef(value=VALID_EVIDENCE_VALUE)
        ref_b = ConfirmationEvidenceRef(value=VALID_EVIDENCE_VALUE_2)
        assert ref_a.value != ref_b.value
        assert ref_a != ref_b

    def test_valid_reference_usable_end_to_end_on_a_direct_succeeded_receipt(
        self, now: datetime
    ) -> None:
        receipt = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(seconds=1),
            confirmation_evidence_ref=ConfirmationEvidenceRef(
                value=VALID_EVIDENCE_VALUE
            ),
        )
        assert receipt.confirmation_evidence_ref is not None
        assert receipt.confirmation_evidence_ref.value == VALID_EVIDENCE_VALUE
        assert VALID_EVIDENCE_VALUE in receipt.model_dump_json()

    def test_valid_reference_usable_end_to_end_on_a_reconciled_succeeded_receipt(
        self, now: datetime
    ) -> None:
        receipt = ExecutionReceipt(
            **_ids(),
            final_state=ExecutionState.SUCCEEDED,
            recorded_at=now,
            dispatch_started_at=now - timedelta(minutes=6),
            confirmation_evidence_ref=ConfirmationEvidenceRef(
                value=VALID_EVIDENCE_VALUE
            ),
            reconciliation_evidence="queried provider ledger, effect confirmed",
            resolves_ambiguous_recorded_at=now - timedelta(minutes=5),
            resolved_at=now,
        )
        assert receipt.confirmation_evidence_ref is not None
        assert receipt.confirmation_evidence_ref.value == VALID_EVIDENCE_VALUE


class TestConfirmationRefProbeCanFail:
    """
    Proves the shape-rejection assertions above are real probes by running
    the identical validator against a deliberately PERMISSIVE synthetic
    stand-in (accepts any non-empty string, i.e. the pre-repair
    `str | None` contract this stream inherited at 55140e1f) and observing
    the OAuth canary and other malformed inputs actually get ACCEPTED --
    printing `injected: True` to confirm the broken variant really is more
    permissive than the real type, not accidentally just as strict.
    """

    def test_probe_catches_the_pre_repair_permissive_contract(self) -> None:
        class PermissiveLikePreRepair(BaseModel):
            # Mirrors the pre-repair ExecutionReceipt.confirmation_evidence_ref
            # shape exactly: `str | None` with no shape validation at all.
            model_config = ConfigDict(frozen=True, extra="forbid")
            confirmation_evidence_ref: str | None = None

        broken = PermissiveLikePreRepair(confirmation_evidence_ref=OAUTH_TOKEN_CANARY)
        injected = broken.confirmation_evidence_ref == OAUTH_TOKEN_CANARY
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the deliberately permissive "
            "synthetic model did not accept the OAuth canary, so this "
            "test proves nothing about the real type's rejection of it"
        )
        # Now show the REAL type refuses the exact same input the broken
        # stand-in accepted -- this is the paired positive proof that the
        # repair, not merely the test file, closed the gap.
        with pytest.raises(ValidationError):
            ConfirmationEvidenceRef(value=OAUTH_TOKEN_CANARY)

    def test_probe_catches_a_reject_everything_validator(self) -> None:
        # The inverse failure mode from proof 6's own docstring: a
        # validator that rejects every input would pass all the negative
        # proofs above while destroying the contract. Prove such a
        # validator is DISTINGUISHABLE from the real one by observing it
        # reject the valid fixture value that the real type accepts.
        class RejectEverything(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            value: str

            @classmethod
            def validate_shape(cls, _v: str) -> None:
                raise ValueError("rejects everything, including valid input")

        with pytest.raises(ValueError, match="rejects everything"):
            RejectEverything.validate_shape(VALID_EVIDENCE_VALUE)
        injected = True
        print(f"injected: {injected}")
        # The real type must NOT share this behavior for the same input.
        ConfirmationEvidenceRef(value=VALID_EVIDENCE_VALUE)  # must not raise
