"""
Immutable connector revision manifest, per packet section 5.1.

Consumed by: connection and execution contracts in this package (which pin
a ConnectorRevisionId); the (not-yet-built) admission and orchestration
layers (steps 5-6, out of this step's scope).
Must NOT contain: adapter imports, live provider calls, secret material.

A connector revision declares admitted business operations, not raw
provider endpoints (disposition 10: business operations are allowlisted).
Nothing in this module or its callers may accept a caller-selected origin,
path, auth header or callback URL -- every one of those is fixed at the
revision level, once, before any execution exists.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections.enums import IdempotencyMode, RiskClass
from zeo_core.contracts.connections.identity import (
    ConnectorId,
    ConnectorRevisionId,
    OperationId,
)


class BusinessOperation(BaseModel):
    """
    One admitted business operation declared by a connector revision.

    Business operations are named for what they accomplish
    (`google.drive.list_files_in_connected_folder`), never for the raw
    provider call underneath (`GET /drive/v3/files`) -- packet section 5.1's
    good/prohibited examples. This model does not itself enforce the naming
    convention (that is a connector-authoring lint, not a frozen contract's
    job); it fixes the fields a revision must declare per operation so
    admission (step 5) has something concrete to validate against:
    missing origin, unconstrained path, undeclared secret binding, absent
    idempotency mode, and absent reconciliation strategy for an effectful
    operation are all rejections admission must be able to make, and it can
    only make them if every one of those is a required field here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation_id: OperationId
    effect: EffectKind
    request_schema: dict[str, object]
    response_schema: dict[str, object]
    allowed_origin: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    path_template: str = Field(..., min_length=1)
    secret_bindings: tuple[str, ...] = Field(default_factory=tuple)
    redaction_paths: tuple[str, ...] = Field(default_factory=tuple)
    idempotency_mode: IdempotencyMode
    reconciliation_strategy: str | None = None

    @field_validator("allowed_origin")
    @classmethod
    def _non_empty_origin(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("allowed_origin must be non-empty")
        return v

    @field_validator("reconciliation_strategy")
    @classmethod
    def _normalize_blank_reconciliation(cls, v: str | None) -> str | None:
        # The real effect/reconciliation cross-field check lives on
        # ConnectorRevision below (it needs to see this operation's `effect`
        # field too). This validator only normalizes an empty string to
        # None so "" and unset are not two different representations of
        # "absent" by the time that cross-field check runs.
        if v is not None and not v.strip():
            return None
        return v


class ConnectorRevision(BaseModel):
    """
    One immutable revision of a connector, per packet section 5.1.

    Connector revisions are frozen: executions pin a ConnectorRevisionId,
    never a bare ConnectorId, so updating a connector creates a new
    revision and never mutates a historical execution's meaning
    (disposition 9). There is deliberately no "latest revision" concept
    anywhere in this contract -- callers that need one resolve it through
    persistence (step 4), not by asking a ConnectorRevision what comes
    after it, because a revision object has no way to know.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    connector_id: ConnectorId
    revision_id: ConnectorRevisionId
    provider: str = Field(..., min_length=1)
    authentication_profile: str = Field(..., min_length=1)
    permitted_upstream_origins: tuple[str, ...] = Field(..., min_length=1)
    required_provider_scopes: tuple[str, ...] = Field(default_factory=tuple)
    external_account_identity_probe: str = Field(..., min_length=1)
    health_probe: str = Field(..., min_length=1)
    operations: tuple[BusinessOperation, ...] = Field(..., min_length=1)
    request_size_limit_bytes: int = Field(..., gt=0)
    response_size_limit_bytes: int = Field(..., gt=0)
    timeout_seconds: float = Field(..., gt=0)
    follow_redirects: bool = False
    credential_injection_point: str = Field(..., min_length=1)
    redaction_policy: str = Field(..., min_length=1)
    risk_class: RiskClass
    provider_supports_native_idempotency: bool = False
    reconciliation_method: str | None = None
    webhook_verification_profile: str | None = None
    provider_error_mapping_version: str = Field(..., min_length=1)
    conformance_fixture_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("operations")
    @classmethod
    def _unique_operation_ids(
        cls, v: tuple[BusinessOperation, ...]
    ) -> tuple[BusinessOperation, ...]:
        seen: set[str] = set()
        for op in v:
            key = str(op.operation_id)
            if key in seen:
                raise ValueError(
                    f"duplicate operation_id within one connector revision: {key!r}"
                )
            seen.add(key)
        return v

    @field_validator("operations")
    @classmethod
    def _effectful_operations_declare_reconciliation(
        cls, v: tuple[BusinessOperation, ...]
    ) -> tuple[BusinessOperation, ...]:
        # idempotency_mode has no default (Field is required on
        # BusinessOperation), so a NOT_IDEMPOTENT operation only reaches
        # this validator if an author declared it deliberately -- disposition
        # 10 permits that. What it does not permit is an effectful operation
        # with no reconciliation path at all, which is the one thing this
        # validator rejects.
        read_only = {EffectKind.READ}
        for op in v:
            is_effectful = op.effect not in read_only
            if is_effectful and not op.reconciliation_strategy:
                raise ValueError(
                    "effectful business operation "
                    f"{op.operation_id!s} must declare a reconciliation_strategy "
                    "(disposition 14: ambiguous is not failed, and a "
                    "connector cannot be admitted without a declared "
                    "reconciliation path for the effects it can leave "
                    "in doubt)"
                )
        return v
