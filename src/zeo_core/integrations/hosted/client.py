"""Typed, credential-free client boundary for ZEOconnect operations."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue, model_validator

from zeo_core.contracts.connections import NormalizedError

_SECRET_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "client_secret",
        "credential",
        "credentials",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)


class HostedOperationStatus(StrEnum):
    """Closed dispositions returned by the hosted connection broker."""

    CONFIRMED = "confirmed"
    REFUSED = "refused"
    FAILED_SAFE = "failed_safe"
    AMBIGUOUS = "ambiguous"
    APPROVAL_REQUIRED = "approval_required"


class HostedArtifactDescriptor(BaseModel):
    """Bounded metadata for bytes fetched through the authenticated transport."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: str = Field(..., pattern=r"^art_[A-Za-z0-9_-]{8,200}$")
    content_sha256: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(..., ge=0)
    media_type: str = Field(..., min_length=1, max_length=200)
    filename: str = Field(..., min_length=1, max_length=255)

    @model_validator(mode="after")
    def _filename_is_one_safe_segment(self) -> HostedArtifactDescriptor:
        if (
            self.filename in {".", ".."}
            or "/" in self.filename
            or "\\" in self.filename
        ):
            raise ValueError("artifact filename must be one safe path segment")
        return self


class HostedOperationRequest(BaseModel):
    """Exact named operation request; no tenant, URL, method, header, or token."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    connection_id: str = Field(..., min_length=1, max_length=200)
    connector_revision: str = Field(..., min_length=1, max_length=200)
    operation_id: str = Field(..., min_length=1, max_length=200)
    arguments: dict[str, JsonValue]
    idempotency_key: str = Field(..., min_length=1, max_length=200)


class HostedOperationResponse(BaseModel):
    """Bounded broker response with mutually exclusive result shapes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: HostedOperationStatus
    execution_id: str = Field(..., min_length=1, max_length=200)
    result: JsonValue | None = None
    artifact: HostedArtifactDescriptor | None = None
    approval_url: HttpUrl | None = None
    normalized_error: NormalizedError | None = None
    receipt: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def _shape_matches_status(self) -> HostedOperationResponse:
        if self.normalized_error is not None and self.normalized_error.provider_detail:
            raise ValueError("provider detail is forbidden in hosted responses")
        if _contains_secret_key(self.result) or _contains_secret_key(self.receipt):
            raise ValueError("hosted response contains a secret-bearing field")
        representations = int(self.result is not None) + int(self.artifact is not None)
        if self.status is HostedOperationStatus.CONFIRMED:
            if representations != 1 or self.approval_url is not None:
                raise ValueError("confirmed response requires exactly one result")
            if self.normalized_error is not None:
                raise ValueError("confirmed response forbids normalized_error")
        elif self.status is HostedOperationStatus.APPROVAL_REQUIRED:
            if self.approval_url is None or representations or self.normalized_error:
                raise ValueError(
                    "approval-required response requires only approval_url"
                )
        elif representations or self.approval_url is not None:
            raise ValueError("non-confirmed response cannot carry a result")
        return self


@runtime_checkable
class HostedAuthorizedTransport(Protocol):
    """Authenticated transport owned by ZEOconnect pairing/custody code."""

    def invoke(self, request: HostedOperationRequest) -> HostedOperationResponse: ...

    def fetch_artifact(self, *, artifact_id: str, max_bytes: int) -> bytes: ...


class HostedConnectionClient:
    """Invoke curated operations; credentials remain entirely inside transport."""

    def __init__(self, *, transport: HostedAuthorizedTransport) -> None:
        self._transport = transport

    def invoke(self, request: HostedOperationRequest) -> HostedOperationResponse:
        return self._transport.invoke(request)

    def download_artifact(self, artifact: HostedArtifactDescriptor) -> bytes:
        content = self._transport.fetch_artifact(
            artifact_id=artifact.artifact_id,
            max_bytes=artifact.size_bytes,
        )
        if len(content) != artifact.size_bytes:
            raise HostedClientError("hosted artifact size did not match receipt")
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        if digest != artifact.content_sha256:
            raise HostedClientError("hosted artifact digest did not match receipt")
        return content


class HostedClientError(RuntimeError):
    """Sanitized failure at the hosted-client trust boundary."""


def _contains_secret_key(value: JsonValue | dict[str, JsonValue] | None) -> bool:
    if isinstance(value, Mapping):
        if any(str(key).lower() in _SECRET_KEYS for key in value):
            return True
        return any(_contains_secret_key(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_secret_key(item) for item in value)
    return False


__all__ = [
    "HostedArtifactDescriptor",
    "HostedAuthorizedTransport",
    "HostedClientError",
    "HostedConnectionClient",
    "HostedOperationRequest",
    "HostedOperationResponse",
    "HostedOperationStatus",
]
