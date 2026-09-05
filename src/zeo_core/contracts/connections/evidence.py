"""Adapter-neutral, sanitized confirmation evidence."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zeo_core.contracts.connections.identity import (
    ConfirmationEvidenceRef,
    ExecutionId,
    OrganizationId,
)

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")


class ConfirmationEvidence(BaseModel):
    """Durable sanitized proof behind a confirmation evidence reference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_ref: ConfirmationEvidenceRef
    organization_id: OrganizationId
    execution_id: ExecutionId
    observed_at: datetime
    confirmation_digest: str = Field(..., min_length=64, max_length=64)

    @field_validator("confirmation_digest")
    @classmethod
    def _digest_is_lowercase_sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("confirmation_digest must be lowercase SHA-256 hex")
        return value


__all__ = ["ConfirmationEvidence"]
