"""
QuackCore Contracts - Canonical Data Contracts (Ring A / Kernel)

This module defines the stable, versionable contracts for the QuackCore system.
See GET-STARTED.md for architecture details and contribution guidelines.

Quick Start:
    >>> from quack_core.contracts import (
    ...     CapabilityResult,
    ...     ArtifactRef,
    ...     RunManifest,
    ...     StorageRef
    ... )

    >>> # Tool emits result
    >>> result = CapabilityResult.ok(
    ...     data={"transcription": "Hello world"},
    ...     msg="Transcription completed"
    ... )

    >>> # Tool creates artifact reference
    >>> artifact = ArtifactRef(
    ...     role="transcript_txt",
    ...     kind=ArtifactKind.final,
    ...     content_type="text/plain",
    ...     storage=StorageRef(
    ...         scheme=StorageScheme.local,
    ...         uri="file:///data/transcript.txt"
    ...     )
    ... )
"""

# Common utilities
# Artifacts (refs, manifests)
from quack_core.contracts.artifacts import (
    ArtifactRef,
    Checksum,
    ManifestInput,
    Provenance,
    RunManifest,
    StorageRef,
    ToolInfo,
)

# Capability models (demo only -- see demo/__init__.py: implementations are
# internal-only and not exported; Media capability models below remain
# commented out to match __all__, which does not yet declare them stable)
from quack_core.contracts.capabilities import (
    # Demo (models only)
    EchoRequest,
    # SlicedClipData,
    # SliceVideoRequest,
    # SliceVideoResponse,
    # Media
    # TimeRange,
    # TranscribeRequest,
    # TranscribeResponse,
    # TranscriptionSegment,
    VideoRefRequest,
)
from quack_core.contracts.common import (  # Versions; Enums; IDs; Time
    ARTIFACT_SCHEMA_VERSION,
    CONTRACTS_VERSION,
    ENVELOPE_VERSION,
    MANIFEST_VERSION,
    ArtifactKind,
    CapabilityStatus,
    ChecksumAlgorithm,
    LogLevel,
    StorageScheme,
    generate_artifact_id,
    generate_run_id,
    is_valid_uuid,
    utcnow,
    utcnow_iso,
)

# Envelopes (results, errors, logs)
from quack_core.contracts.envelopes import (
    CapabilityError,
    CapabilityLogEvent,
    CapabilityResult,
)

__version__ = CONTRACTS_VERSION

__all__ = [
    # --- Common ---
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
    # Time
    "utcnow",
    "utcnow_iso",
    # Versions
    "CONTRACTS_VERSION",
    "MANIFEST_VERSION",
    "ARTIFACT_SCHEMA_VERSION",
    "ENVELOPE_VERSION",
    # --- Envelopes ---
    "CapabilityResult",
    "CapabilityError",
    "CapabilityLogEvent",
    # --- Artifacts ---
    "StorageRef",
    "Checksum",
    "ArtifactRef",
    "ToolInfo",
    "Provenance",
    "ManifestInput",
    "RunManifest",
    # --- Capabilities ---
    # Media
    # "TimeRange",
    # "SliceVideoRequest",
    # "SlicedClipData",
    # "SliceVideoResponse",
    # "TranscribeRequest",
    # "TranscriptionSegment",
    # "TranscribeResponse",
    # Demo (models only, not implementations)
    "EchoRequest",
    "VideoRefRequest",
]
