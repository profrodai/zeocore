"""Client key, certificate, assertion and the fixed token endpoint. Offline."""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import SecretStr

from zeo_core.integrations.revolut import RevolutEnvironment
from zeo_core.integrations.revolut.local.auth import (
    HttpRevolutTokenGateway,
    TokenFailure,
    TokenGrant,
    client_assertion,
    generate_client_key,
    public_certificate,
)

NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)
ISSUER = "example.test"
CLIENT_ID = "client-id-from-revolut"
CANARY = "token-canary-5d1e"
KEY = generate_client_key()


def _decode(segment: str) -> dict[str, object]:
    padded = segment + "=" * (-len(segment) % 4)
    decoded: dict[str, object] = json.loads(base64.urlsafe_b64decode(padded))
    return decoded


def test_certificate_and_assertion_verify_against_each_other() -> None:
    certificate = x509.load_pem_x509_certificate(
        public_certificate(KEY, common_name=ISSUER, now=NOW).encode()
    )
    assert certificate.subject == certificate.issuer
    assert certificate.not_valid_after_utc > NOW + timedelta(days=365)
    assertion = client_assertion(KEY, client_id=CLIENT_ID, issuer=ISSUER, now=NOW)
    header, claims, signature = assertion.split(".")
    assert _decode(header) == {"alg": "RS256", "typ": "JWT"}
    assert _decode(claims) == {
        "iss": ISSUER,
        "sub": CLIENT_ID,
        "aud": "https://revolut.com",
        "exp": int((NOW + timedelta(seconds=120)).timestamp()),
    }
    public_key = certificate.public_key()
    assert isinstance(public_key, rsa.RSAPublicKey)
    public_key.verify(
        base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)),
        f"{header}.{claims}".encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    assert b"PRIVATE" not in certificate.public_bytes(serialization.Encoding.PEM)
    with pytest.raises(ValueError):
        client_assertion(b"not a key", client_id=CLIENT_ID, issuer=ISSUER, now=NOW)


def test_http_gateway_uses_fixed_origins_and_reports_failures_as_values() -> None:
    seen: list[httpx.Request] = []
    responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return responses.pop(0)

    gateway = HttpRevolutTokenGateway(transport=httpx.MockTransport(handler))

    def refresh(
        target: HttpRevolutTokenGateway, environment: RevolutEnvironment
    ) -> TokenGrant | TokenFailure:
        return target.refresh(
            environment=environment,
            client_id=CLIENT_ID,
            issuer=ISSUER,
            private_key_pem=KEY,
            refresh_token=SecretStr("refresh"),
            now=NOW,
        )

    responses.append(
        httpx.Response(
            200,
            json={
                "access_token": CANARY,
                "refresh_token": "refresh",
                "expires_in": 2399,
                "token_type": "bearer",
            },
        )
    )
    grant = gateway.exchange(
        environment=RevolutEnvironment.SANDBOX,
        client_id=CLIENT_ID,
        issuer=ISSUER,
        private_key_pem=KEY,
        code=SecretStr("auth-code"),
        now=NOW,
    )
    assert isinstance(grant, TokenGrant) and grant.expires_in == 2399
    assert CANARY not in repr(grant)
    assert str(seen[0].url) == "https://sandbox-b2b.revolut.com/api/1.0/auth/token"
    form = parse_qs(seen[0].content.decode())
    assert form["grant_type"] == ["authorization_code"] and form["code"] == [
        "auth-code"
    ]
    assert form["client_assertion_type"] == [
        "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
    ]
    assert form["client_assertion"][0].count(".") == 2 and "code_verifier" not in form

    def refuse_to_read() -> Iterator[bytes]:
        raise AssertionError("a refusal body was read")
        yield b""

    def endless() -> Iterator[bytes]:
        while True:
            yield b" " * 4096

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    for response, kind in (
        (httpx.Response(400, content=refuse_to_read()), "refused"),
        (httpx.Response(401, json={"error": "invalid_grant"}), "refused"),
        (httpx.Response(503), "unknown"),
        (
            httpx.Response(302, headers={"Location": "https://evil.invalid"}),
            "unavailable",
        ),
        (httpx.Response(200, content=b"not json"), "unknown"),
        (httpx.Response(200, content=endless()), "unknown"),
    ):
        responses.append(response)
        outcome = refresh(gateway, RevolutEnvironment.PRODUCTION)
        assert isinstance(outcome, TokenFailure) and outcome.kind == kind
    assert str(seen[-1].url) == "https://b2b.revolut.com/api/1.0/auth/token"
    assert parse_qs(seen[-1].content.decode())["grant_type"] == ["refresh_token"]
    gateway.close()

    def answer_lost(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("no answer", request=request)

    # The request left; whether the provider refreshed cannot be established.
    lost = HttpRevolutTokenGateway(transport=httpx.MockTransport(answer_lost))
    assert refresh(lost, RevolutEnvironment.SANDBOX) == TokenFailure(kind="unknown")

    ticks = iter([0.0, 31.0])
    slow = HttpRevolutTokenGateway(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b'{"access_token":')
        ),
        monotonic=lambda: next(ticks),
    )
    assert refresh(slow, RevolutEnvironment.SANDBOX) == TokenFailure(kind="unknown")

    offline = HttpRevolutTokenGateway(transport=httpx.MockTransport(unreachable))
    assert refresh(offline, RevolutEnvironment.SANDBOX) == TokenFailure(
        kind="unavailable"
    )
