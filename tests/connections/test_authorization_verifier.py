"""Behavioral proofs for exact, fail-closed effect authorization checks."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest

from zeo_core.connections import ExactAuthorizationVerifier
from zeo_core.contracts.connections import (
    AuthorizationRefusalReason,
    AuthorizationVerdict,
    ConnectionId,
    ConnectorRevisionId,
    EffectAuthorization,
    EffectAuthorizationVerifier,
    OrganizationId,
)


class NonceLookup:
    def __init__(self, *nonces: str) -> None:
        self.nonces = set(nonces)

    def has_authorization_nonce(
        self, *, organization_id: OrganizationId, nonce: str
    ) -> bool:
        del organization_id
        return nonce in self.nonces


class SignatureVerifier:
    def __init__(self, *, accepted: bool = True) -> None:
        self.accepted = accepted
        self.calls = 0

    def verify_signature(self, authorization: EffectAuthorization) -> bool:
        del authorization
        self.calls += 1
        return self.accepted


def exact_verifier(
    *, signature_verifier: SignatureVerifier | None = None
) -> ExactAuthorizationVerifier:
    return ExactAuthorizationVerifier(
        signature_verifier=signature_verifier or SignatureVerifier(),
        expected_audience="zeocore",
        trusted_issuers=frozenset({"zeo-go"}),
    )


def verify(
    authorization: EffectAuthorization | None,
    now: datetime,
    *,
    organization_id: OrganizationId | None = None,
    connection_id: ConnectionId | None = None,
    connector_revision: ConnectorRevisionId | None = None,
    operation_id: str | None = None,
    request_digest: str | None = None,
    seen_nonces: object | None = None,
) -> AuthorizationVerdict:
    source = authorization
    return exact_verifier().verify(
        authorization=source,
        organization_id=organization_id
        or (source.organization_id if source else OrganizationId(value="org-1")),
        connection_id=connection_id
        or (source.connection_id if source else ConnectionId(value="conn-1")),
        connector_revision=connector_revision
        or (
            source.connector_revision
            if source
            else ConnectorRevisionId(value="revision-1")
        ),
        operation_id=operation_id
        or (str(source.operation_id) if source else "operation-1"),
        request_digest=request_digest
        or (source.argument_digest if source else "sha256:none"),
        now=now,
        seen_nonces=seen_nonces if seen_nonces is not None else NonceLookup(),
    )


def test_verifier_satisfies_protocol() -> None:
    assert isinstance(exact_verifier(), EffectAuthorizationVerifier)


def test_exact_authorization_is_accepted(
    effect_authorization: EffectAuthorization, now: datetime
) -> None:
    verdict = verify(effect_authorization, now)

    assert verdict.authorized is True
    assert verdict.authorization_id == effect_authorization.authorization_id
    assert verdict.request_digest == effect_authorization.argument_digest


@pytest.mark.parametrize(
    "field,value,reason",
    [
        (
            "organization_id",
            OrganizationId(value="other"),
            AuthorizationRefusalReason.ORGANIZATION_MISMATCH,
        ),
        (
            "connection_id",
            ConnectionId(value="other"),
            AuthorizationRefusalReason.CONNECTION_MISMATCH,
        ),
        (
            "connector_revision",
            ConnectorRevisionId(value="other"),
            AuthorizationRefusalReason.CONNECTOR_REVISION_MISMATCH,
        ),
        ("operation_id", "other", AuthorizationRefusalReason.OPERATION_MISMATCH),
        (
            "request_digest",
            "sha256:other",
            AuthorizationRefusalReason.REQUEST_DIGEST_MISMATCH,
        ),
    ],
)
def test_each_mismatch_refuses_closed(
    effect_authorization: EffectAuthorization,
    now: datetime,
    field: str,
    value: Any,  # noqa: ANN401 -- heterogeneous parametrized keyword values
    reason: AuthorizationRefusalReason,
) -> None:
    kwargs: dict[str, Any] = {field: value}
    verdict = verify(effect_authorization, now, **kwargs)

    assert verdict.authorized is False
    assert verdict.refusal_reason is reason


def test_absence_expiry_and_replay_each_refuse(
    effect_authorization: EffectAuthorization, now: datetime
) -> None:
    absent = verify(None, now)
    expired = verify(effect_authorization, now + timedelta(hours=1))
    replayed = verify(
        effect_authorization,
        now,
        seen_nonces=NonceLookup(effect_authorization.nonce),
    )

    assert absent.refusal_reason is AuthorizationRefusalReason.ABSENT
    assert expired.refusal_reason is AuthorizationRefusalReason.EXPIRED
    assert replayed.refusal_reason is AuthorizationRefusalReason.REPLAYED


def test_audience_issuer_and_signature_each_refuse_closed(
    effect_authorization: EffectAuthorization, now: datetime
) -> None:
    wrong_audience = ExactAuthorizationVerifier(
        signature_verifier=SignatureVerifier(),
        expected_audience="other-runtime",
        trusted_issuers=frozenset({effect_authorization.issuer}),
    ).verify(
        authorization=effect_authorization,
        organization_id=effect_authorization.organization_id,
        connection_id=effect_authorization.connection_id,
        connector_revision=effect_authorization.connector_revision,
        operation_id=str(effect_authorization.operation_id),
        request_digest=effect_authorization.argument_digest,
        now=now,
        seen_nonces=NonceLookup(),
    )
    untrusted_issuer = ExactAuthorizationVerifier(
        signature_verifier=SignatureVerifier(),
        expected_audience=effect_authorization.audience,
        trusted_issuers=frozenset({"other-issuer"}),
    ).verify(
        authorization=effect_authorization,
        organization_id=effect_authorization.organization_id,
        connection_id=effect_authorization.connection_id,
        connector_revision=effect_authorization.connector_revision,
        operation_id=str(effect_authorization.operation_id),
        request_digest=effect_authorization.argument_digest,
        now=now,
        seen_nonces=NonceLookup(),
    )
    bad_signature = SignatureVerifier(accepted=False)
    unverifiable = ExactAuthorizationVerifier(
        signature_verifier=bad_signature,
        expected_audience=effect_authorization.audience,
        trusted_issuers=frozenset({effect_authorization.issuer}),
    ).verify(
        authorization=effect_authorization,
        organization_id=effect_authorization.organization_id,
        connection_id=effect_authorization.connection_id,
        connector_revision=effect_authorization.connector_revision,
        operation_id=str(effect_authorization.operation_id),
        request_digest=effect_authorization.argument_digest,
        now=now,
        seen_nonces=NonceLookup(),
    )

    assert wrong_audience.refusal_reason is AuthorizationRefusalReason.AUDIENCE_MISMATCH
    assert (
        untrusted_issuer.refusal_reason is AuthorizationRefusalReason.ISSUER_UNTRUSTED
    )
    assert (
        unverifiable.refusal_reason is AuthorizationRefusalReason.SIGNATURE_UNVERIFIABLE
    )
    assert bad_signature.calls == 1


def test_verifier_configuration_has_no_permissive_default() -> None:
    with pytest.raises(TypeError):
        ExactAuthorizationVerifier()  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="expected_audience"):
        ExactAuthorizationVerifier(
            signature_verifier=SignatureVerifier(),
            expected_audience="",
            trusted_issuers=frozenset({"zeo-go"}),
        )
    with pytest.raises(ValueError, match="trusted_issuers"):
        ExactAuthorizationVerifier(
            signature_verifier=SignatureVerifier(),
            expected_audience="zeocore",
            trusted_issuers=frozenset(),
        )


def test_plain_nonce_container_is_supported(
    effect_authorization: EffectAuthorization, now: datetime
) -> None:
    verdict = verify(
        effect_authorization,
        now,
        seen_nonces={effect_authorization.nonce},
    )
    assert verdict.refusal_reason is AuthorizationRefusalReason.REPLAYED


def test_invalid_clock_or_nonce_lookup_refuses_to_grade(
    effect_authorization: EffectAuthorization, now: datetime
) -> None:
    with pytest.raises(TypeError, match="now must be"):
        exact_verifier().verify(
            authorization=effect_authorization,
            organization_id=effect_authorization.organization_id,
            connection_id=effect_authorization.connection_id,
            connector_revision=effect_authorization.connector_revision,
            operation_id=str(effect_authorization.operation_id),
            request_digest=effect_authorization.argument_digest,
            now="not-a-clock",
            seen_nonces=set(),
        )
    with pytest.raises(TypeError, match="seen_nonces"):
        verify(effect_authorization, now, seen_nonces=object())
