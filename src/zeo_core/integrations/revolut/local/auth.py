"""Revolut Business client key, certificate, assertion and fixed token endpoint.

Needs the ``revolut`` extra (``cryptography``). The token endpoint reports
refusal, unavailability and an unknown outcome as values: the three are not
interchangeable, and only the caller knows what to do with each.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Literal, Protocol
from urllib.parse import urlencode

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from ..models import RevolutEnvironment

_TOKEN_URLS = {
    RevolutEnvironment.PRODUCTION: "https://b2b.revolut.com/api/1.0/auth/token",
    RevolutEnvironment.SANDBOX: "https://sandbox-b2b.revolut.com/api/1.0/auth/token",
}
_CONSENT_URLS = {
    RevolutEnvironment.PRODUCTION: "https://business.revolut.com/app-confirm",
    RevolutEnvironment.SANDBOX: "https://sandbox-business.revolut.com/app-confirm",
}
_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
_ASSERTION_AUDIENCE = "https://revolut.com"
_ASSERTION_LIFETIME = timedelta(seconds=120)
_CERTIFICATE_LIFETIME = timedelta(days=5 * 365)
_MAX_TOKEN_RESPONSE_BYTES = 64 * 1024
# Per-phase limits plus a total read deadline keep one request well inside the
# window after which its outcome is declared unknown.
_PHASE_TIMEOUT_SECONDS = 10.0
_RESPONSE_DEADLINE_SECONDS = 30.0


class TokenGrant(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    access_token: SecretStr = Field(min_length=1)
    # Revolut returns a refresh token on exchange and may omit it on refresh.
    refresh_token: SecretStr | None = None
    expires_in: int = Field(gt=0, le=24 * 60 * 60)


class TokenFailure(BaseModel):
    """Why no grant was obtained. The three kinds are not interchangeable.

    ``refused``      the provider answered and rejected the grant itself.
    ``unavailable``  the provider did not process it: nothing was sent, or it
                     answered with a status that precedes grant processing.
    ``unknown``      the request may have been processed but the answer was
                     lost or unusable. A refresh may have invalidated the
                     current access token, so this must never be retried as if
                     nothing happened.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["refused", "unavailable", "unknown"]


class RevolutTokenGateway(Protocol):
    def exchange(
        self,
        *,
        environment: RevolutEnvironment,
        client_id: str,
        issuer: str,
        private_key_pem: bytes,
        code: SecretStr,
        now: datetime,
    ) -> TokenGrant | TokenFailure: ...

    def refresh(
        self,
        *,
        environment: RevolutEnvironment,
        client_id: str,
        issuer: str,
        private_key_pem: bytes,
        refresh_token: SecretStr,
        now: datetime,
    ) -> TokenGrant | TokenFailure: ...


def consent_url(
    *, environment: RevolutEnvironment, client_id: str, redirect_uri: str, state: str
) -> str:
    """Read-only consent. The host is fixed per environment."""

    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "READ",
            "state": state,
        }
    )
    return f"{_CONSENT_URLS[RevolutEnvironment(environment)]}?{query}"


def generate_client_key() -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _private_key(private_key_pem: bytes) -> rsa.RSAPrivateKey:
    key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("Revolut client key must be RSA")
    return key


def public_certificate(
    private_key_pem: bytes, *, common_name: str, now: datetime
) -> str:
    """Self-signed certificate the member registers in Revolut Business."""

    key = _private_key(private_key_pem)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + _CERTIFICATE_LIFETIME)
        .sign(key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.PEM).decode("ascii")


def _segment(value: bytes) -> bytes:
    return base64.urlsafe_b64encode(value).rstrip(b"=")


def client_assertion(
    private_key_pem: bytes, *, client_id: str, issuer: str, now: datetime
) -> str:
    """RS256 JWT: ``iss`` is the registered redirect domain, ``sub`` the client."""

    claims = {
        "iss": issuer,
        "sub": client_id,
        "aud": _ASSERTION_AUDIENCE,
        "exp": int((now + _ASSERTION_LIFETIME).timestamp()),
    }
    signing_input = b".".join(
        _segment(json.dumps(part, separators=(",", ":"), sort_keys=True).encode())
        for part in ({"alg": "RS256", "typ": "JWT"}, claims)
    )
    signature = _private_key(private_key_pem).sign(
        signing_input, padding.PKCS1v15(), hashes.SHA256()
    )
    return (signing_input + b"." + _segment(signature)).decode("ascii")


class HttpRevolutTokenGateway:
    """A caller may inject an HTTP transport, never a token endpoint URL."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._monotonic = monotonic
        self._http = httpx.Client(
            transport=transport,
            timeout=_PHASE_TIMEOUT_SECONDS,
            trust_env=False,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._http.close()

    def exchange(
        self,
        *,
        environment: RevolutEnvironment,
        client_id: str,
        issuer: str,
        private_key_pem: bytes,
        code: SecretStr,
        now: datetime,
    ) -> TokenGrant | TokenFailure:
        return self._grant(
            environment,
            {"grant_type": "authorization_code", "code": code.get_secret_value()},
            client_assertion(
                private_key_pem, client_id=client_id, issuer=issuer, now=now
            ),
        )

    def refresh(
        self,
        *,
        environment: RevolutEnvironment,
        client_id: str,
        issuer: str,
        private_key_pem: bytes,
        refresh_token: SecretStr,
        now: datetime,
    ) -> TokenGrant | TokenFailure:
        return self._grant(
            environment,
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token.get_secret_value(),
            },
            client_assertion(
                private_key_pem, client_id=client_id, issuer=issuer, now=now
            ),
        )

    def _grant(
        self, environment: RevolutEnvironment, form: dict[str, str], assertion: str
    ) -> TokenGrant | TokenFailure:
        content = bytearray()
        started = self._monotonic()
        try:
            with self._http.stream(
                "POST",
                _TOKEN_URLS[RevolutEnvironment(environment)],
                data={
                    **form,
                    "client_assertion_type": _ASSERTION_TYPE,
                    "client_assertion": assertion,
                },
                headers={"Accept": "application/json"},
            ) as response:
                status = response.status_code
                # A refusal body can quote the grant; it is never read.
                if status == 200:
                    for chunk in response.iter_bytes():
                        content += chunk
                        if (
                            len(content) > _MAX_TOKEN_RESPONSE_BYTES
                            or self._monotonic() - started > _RESPONSE_DEADLINE_SECONDS
                        ):
                            # The grant was issued; only its delivery failed.
                            return TokenFailure(kind="unknown")
        except httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout:
            return TokenFailure(kind="unavailable")  # nothing reached the provider
        except httpx.HTTPError:
            return TokenFailure(kind="unknown")
        if status in {400, 401}:
            return TokenFailure(kind="refused")
        if status >= 500:
            return TokenFailure(kind="unknown")  # may have failed after processing
        if status != 200:
            return TokenFailure(kind="unavailable")
        try:
            return TokenGrant.model_validate_json(bytes(content))
        except ValidationError:
            return TokenFailure(kind="unknown")


__all__ = [
    "HttpRevolutTokenGateway",
    "RevolutTokenGateway",
    "TokenFailure",
    "TokenGrant",
    "client_assertion",
    "consent_url",
    "generate_client_key",
    "public_certificate",
]
