# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/__init__.py
# module: quack_core.contracts.common.__init__
# role: module
# neighbors: enums.py, ids.py, time.py, typing.py, versions.py
# exports: CapabilityStatus, LogLevel, ArtifactKind, StorageScheme, ChecksumAlgorithm, generate_run_id, generate_artifact_id, is_valid_uuid (+11 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 21a4e25
# === QV-LLM:END ===

"""
Common utilities and types for contracts.

Provides shared enums, ID generation, timestamps, and type aliases.
"""

from quack_core.contracts.common.enums import (
    CapabilityStatus,
    LogLevel,
    ArtifactKind,
    StorageScheme,
    ChecksumAlgorithm,
)
from quack_core.contracts.common.ids import (
    generate_run_id,
    generate_artifact_id,
    is_valid_uuid,
    RunID,
    ArtifactID,
)
from quack_core.contracts.common.time import (
    utcnow,
    utcnow_iso,
)
from quack_core.contracts.common.versions import (
    CONTRACTS_VERSION,
    MANIFEST_VERSION,
    ARTIFACT_SCHEMA_VERSION,
    ENVELOPE_VERSION,
)
from quack_core.contracts.common.typing import (
    Metadata,
    ErrorCode,
    ArtifactRole,
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