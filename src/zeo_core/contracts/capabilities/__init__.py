"""
Capability request/response contracts.

This module defines the API schemas for all ZeoCore capabilities.
Implementations live in Ring B (zeo_core.tools), not here.
"""

from zeo_core.contracts.capabilities.definition import (
    CapabilityDefinition,
    schemas_from_models,
)
from zeo_core.contracts.capabilities.demo.models import (
    EchoRequest,
    VideoRefRequest,
)
from zeo_core.contracts.capabilities.guards import (
    GUARD_REJECTION_OUTCOME,
    GuardIssue,
    GuardResult,
    RequestGuard,
)
from zeo_core.contracts.capabilities.identity import CapabilityId, parse_semver
from zeo_core.contracts.capabilities.invocation import (
    CapabilityInvocationRecord,
    canonical_json,
    digest_payload,
    redact_value,
)
from zeo_core.contracts.capabilities.manifest import CapabilityManifest
from zeo_core.contracts.capabilities.metadata import (
    CapabilityDeprecation,
    CapabilityEffects,
    CapabilityExample,
    CapabilityRequirements,
    FilesystemRequirement,
    JsonValue,
    NetworkRequirement,
)

__all__ = [
    "EchoRequest",
    "VideoRefRequest",
    "CapabilityId",
    "parse_semver",
    "CapabilityDefinition",
    "schemas_from_models",
    "CapabilityExample",
    "CapabilityEffects",
    "CapabilityRequirements",
    "CapabilityDeprecation",
    "NetworkRequirement",
    "FilesystemRequirement",
    "JsonValue",
    "GuardIssue",
    "GuardResult",
    "RequestGuard",
    "GUARD_REJECTION_OUTCOME",
    "CapabilityManifest",
    "CapabilityInvocationRecord",
    "canonical_json",
    "digest_payload",
    "redact_value",
]
