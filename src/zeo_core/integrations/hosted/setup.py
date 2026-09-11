"""Versioned presentation contracts. These snapshots never authorize dispatch.

Only trusted, reviewed catalogue metadata supplies copy and action identifiers.
Hosts own authentication, enrollment endpoints, policy, and fresh admission.
Importing or evaluating this module performs no I/O.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from .profile import (
    ExecutionProfile,
    HostedResourceSummary,
    OpaqueConnectionHandle,
    ServiceRequirement,
)


class SetupAction(StrEnum):
    SIGN_IN = "sign_in"
    SELECT_ORGANIZATION = "select_organization"
    REVIEW_ACCESS = "review_access"
    PAIR_INSTALLATION = "pair_installation"
    CONNECT = "connect"
    REPAIR = "repair"
    SELECT_RESOURCES = "select_resources"
    REVIEW_PROVIDER_FEATURES = "review_provider_features"
    RECHECK = "recheck"
    REQUEST_RUNTIME_DECISION = "request_runtime_decision"
    INSTALL_LOCAL_TOOL = "install_local_tool"
    OPEN_LOCAL_SETTINGS = "open_local_settings"
    REVOKE = "revoke"


class AuthMethod(StrEnum):
    OAUTH = "oauth"
    INSTALLATION = "installation_authorization"
    DEVICE = "device_consent"
    GUIDED_SECRET = "guided_secret"  # noqa: S105 -- auth-method identifier
    LOCAL_PERMISSION = "local_permission"
    LOCAL_TOOL = "local_tool"
    UNSUPPORTED = "unsupported"


class SupportStatus(StrEnum):
    IMPLEMENTED = "implemented"
    NOT_ADMITTED = "not_admitted"
    UNSUPPORTED = "unsupported"


class _Metadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProfileSetup(_Metadata):
    profile: ExecutionProfile
    support: SupportStatus
    auth_method: AuthMethod
    auth_revision: str = Field(min_length=1, max_length=200)
    limitations: tuple[str, ...] = Field(min_length=1, max_length=20)
    actions: tuple[SetupAction, ...] = ()

    @model_validator(mode="after")
    def _unavailable_does_not_offer_enrollment(self) -> ProfileSetup:
        if self.support is not SupportStatus.IMPLEMENTED and any(
            action in {SetupAction.CONNECT, SetupAction.PAIR_INSTALLATION}
            for action in self.actions
        ):
            raise ValueError("unavailable profiles cannot offer enrollment")
        return self


class OperationSetup(_Metadata):
    """Existing logical operation plus optional existing capability mapping."""

    operation: str = Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+$")
    capability: str | None = Field(
        default=None, pattern=r"^[a-z][a-z0-9_.]+@[0-9]+\.[0-9]+\.[0-9]+$"
    )
    requirement: ServiceRequirement

    @model_validator(mode="after")
    def _mapping_matches_requirement(self) -> OperationSetup:
        if self.operation not in self.requirement.operations:
            raise ValueError("operation is absent from its service requirement")
        if self.capability and self.capability.split("@")[0] != self.operation:
            raise ValueError("capability and operation identities disagree")
        return self


class SetupManifest(_Metadata):
    """Safe catalogue data, not provider configuration or account readiness."""

    schema_version: Literal[1] = 1
    integration_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:\.[a-z0-9]+)*$")
    display_name: str = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=500)
    requested_access: str = Field(min_length=1, max_length=500)
    account_label: str = Field(min_length=1, max_length=100)
    resource_selection: str = Field(min_length=1, max_length=500)
    custody: str = Field(min_length=1, max_length=500)
    repair: str = Field(min_length=1, max_length=500)
    revocation: str = Field(min_length=1, max_length=500)
    prerequisites: tuple[str, ...] = Field(min_length=1, max_length=20)
    profiles: tuple[ProfileSetup, ...] = Field(min_length=1, max_length=4)
    operations: tuple[OperationSetup, ...] = Field(default=(), max_length=100)
    unmapped_operations: str | None = Field(default=None, max_length=500)
    identity_probe: str = Field(min_length=1, max_length=300)
    health_probe: str = Field(min_length=1, max_length=300)
    status_ttl_seconds: int = Field(default=10, ge=1, le=10)
    guide: str = Field(pattern=r"^[a-z][a-z0-9-]*\.md$")
    source_revision: str = Field(min_length=1, max_length=200)
    reviewed_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    owner: str = Field(min_length=1, max_length=100)
    live_validation: Literal["not_run", "passed", "failed"] = "not_run"
    live_evidence: str | None = Field(default=None, min_length=1, max_length=300)
    surface: Literal["business", "builder", "model", "local", "onboarding"]

    @model_validator(mode="after")
    def _unique_profiles_and_operations(self) -> SetupManifest:
        if len({item.profile for item in self.profiles}) != len(self.profiles):
            raise ValueError("duplicate execution profile")
        if len({item.operation for item in self.operations}) != len(self.operations):
            raise ValueError("duplicate operation mapping")
        if not self.operations and not self.unmapped_operations:
            raise ValueError("missing operations require an explicit disposition")
        if self.live_validation != "not_run" and not self.live_evidence:
            raise ValueError("live qualification requires evidence")
        return self


class AvailabilityDimension(StrEnum):
    IMPLEMENTATION = "implementation"
    ENTITLEMENT = "entitlement"
    CONSENT = "provider_consent"
    ACCOUNT = "account_health"
    RESOURCE = "resource_binding"
    RUNTIME = "runtime_authority"
    REACHABILITY = "reachability"


class BlockerCode(StrEnum):
    IDENTITY_CONFLICT = "identity_conflict"
    ORGANIZATION_CONFLICT = "organization_conflict"
    REVOKED = "revoked"
    UNSUPPORTED = "unsupported"
    ENTITLEMENT_REQUIRED = "entitlement_required"
    INSTALLATION_OFFLINE = "installation_offline"
    CONSENT_REQUIRED = "consent_required"
    REPAIR_REQUIRED = "repair_required"
    RESOURCE_REQUIRED = "resource_required"
    FEATURE_UNAVAILABLE = "feature_unavailable"
    PROVIDER_OUTAGE = "provider_outage"
    RATE_LIMITED = "rate_limited"
    RUNTIME_DECISION_REQUIRED = "runtime_decision_required"
    UNKNOWN = "unknown"
    STALE = "stale"


# One reviewed order; provider consent cannot conceal an identity conflict.
_PRIORITY = {code: index for index, code in enumerate(BlockerCode)}
_ACTIONS = {
    BlockerCode.IDENTITY_CONFLICT: (SetupAction.SIGN_IN,),
    BlockerCode.ORGANIZATION_CONFLICT: (SetupAction.SELECT_ORGANIZATION,),
    BlockerCode.REVOKED: (SetupAction.REVIEW_ACCESS,),
    BlockerCode.UNSUPPORTED: (),
    BlockerCode.ENTITLEMENT_REQUIRED: (SetupAction.REVIEW_ACCESS,),
    BlockerCode.INSTALLATION_OFFLINE: (SetupAction.RECHECK,),
    BlockerCode.CONSENT_REQUIRED: (SetupAction.CONNECT,),
    BlockerCode.REPAIR_REQUIRED: (SetupAction.REPAIR,),
    BlockerCode.RESOURCE_REQUIRED: (SetupAction.SELECT_RESOURCES,),
    BlockerCode.FEATURE_UNAVAILABLE: (SetupAction.REVIEW_PROVIDER_FEATURES,),
    BlockerCode.PROVIDER_OUTAGE: (SetupAction.RECHECK,),
    BlockerCode.RATE_LIMITED: (SetupAction.RECHECK,),
    BlockerCode.RUNTIME_DECISION_REQUIRED: (SetupAction.REQUEST_RUNTIME_DECISION,),
    BlockerCode.UNKNOWN: (SetupAction.RECHECK,),
    BlockerCode.STALE: (SetupAction.RECHECK,),
}


class AvailabilityFact(_Metadata):
    dimension: AvailabilityDimension
    state: Literal["satisfied", "blocked", "unknown"]
    revision: str = Field(min_length=1, max_length=200)
    observed_at: AwareDatetime
    fresh_until: AwareDatetime
    blockers: tuple[BlockerCode, ...] = ()

    @model_validator(mode="after")
    def _coherent_fact(self) -> AvailabilityFact:
        if self.fresh_until <= self.observed_at:
            raise ValueError("freshness must end after the observation")
        if (self.state == "blocked") != bool(self.blockers):
            raise ValueError("only blocked facts must specify blockers")
        if len(set(self.blockers)) != len(self.blockers):
            raise ValueError("duplicate blocker")
        return self


class AvailabilityBlocker(_Metadata):
    dimension: AvailabilityDimension
    code: BlockerCode
    actions: tuple[SetupAction, ...]


class AvailabilityView(_Metadata):
    """Display only: no method or field can turn this into an authorization."""

    schema_version: Literal[1] = 1
    blockers: tuple[AvailabilityBlocker, ...]
    dispatch_recheck_required: Literal[True] = True

    @property
    def primary(self) -> AvailabilityBlocker | None:
        return self.blockers[0] if self.blockers else None


class AvailabilitySnapshot(_Metadata):
    schema_version: Literal[1] = 1
    requirement: ServiceRequirement
    profile: ExecutionProfile
    connection: OpaqueConnectionHandle | None = None
    revision: str = Field(min_length=1, max_length=200)
    facts: tuple[AvailabilityFact, ...] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def _all_seven_dimensions(self) -> AvailabilitySnapshot:
        if {fact.dimension for fact in self.facts} != set(AvailabilityDimension):
            raise ValueError(
                "exactly one fact for every availability dimension required"
            )
        return self

    def evaluate(self, *, now: datetime) -> AvailabilityView:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("evaluation requires an aware time")
        blockers: list[AvailabilityBlocker] = []
        for fact in self.facts:
            codes = set(fact.blockers)
            if fact.state == "unknown" or fact.observed_at > now:
                codes.add(BlockerCode.UNKNOWN)
            if now >= fact.fresh_until:
                codes.add(BlockerCode.STALE)
            blockers.extend(
                AvailabilityBlocker(
                    dimension=fact.dimension, code=code, actions=_ACTIONS[code]
                )
                for code in codes
            )
        blockers.sort(key=lambda item: (_PRIORITY[item.code], item.dimension.value))
        return AvailabilityView(blockers=tuple(blockers))


class ResourceSelectionSemantics(StrEnum):
    EXACT_OBJECT = "exact_object"
    FIXED_COLLECTION = "fixed_collection"
    DYNAMIC_CONTAINER = "dynamic_container"


class HostedResourceSelection(HostedResourceSummary):
    """Versioned extension of the existing summary, not a new Connection family."""

    schema_version: Literal[1] = 1
    provider: str = Field(pattern=r"^[a-z][a-z0-9_.]*$")
    connection: OpaqueConnectionHandle
    resource_type: str = Field(min_length=1, max_length=100)
    provider_version: str | None = Field(default=None, min_length=1, max_length=300)
    observed_at: AwareDatetime
    grant_revision: int = Field(ge=1)
    semantics: ResourceSelectionSemantics
    members: tuple[str, ...] = Field(default=(), max_length=100)
    includes_future_members: bool

    @model_validator(mode="after")
    def _explicit_membership(self) -> HostedResourceSelection:
        fixed = self.semantics is ResourceSelectionSemantics.FIXED_COLLECTION
        dynamic = self.semantics is ResourceSelectionSemantics.DYNAMIC_CONTAINER
        if fixed != bool(self.members):
            raise ValueError("only fixed collections must enumerate their members")
        if len(set(self.members)) != len(self.members) or any(
            not item.strip() or len(item) > 500 for item in self.members
        ):
            raise ValueError("members require unique bounded opaque identities")
        if dynamic != self.includes_future_members:
            raise ValueError("future membership requires explicit dynamic semantics")
        return self
