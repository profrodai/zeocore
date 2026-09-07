"""Fixed-origin Kit HTTP boundary with no implicit mutation retries."""

from __future__ import annotations

import logging
import re
from contextvars import ContextVar
from typing import Any
from urllib.parse import unquote

import httpx
from pydantic import SecretStr

_private_request: ContextVar[bool] = ContextVar("kit_private_request", default=False)


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


class KitAPIError(RuntimeError):
    """Safe diagnostic: never retain provider bodies, request URLs or credentials."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        outcome_unknown: bool = False,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.outcome_unknown = outcome_unknown
        self.retry_after_seconds = retry_after_seconds


class KitTransport:
    """A caller may inject an HTTP transport, never a provider base URL."""

    def __init__(
        self,
        api_key: SecretStr | None = None,
        *,
        access_token: SecretStr | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        if (api_key is None) == (access_token is None):
            raise ValueError("Supply exactly one Kit API key or OAuth access token")
        credential = api_key if api_key is not None else access_token
        if credential is None or not credential.get_secret_value().strip():
            raise ValueError("Kit credential is required")
        if not 0 < timeout <= 120:
            raise ValueError("Kit timeout must be between zero and 120 seconds")
        _protect_http_logs()
        self._token = credential
        self._auth_header = "X-Kit-Api-Key" if api_key is not None else "Authorization"
        self._auth_prefix = "" if api_key is not None else "Bearer "
        self._http = httpx.Client(
            transport=transport,
            timeout=timeout,
            trust_env=False,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._http.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, str | int | bool] | None = None,
    ) -> dict[str, Any]:
        routes = {
            r"/v4/account(?:/email_stats)?": {"GET"},
            r"/v4/broadcasts": {"GET", "POST"},
            r"/v4/broadcasts/stats": {"GET"},
            r"/v4/broadcasts/[1-9][0-9]*": {"GET", "PUT", "DELETE"},
            r"/v4/broadcasts/[1-9][0-9]*/(?:stats|clicks)": {"GET"},
            r"/v4/(?:email_templates|segments)": {"GET"},
            r"/v4/sequences": {"GET", "POST"},
            r"/v4/sequences/[1-9][0-9]*": {"GET", "PUT", "DELETE"},
            r"/v4/sequences/[1-9][0-9]*/emails": {"GET", "POST"},
            r"/v4/sequences/[1-9][0-9]*/emails/[1-9][0-9]*": {"GET", "PUT", "DELETE"},
            r"/v4/sequences/[1-9][0-9]*/subscribers": {"GET"},
            r"/v4/sequences/[1-9][0-9]*/subscribers/[1-9][0-9]*": {"POST"},
            r"/v4/subscribers": {"GET", "POST"},
            r"/v4/subscribers/[1-9][0-9]*": {"GET"},
            r"/v4/subscribers/[1-9][0-9]*/(?:tags|stats)": {"GET"},
            r"/v4/subscribers/[1-9][0-9]*/unsubscribe": {"POST"},
            r"/v4/tags": {"GET", "POST"},
            r"/v4/tags/[1-9][0-9]*": {"PUT"},
            r"/v4/tags/[1-9][0-9]*/subscribers": {"GET"},
            r"/v4/tags/[1-9][0-9]*/subscribers/[1-9][0-9]*": {"POST", "DELETE"},
        }
        if (
            not any(
                re.fullmatch(pattern, path) and method in methods
                for pattern, methods in routes.items()
            )
            or any(part in {".", ".."} for part in unquote(path).split("/"))
            or "\\" in unquote(path)
            or any(ord(character) < 32 for character in unquote(path))
            or method not in {"GET", "POST", "PATCH", "PUT", "DELETE"}
            or "?" in path
            or "#" in path
        ):
            raise ValueError("Kit route is outside the marketing integration")
        mutation = method != "GET"
        private_token = _private_request.set(True)
        try:
            response = self._http.request(
                method,
                "https://api.kit.com" + path,
                headers={
                    self._auth_header: self._auth_prefix
                    + self._token.get_secret_value(),
                    "Accept": "application/json",
                },
                json=body,
                params=params,
            )
        except httpx.HTTPError:
            raise KitAPIError(
                "TRANSPORT",
                (
                    "Kit request failed; reconcile provider state before "
                    "repeating a mutation"
                ),
                outcome_unknown=mutation,
            ) from None
        finally:
            _private_request.reset(private_token)
        if not 200 <= response.status_code < 300:
            status = response.status_code
            code, message = {
                401: (
                    "AUTHENTICATION",
                    "Kit token is invalid or expired; reauthorize before retrying",
                ),
                403: (
                    "ACCESS",
                    (
                        "Kit access denied; check app authentication and Kit "
                        "subscription tier"
                    ),
                ),
                404: ("NOT_FOUND", "Kit marketing resource was not found"),
                429: (
                    "RATE_LIMIT",
                    "Kit rate limit reached; no automatic retry was attempted",
                ),
            }.get(status, ("HTTP", "Kit rejected the marketing request"))
            retry = response.headers.get("Retry-After", "")
            raise KitAPIError(
                code,
                message,
                status_code=status,
                outcome_unknown=mutation and status >= 500,
                retry_after_seconds=int(retry)
                if retry.isascii() and retry.isdigit() and len(retry) < 9
                else None,
            )
        if response.status_code == 204:
            return {}
        try:
            data = response.json()
        except ValueError:
            raise KitAPIError(
                "RESPONSE",
                "Kit returned an invalid JSON response",
                outcome_unknown=mutation,
            ) from None
        if not isinstance(data, dict):
            raise KitAPIError(
                "RESPONSE",
                "Kit returned an unexpected response shape",
                outcome_unknown=mutation,
            )
        return data
