"""
Normalized error contract, per packet section 5.6.

Consumed by: receipt contracts in this package; the (not-yet-built)
orchestration layer's error-mapping step (out of this step's scope).
Must NOT contain: raw tokens, cross-tenant identifiers, or any field that
could carry credential material. Section 5.6: "Provider detail remains
available for diagnosis but must not become the only product explanation" --
`code` is always the required, closed-taxonomy field so an orchestrator
never has to parse `provider_detail` text to branch, and `provider_detail`
is a caller-provided string, not a place this contract goes looking for
credential-shaped values itself (that redaction is the connector's
declared redaction_policy and redaction_paths, applied before this model is
ever constructed -- outside this step's scope).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from zeo_core.contracts.connections.enums import NormalizedErrorCode


class NormalizedError(BaseModel):
    """
    A provider failure normalized into the closed taxonomy of
    NormalizedErrorCode, per packet section 5.6.

    `code` is required and always drawn from the closed enum; `message` is a
    short, human-readable, product-level explanation; `provider_detail` is
    optional raw diagnostic text, present for engineers but never load-
    bearing for product behavior (disposition 15: "Provider errors map to a
    closed taxonomy while redacted provider metadata remains available for
    operations").
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: NormalizedErrorCode
    message: str = Field(..., min_length=1)
    provider_detail: str | None = None
