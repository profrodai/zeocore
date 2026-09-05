"""Fail-closed mechanical verification of effect authorization bindings."""

from __future__ import annotations

from collections.abc import Container
from datetime import datetime
from typing import Protocol

from zeo_core.contracts.connections import (
    AuthorizationRefusalReason,
    AuthorizationVerdict,
    ConnectionId,
    ConnectorRevisionId,
    EffectAuthorization,
    OperationId,
    OrganizationId,
)


class AuthorizationNonceLookup(Protocol):
    """Organization-scoped replay lookup implemented by durable stores."""

    def has_authorization_nonce(
        self, *, organization_id: OrganizationId, nonce: str
    ) -> bool: ...


class AuthorizationSignatureVerifier(Protocol):
    """Cryptographically verify an authorization with configured trust roots."""

    def verify_signature(self, authorization: EffectAuthorization) -> bool: ...


class ExactAuthorizationVerifier:
    """Verify exact mechanical fields and delegated cryptographic trust."""

    def __init__(
        self,
        *,
        signature_verifier: AuthorizationSignatureVerifier,
        expected_audience: str,
        trusted_issuers: frozenset[str],
    ) -> None:
        if not expected_audience:
            raise ValueError("expected_audience must not be empty")
        if not trusted_issuers or any(not issuer for issuer in trusted_issuers):
            raise ValueError("trusted_issuers must contain non-empty issuers")
        self._signature_verifier = signature_verifier
        self._expected_audience = expected_audience
        self._trusted_issuers = trusted_issuers

    def verify(
        self,
        *,
        authorization: EffectAuthorization | None,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        connector_revision: ConnectorRevisionId,
        operation_id: str,
        request_digest: str,
        now: object,
        seen_nonces: object,
    ) -> AuthorizationVerdict:
        if not isinstance(now, datetime):
            raise TypeError("now must be a datetime")
        if authorization is None:
            return self._refused(now, AuthorizationRefusalReason.ABSENT)
        checks = (
            (
                authorization.organization_id == organization_id,
                AuthorizationRefusalReason.ORGANIZATION_MISMATCH,
            ),
            (
                authorization.connection_id == connection_id,
                AuthorizationRefusalReason.CONNECTION_MISMATCH,
            ),
            (
                authorization.connector_revision == connector_revision,
                AuthorizationRefusalReason.CONNECTOR_REVISION_MISMATCH,
            ),
            (
                authorization.operation_id == OperationId(value=operation_id),
                AuthorizationRefusalReason.OPERATION_MISMATCH,
            ),
            (
                authorization.argument_digest == request_digest,
                AuthorizationRefusalReason.REQUEST_DIGEST_MISMATCH,
            ),
            (
                authorization.audience == self._expected_audience,
                AuthorizationRefusalReason.AUDIENCE_MISMATCH,
            ),
            (
                authorization.issuer in self._trusted_issuers,
                AuthorizationRefusalReason.ISSUER_UNTRUSTED,
            ),
            (
                not authorization.is_expired(at=now),
                AuthorizationRefusalReason.EXPIRED,
            ),
        )
        for accepted, reason in checks:
            if not accepted:
                return self._refused(now, reason)
        if not self._signature_verifier.verify_signature(authorization):
            return self._refused(now, AuthorizationRefusalReason.SIGNATURE_UNVERIFIABLE)
        if self._nonce_seen(seen_nonces, organization_id, authorization.nonce):
            return self._refused(now, AuthorizationRefusalReason.REPLAYED)
        return AuthorizationVerdict(
            authorized=True,
            organization_id=organization_id,
            connection_id=connection_id,
            connector_revision=connector_revision,
            operation_id=authorization.operation_id,
            authorization_id=authorization.authorization_id,
            request_digest=request_digest,
            checked_at=now,
        )

    @staticmethod
    def _nonce_seen(
        seen_nonces: object, organization_id: OrganizationId, nonce: str
    ) -> bool:
        method = getattr(seen_nonces, "has_authorization_nonce", None)
        if callable(method):
            result = method(organization_id=organization_id, nonce=nonce)
            if not isinstance(result, bool):
                raise TypeError("nonce lookup must return bool")
            return result
        if isinstance(seen_nonces, Container):
            return nonce in seen_nonces
        raise TypeError("seen_nonces must be a nonce lookup or container")

    @staticmethod
    def _refused(
        now: datetime, reason: AuthorizationRefusalReason
    ) -> AuthorizationVerdict:
        return AuthorizationVerdict(
            authorized=False,
            checked_at=now,
            refusal_reason=reason,
        )
