"""Fixed-origin HubSpot HTTP boundary with no implicit mutation retries."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote

import httpx
from pydantic import SecretStr


class HubSpotAPIError(RuntimeError):
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


class HubSpotTransport:
    """A caller may inject an HTTP transport, never a provider base URL."""

    def __init__(
        self,
        access_token: SecretStr,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not access_token.get_secret_value().strip():
            raise ValueError("HubSpot access token is required")
        if not 0 < timeout <= 120:
            raise ValueError("HubSpot timeout must be between zero and 120 seconds")
        self._token = access_token
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
        read_only: bool = False,
    ) -> dict[str, Any]:
        allowed = (
            "/marketing/emails/2026-03",
            "/marketing/campaigns/2026-03",
            "/communication-preferences/2026-03",
            "/automation/v4/flows",
            "/automation/v4/workflow-id-mappings/batch/read",
            "/automation/v2/workflows/",
        )
        if (
            not any(
                path == prefix or path.startswith(prefix.rstrip("/") + "/")
                for prefix in allowed
            )
            or any(part in {".", ".."} for part in unquote(path).split("/"))
            or "\\" in unquote(path)
            or any(ord(character) < 32 for character in unquote(path))
            or method not in {"GET", "POST", "PATCH", "PUT", "DELETE"}
            or "?" in path
            or "#" in path
        ):
            raise ValueError("HubSpot route is outside the marketing integration")
        mutation = method != "GET" and not read_only
        try:
            response = self._http.request(
                method,
                "https://api.hubapi.com" + path,
                headers={
                    "Authorization": "Bearer " + self._token.get_secret_value(),
                    "Accept": "application/json",
                },
                json=body,
                params=params,
            )
        except httpx.HTTPError:
            raise HubSpotAPIError(
                "TRANSPORT",
                (
                    "HubSpot request failed; reconcile provider state before "
                    "repeating a mutation"
                ),
                outcome_unknown=mutation,
            ) from None
        if not 200 <= response.status_code < 300:
            status = response.status_code
            code, message = {
                401: (
                    "AUTHENTICATION",
                    "HubSpot token is invalid or expired; reauthorize before retrying",
                ),
                403: (
                    "ACCESS",
                    (
                        "HubSpot access denied; check app scopes and Marketing Hub "
                        "subscription tier"
                    ),
                ),
                404: ("NOT_FOUND", "HubSpot marketing resource was not found"),
                429: (
                    "RATE_LIMIT",
                    "HubSpot rate limit reached; no automatic retry was attempted",
                ),
            }.get(status, ("HTTP", "HubSpot rejected the marketing request"))
            retry = response.headers.get("Retry-After", "")
            raise HubSpotAPIError(
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
            raise HubSpotAPIError(
                "RESPONSE",
                "HubSpot returned an invalid JSON response",
                outcome_unknown=mutation,
            ) from None
        if not isinstance(data, dict):
            raise HubSpotAPIError(
                "RESPONSE",
                "HubSpot returned an unexpected response shape",
                outcome_unknown=mutation,
            )
        return data
