"""Capability invocation evidence: records, digests, and redaction helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zeo_core.contracts.artifacts.refs import ArtifactRef
from zeo_core.contracts.capabilities.identity import CapabilityId
from zeo_core.contracts.common.enums import CapabilityOutcome, CapabilityStatus
from zeo_core.contracts.common.ids import generate_invocation_id

_REDACTED = "***"
_SECRET_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "oauth",
)


class CapabilityInvocationRecord(BaseModel):
    """
    Serializable evidence a runner may persist.

    Not an organizational execution receipt. Runners supply invocation_id,
    timestamps, authorization context, storage, and trace linkage.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    invocation_id: str = Field(default_factory=generate_invocation_id)
    capability_id: CapabilityId
    request_digest: str
    started_at: datetime
    ended_at: datetime
    outcome: CapabilityOutcome
    status: CapabilityStatus
    error_code: str | None = None
    artifact_refs: tuple[ArtifactRef, ...] = ()
    result_digest: str | None = None
    redactions: tuple[str, ...] = ()

    @field_validator("request_digest", "result_digest")
    @classmethod
    def _digest_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("digests must be lowercase hex SHA-256")
        return value


def canonical_json(value: object) -> str:
    """Deterministic JSON for digests (sorted keys, compact)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest_payload(value: object) -> str:
    """SHA-256 of canonical JSON."""
    encoded = canonical_json(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _looks_secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS)


def redact_value(
    value: Any,  # noqa: ANN401 -- redaction walks arbitrary JSON-shaped data
    *,
    path: str = "$",
    extra_paths: frozenset[str] = frozenset(),
) -> tuple[Any, tuple[str, ...]]:  # noqa: ANN401 -- returns same JSON-shaped structure
    """
    Redact secret-shaped keys and explicit paths.

    Returns (redacted_value, paths_redacted). Never copies raw tokens into the
    record.
    """
    redacted_paths: list[str] = []

    def walk(node: Any, current: str) -> Any:  # noqa: ANN401
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for key, item in node.items():
                child = f"{current}.{key}"
                if _looks_secret_key(str(key)) or child in extra_paths:
                    out[str(key)] = _REDACTED
                    redacted_paths.append(child)
                else:
                    out[str(key)] = walk(item, child)
            return out
        if isinstance(node, list):
            return [walk(item, f"{current}[{i}]") for i, item in enumerate(node)]
        if current in extra_paths:
            redacted_paths.append(current)
            return _REDACTED
        return node

    return walk(value, path), tuple(redacted_paths)
