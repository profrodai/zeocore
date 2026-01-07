# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/__init__.py
# module: quack_core.contracts.__init__
# role: module
# exports: CapabilityStatus, LogLevel, ArtifactKind, StorageScheme, ChecksumAlgorithm, generate_run_id, generate_artifact_id, is_valid_uuid (+18 more)
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

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

'''
# Capability models
from quack_core.contracts.capabilities import (
    # Demo (models only)
    EchoRequest,
    SlicedClipData,
    SliceVideoRequest,
    SliceVideoResponse,
    # Media
    TimeRange,
    TranscribeRequest,
    TranscribeResponse,
    TranscriptionSegment,
    VideoRefRequest,
)
'''

from quack_core.contracts.common import (
    ARTIFACT_SCHEMA_VERSION,
    # Versions
    CONTRACTS_VERSION,
    ENVELOPE_VERSION,
    MANIFEST_VERSION,
    ArtifactKind,
    # Enums
    CapabilityStatus,
    ChecksumAlgorithm,
    LogLevel,
    StorageScheme,
    generate_artifact_id,
    # IDs
    generate_run_id,
    is_valid_uuid,
    # Time
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
    #"TimeRange",
    #"SliceVideoRequest",
    #"SlicedClipData",
    #"SliceVideoResponse",
    #"TranscribeRequest",
    #"TranscriptionSegment",
    #"TranscribeResponse",
    # Demo (models only, not implementations)
    "EchoRequest",
    "VideoRefRequest",
]
