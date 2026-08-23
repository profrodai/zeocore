"""
Common utilities and types for contracts.

Provides shared enums, ID generation, timestamps, and type aliases.
"""

from zeo_core.contracts.common.enums import (
    ArtifactKind,
    CapabilityOutcome,
    CapabilityStatus,
    ChecksumAlgorithm,
    ConcurrencyMode,
    EffectKind,
    LogLevel,
    StorageScheme,
)
from zeo_core.contracts.common.ids import (
    ArtifactID,
    RunID,
    generate_artifact_id,
    generate_invocation_id,
    generate_run_id,
    is_valid_uuid,
)
from zeo_core.contracts.common.time import (
    utcnow,
    utcnow_iso,
)
from zeo_core.contracts.common.typing import (
    ArtifactRole,
    ErrorCode,
    Metadata,
)
from zeo_core.contracts.common.versions import (
    ARTIFACT_SCHEMA_VERSION,
    CAPABILITY_MANIFEST_SCHEMA_VERSION,
    CONTRACTS_VERSION,
    ENVELOPE_VERSION,
    MANIFEST_VERSION,
)

__all__ = [
    # Enums
    "CapabilityStatus",
    "CapabilityOutcome",
    "EffectKind",
    "ConcurrencyMode",
    "LogLevel",
    "ArtifactKind",
    "StorageScheme",
    "ChecksumAlgorithm",
    # IDs
    "generate_run_id",
    "generate_artifact_id",
    "generate_invocation_id",
    "is_valid_uuid",
    "RunID",
    "ArtifactID",
    # Time
    "utcnow",
    "utcnow_iso",
    # Versions
    "CONTRACTS_VERSION",
    "MANIFEST_VERSION",
    "ARTIFACT_SCHEMA_VERSION",
    "ENVELOPE_VERSION",
    "CAPABILITY_MANIFEST_SCHEMA_VERSION",
    # Types
    "Metadata",
    "ErrorCode",
    "ArtifactRole",
]
