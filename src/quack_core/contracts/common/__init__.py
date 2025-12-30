# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/__init__.py
# module: quack_core.contracts.common.__init__
# role: module
# neighbors: enums.py, ids.py, time.py, typing.py, versions.py
# exports: CapabilityStatus, LogLevel, ArtifactKind, StorageScheme, ChecksumAlgorithm, generate_run_id, generate_artifact_id, is_valid_uuid (+11 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
Common utilities and types for contracts.

Provides shared enums, ID generation, timestamps, and type aliases.
"""

from quack_core.contracts.common.enums import (
    ArtifactKind,
    CapabilityStatus,
    ChecksumAlgorithm,
    LogLevel,
    StorageScheme,
)
from quack_core.contracts.common.ids import (
    ArtifactID,
    RunID,
    generate_artifact_id,
    generate_run_id,
    is_valid_uuid,
)
from quack_core.contracts.common.time import (
    utcnow,
    utcnow_iso,
)
from quack_core.contracts.common.typing import (
    ArtifactRole,
    ErrorCode,
    Metadata,
)
from quack_core.contracts.common.versions import (
    ARTIFACT_SCHEMA_VERSION,
    CONTRACTS_VERSION,
    ENVELOPE_VERSION,
    MANIFEST_VERSION,
)

__all__ = [
    # Enums
    "CapabilityStatus",
    "LogLevel",
    "ArtifactKind",
    "StorageScheme",
    "ChecksumAlgorithm",
    # IDs
    "generate_run_id",
    "generate_artifact_id",
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
    # Types
    "Metadata",
    "ErrorCode",
    "ArtifactRole",
]
