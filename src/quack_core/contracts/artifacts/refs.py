# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/artifacts/refs.py
# module: quack_core.contracts.artifacts.refs
# role: module
# neighbors: __init__.py, manifest.py
# exports: StorageRef, Checksum, ArtifactRef
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Artifact and storage reference models.

Consumed by: ALL Ring B tools (to emit artifacts), Ring C orchestrators (to route)
Must NOT contain: File I/O, upload logic, storage implementation

These models define HOW to reference artifacts without implementing
the actual storage operations.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from quack_core.contracts.common.enums import (
    ArtifactKind,
    ChecksumAlgorithm,
    StorageScheme,
)
from quack_core.contracts.common.ids import generate_artifact_id, is_valid_uuid
from quack_core.contracts.common.time import utcnow
from quack_core.contracts.common.typing import ArtifactRole


class StorageRef(BaseModel):
    """
    Reference to where an artifact is stored.

    This abstraction enables pluggable storage backends without changing
    artifact contracts. Tools emit StorageRefs, runners read them.

    Scheme Examples:
        - local: file:///data/transcript.txt
        - s3: s3://my-bucket/transcripts/abc123.txt
        - gcs: gs://my-bucket/transcripts/abc123.txt
        - https: https://storage.example.com/file.mp4
        - drive: drive://1AbC-FileId
        - custom: Use scheme_custom to specify (e.g., "minio", "ceph")

    Example:
        >>> # Local file
        >>> ref = StorageRef(
        ...     scheme=StorageScheme.local,
        ...     uri="file:///data/output/transcript.txt"
        ... )

        >>> # S3 object
        >>> ref = StorageRef(
        ...     scheme=StorageScheme.s3,
        ...     uri="s3://my-bucket/outputs/transcript.txt",
        ...     bucket="my-bucket",
        ...     key="outputs/transcript.txt",
        ...     metadata={"region": "us-east-1"}
        ... )

        >>> # Custom storage backend
        >>> ref = StorageRef(
        ...     scheme=StorageScheme.custom,
        ...     scheme_custom="minio",
        ...     uri="minio://my-bucket/file.mp4"
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "scheme": "local",
                    "uri": "file:///data/transcript.txt",
                    "metadata": {}
                },
                {
                    "scheme": "s3",
                    "uri": "s3://my-bucket/outputs/video.mp4",
                    "bucket": "my-bucket",
                    "key": "outputs/video.mp4",
                    "metadata": {"region": "us-east-1"}
                },
                {
                    "scheme": "custom",
                    "scheme_custom": "minio",
                    "uri": "minio://my-bucket/file.mp4",
                    "metadata": {"endpoint": "minio.example.com:9000"}
                }
            ]
        }
    )

    scheme: StorageScheme = Field(
        ...,
        description="Storage backend type"
    )

    scheme_custom: str | None = Field(
        None,
        description="Custom scheme name when scheme=custom (e.g., 'minio', 'ceph')"
    )

    uri: str = Field(
        ...,
        description="Full URI to the artifact",
        examples=[
            "file:///data/output.txt",
            "s3://bucket/key.mp4",
            "gs://bucket/object.json",
            "https://example.com/file.pdf"
        ]
    )

    bucket: str | None = Field(
        None,
        description="Bucket name (for object storage schemes like s3, gcs, azure)"
    )

    key: str | None = Field(
        None,
        description="Object key/path within bucket"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Storage-specific metadata (region, credentials ref, etc.)"
    )

    @model_validator(mode='after')
    def validate_custom_scheme(self) -> 'StorageRef':
        """Ensure scheme_custom is provided when scheme is custom."""
        if self.scheme == StorageScheme.custom and not self.scheme_custom:
            raise ValueError(
                "scheme_custom must be specified when scheme=custom"
            )
        return self

    @model_validator(mode='after')
    def validate_uri_matches_scheme(self) -> 'StorageRef':
        """Basic validation that URI prefix matches declared scheme."""
        scheme_prefixes = {
            StorageScheme.local: ("file://",),
            StorageScheme.s3: ("s3://",),
            StorageScheme.gcs: ("gs://",),
            StorageScheme.azure: ("https://", "azure://"),
            StorageScheme.http: ("http://",),
            StorageScheme.https: ("https://",),
            StorageScheme.drive: ("drive://",),
            StorageScheme.ftp: ("ftp://",),
        }

        if self.scheme in scheme_prefixes:
            expected = scheme_prefixes[self.scheme]
            if not any(self.uri.startswith(prefix) for prefix in expected):
                raise ValueError(
                    f"URI '{self.uri}' does not match scheme '{self.scheme.value}'. "
                    f"Expected URI to start with one of: {expected}"
                )

        return self


class Checksum(BaseModel):
    """
    Checksum for artifact integrity verification.

    SHA256 is the blessed algorithm. For custom algorithms,
    use algorithm='custom' and specify the actual algorithm in
    the metadata dict.

    Stores the checksum value (pre-computed) - this model does NOT
    compute checksums, it only validates and stores them.
    """

    model_config = ConfigDict(extra="forbid")

    algorithm: ChecksumAlgorithm = Field(
        default=ChecksumAlgorithm.sha256,
        description="Hashing algorithm used (sha256 is blessed)"
    )

    algorithm_custom: str | None = Field(
        None,
        description="Custom algorithm name when algorithm=custom (e.g., 'blake2b', 'md5')"
    )

    value: str = Field(
        ...,
        description="Hex-encoded checksum value",
        examples=["a1b2c3d4e5f6...", "5d41402abc4b2a76b9719d911017c592"]
    )

    @field_validator("value")
    @classmethod
    def validate_hex_format(cls, v: str) -> str:
        """Ensure checksum value is valid hexadecimal."""
        try:
            int(v, 16)
        except ValueError:
            raise ValueError(f"Checksum value must be valid hexadecimal, got: {v}")
        return v.lower()

    @model_validator(mode='after')
    def validate_sha256_and_custom(self) -> 'Checksum':
        """
        Validate SHA256 checksums and enforce custom algorithm naming.
        """
        # If algorithm is sha256, validate length (64 hex chars)
        if self.algorithm == ChecksumAlgorithm.sha256:
            if len(self.value) != 64:
                raise ValueError(
                    f"SHA256 checksum must be 64 hex characters, got {len(self.value)}"
                )

        # If algorithm is custom, require algorithm_custom
        if self.algorithm == ChecksumAlgorithm.custom and not self.algorithm_custom:
            raise ValueError(
                "algorithm_custom must be specified when algorithm=custom"
            )

        return self


class ArtifactRef(BaseModel):
    """
    Reference to a single artifact produced or consumed by a capability.

    This is the fundamental unit of data flow in QuackCore. All artifacts
    (videos, transcripts, clips, reports) are referenced via ArtifactRef.

    Orchestrators (n8n, Temporal) route artifacts based on:
        - role: Semantic meaning (e.g., "transcript_txt", "video_slice_1")
        - kind: Purpose (intermediate, final, debug, report)
        - content_type: MIME type for format detection
        - tags: Additional routing hints

    Common Role Naming Convention:
        Use namespaced roles to avoid collisions across capability domains:
        - media.video_source: Original input video
        - media.video_slice_{n}: Nth extracted clip
        - media.transcript_txt: Plain text transcription
        - media.transcript_srt: SRT subtitle file
        - media.thumbnail_jpg: Preview thumbnail
        - text.summary_md: Markdown summary
        - text.entities_json: Extracted entities
        - crm.contacts_csv: Contact export

    Example:
        >>> artifact = ArtifactRef(
        ...     role="media.transcript_txt",
        ...     kind=ArtifactKind.final,
        ...     content_type="text/plain",
        ...     storage=StorageRef(
        ...         scheme=StorageScheme.local,
        ...         uri="file:///data/transcript.txt"
        ...     ),
        ...     size_bytes=1024,
        ...     tags={"language": "en", "model": "whisper-large"}
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "artifact_id": "550e8400-e29b-41d4-a716-446655440000",
                    "role": "media.transcript_txt",
                    "kind": "final",
                    "content_type": "text/plain",
                    "storage": {
                        "scheme": "local",
                        "uri": "file:///data/transcript.txt"
                    },
                    "size_bytes": 2048,
                    "checksum": {
                        "algorithm": "sha256",
                        "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                    },
                    "created_at": "2025-01-15T10:30:00Z",
                    "tags": {"language": "en"},
                    "metadata": {"word_count": 150}
                }
            ]
        }
    )

    artifact_id: str = Field(
        default_factory=generate_artifact_id,
        description="Unique identifier for this artifact"
    )

    role: ArtifactRole = Field(
        ...,
        description="Semantic role in workflow (e.g., media.transcript_txt, text.summary_md)",
        examples=["media.video_source", "media.transcript_txt", "text.summary_md", "crm.contacts_csv"]
    )

    kind: ArtifactKind = Field(
        ...,
        description="Classification for retention and routing"
    )

    content_type: str = Field(
        ...,
        description="MIME type of the artifact content",
        examples=["text/plain", "video/mp4", "application/json", "image/jpeg"]
    )

    storage: StorageRef = Field(
        ...,
        description="Where the artifact is stored"
    )

    size_bytes: int | None = Field(
        None,
        ge=0,
        description="Size of the artifact in bytes"
    )

    checksum: Checksum | None = Field(
        None,
        description="Checksum for integrity verification"
    )

    created_at: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when artifact was created"
    )

    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Additional routing/filtering metadata",
        examples=[{"language": "en"}, {"speaker": "Alice"}, {"quality": "high"}]
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form metadata (duration, resolution, etc.)"
    )

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id_format(cls, v: str) -> str:
        """Ensure artifact_id is a valid UUID."""
        if not is_valid_uuid(v):
            raise ValueError(f"artifact_id must be a valid UUID, got: {v}")
        return v

    @field_validator("role")
    @classmethod
    def validate_role_not_empty(cls, v: str) -> str:
        """Ensure role is not empty (required for routing)."""
        if not v or not v.strip():
            raise ValueError("role must not be empty")
        return v.strip()
