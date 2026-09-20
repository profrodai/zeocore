"""Fixed-origin, read-only Revolut Business HTTP boundary with no implicit retries."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from decimal import Decimal
from typing import Any

import httpx
from pydantic import SecretStr

from .models import RevolutEnvironment

_ORIGINS = {
    RevolutEnvironment.PRODUCTION: "https://b2b.revolut.com",
    RevolutEnvironment.SANDBOX: "https://sandbox-b2b.revolut.com",
}
_API = "/api/1.0"
_ROUTES = frozenset({"/accounts", "/transactions"})
_MAX_RESPONSE_BYTES = 16 * 1024 * 1024

_private_request: ContextVar[bool] = ContextVar(
    "revolut_private_request", default=False
)


class _PrivateHTTPLogs(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _private_request.get()


_private_filter = _PrivateHTTPLogs()


def _protect_http_logs() -> None:
    # Filter only this request's standard library HTTP logs. Other callers and
    # threads retain their logging. Host tracing/injected transports remain a
    # separate redaction responsibility.
    for name in (
        "httpx",
        "httpcore.connection",
        "httpcore.http11",
        "httpcore.http2",
        "httpcore.proxy",
        "httpcore.socks",
    ):
        logging.getLogger(name).addFilter(_private_filter)


class RevolutAPIError(RuntimeError):
    """Safe diagnostic: never retain provider bodies, request URLs or credentials."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class RevolutTransport:
    """A caller may inject an HTTP transport, never a provider base URL.

    The access token is supplied by the caller for the life of this object.
    Signing, exchange, refresh and custody belong to the credential owner.
    """

    def __init__(
        self,
        access_token: SecretStr,
        *,
        environment: RevolutEnvironment,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not access_token.get_secret_value().strip():
            raise ValueError("Revolut access token is required")
        if not 0 < timeout <= 120:
            raise ValueError("Revolut timeout must be between zero and 120 seconds")
        _protect_http_logs()
        self._token = access_token
        self._origin = _ORIGINS[RevolutEnvironment(environment)]
        self._http = httpx.Client(
            transport=transport,
            timeout=timeout,
            trust_env=False,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._http.close()

    def get(
        self, path: str, *, params: dict[str, str | int] | None = None
    ) -> list[dict[str, Any]]:
        if path not in _ROUTES:
            raise ValueError("Revolut route is outside the read integration")
        private_token = _private_request.set(True)
        try:
            response = self._http.get(
                self._origin + _API + path,
                headers={
                    "Authorization": "Bearer " + self._token.get_secret_value(),
                    "Accept": "application/json",
                },
                params=params,
            )
        except httpx.HTTPError:
            raise RevolutAPIError("TRANSPORT", "Revolut request failed") from None
        finally:
            _private_request.reset(private_token)
        if response.status_code != 200:
            status = response.status_code
            code, message = {
                401: (
                    "AUTHENTICATION",
                    "Revolut access token is invalid or expired",
                ),
                403: (
                    "ACCESS",
                    "Revolut access denied; check granted scopes and IP allowlist",
                ),
                404: ("NOT_FOUND", "Revolut resource was not found"),
                429: (
                    "RATE_LIMIT",
                    "Revolut rate limit reached; no automatic retry was attempted",
                ),
            }.get(status, ("HTTP", "Revolut rejected the read request"))
            retry = response.headers.get("Retry-After", "")
            raise RevolutAPIError(
                code,
                message,
                status_code=status,
                retry_after_seconds=int(retry)
                if retry.isascii() and retry.isdigit() and len(retry) < 9
                else None,
            )
        content = response.content
        if len(content) > _MAX_RESPONSE_BYTES:
            raise RevolutAPIError(
                "RESPONSE", "Revolut response exceeded the size limit"
            )
        if self._token.get_secret_value().encode() in content:
            raise RevolutAPIError(
                "RESPONSE", "Revolut response repeated the request credential"
            )
        try:
            # Amounts arrive as JSON numbers; binary floats would corrupt money.
            data = json.loads(content, parse_float=Decimal)
        except ValueError:
            raise RevolutAPIError(
                "RESPONSE", "Revolut returned an invalid JSON response"
            ) from None
        if not isinstance(data, list) or not all(isinstance(i, dict) for i in data):
            raise RevolutAPIError(
                "RESPONSE", "Revolut returned an unexpected response shape"
            )
        return data
