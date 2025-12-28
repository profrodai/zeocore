# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_contracts/test_artifacts.py
# role: tests
# neighbors: __init__.py, test_capabilities.py, test_dependency_boundaries.py, test_envelopes.py
# exports: TestStorageRef, TestChecksum, TestArtifactRef, TestRunManifest, TestManifestFixtures
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
Tests for artifact models (ArtifactRef, StorageRef, RunManifest).

Validates invariants, time ordering, and JSON fixtures.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from quack_core.contracts import (
    StorageRef,
    Checksum,
    ArtifactRef,
    ToolInfo,
    Provenance,
    ManifestInput,
    RunManifest,
    StorageScheme,
    ArtifactKind,
    ChecksumAlgorithm,
    CapabilityStatus,
    CapabilityError,
    CapabilityLogEvent,
    LogLevel,
)


class TestStorageRef:
    """Tests for StorageRef model."""

    def test_local_storage_ref(self):
        """Test creating a local file reference."""
        ref = StorageRef(
            scheme=StorageScheme.local,
            uri="file:///data/video.mp4"
        )

        assert ref.scheme == StorageScheme.local
        assert ref.uri == "file:///data/video.mp4"

    def test_s3_storage_ref(self):
        """Test creating an S3 reference."""
        ref = StorageRef(
            scheme=StorageScheme.s3,
            uri="s3://my-bucket/path/to/file.mp4",
            bucket="my-bucket",
            key="path/to/file.mp4",
            metadata={"region": "us-east-1"}
        )

        assert ref.scheme == StorageScheme.s3
        assert ref.bucket == "my-bucket"
        assert ref.key == "path/to/file.mp4"
        assert ref.metadata["region"] == "us-east-1"

    def test_custom_storage_scheme(self):
        """Test using a custom storage scheme."""
        ref = StorageRef(
            scheme=StorageScheme.custom,
            scheme_custom="minio",
            uri="minio://my-bucket/file.mp4",
            metadata={"endpoint": "minio.example.com:9000"}
        )

        assert ref.scheme == StorageScheme.custom
        assert ref.scheme_custom == "minio"
        assert ref.metadata["endpoint"] == "minio.example.com:9000"

    def test_custom_scheme_requires_scheme_custom(self):
        """Test that custom scheme requires scheme_custom field."""
        with pytest.raises(ValidationError) as exc_info:
            StorageRef(
                scheme=StorageScheme.custom,
                uri="custom://my-bucket/file.mp4"
                # Missing scheme_custom
            )

        assert "scheme_custom" in str(exc_info.value).lower()


class TestChecksum:
    """Tests for Checksum model."""

    def test_valid_checksum(self):
        """Test creating a valid checksum."""
        checksum = Checksum(
            algorithm=ChecksumAlgorithm.sha256,
            value="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014"
        )

        assert checksum.algorithm == ChecksumAlgorithm.sha256
        assert checksum.value == "1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014"

    def test_checksum_lowercase_normalization(self):
        """Test that checksum values are normalized to lowercase."""
        checksum = Checksum(
            algorithm=ChecksumAlgorithm.sha256,
            value="1B4F0E9851971998E732078544C96B36C3D01CEDF7CAA332359D6F1D83567014"
        )

        assert checksum.value == "1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014"

    def test_invalid_checksum_hex(self):
        """Test that invalid hex values are rejected."""
        with pytest.raises(ValidationError):
            Checksum(
                algorithm=ChecksumAlgorithm.sha256,
                value="not-a-hex-value-" + "0" * 48  # Need 64 chars total
            )

    def test_sha256_length_validation(self):
        """Test that SHA256 checksums must be exactly 64 hex characters."""
        # Too short
        with pytest.raises(ValidationError) as exc_info:
            Checksum(
                algorithm=ChecksumAlgorithm.sha256,
                value="abc123"
            )
        assert "64 hex characters" in str(exc_info.value).lower()

        # Too long
        with pytest.raises(ValidationError):
            Checksum(
                algorithm=ChecksumAlgorithm.sha256,
                value="a" * 65
            )

    def test_custom_checksum_algorithm(self):
        """Test using a custom checksum algorithm."""
        checksum = Checksum(
            algorithm=ChecksumAlgorithm.custom,
            algorithm_custom="blake2b",
            value="abcd1234"  # Custom algorithms don't enforce length
        )

        assert checksum.algorithm == ChecksumAlgorithm.custom
        assert checksum.algorithm_custom == "blake2b"

    def test_custom_algorithm_requires_algorithm_custom(self):
        """Test that custom algorithm requires algorithm_custom field."""
        with pytest.raises(ValidationError) as exc_info:
            Checksum(
                algorithm=ChecksumAlgorithm.custom,
                value="abcd1234"
                # Missing algorithm_custom
            )

        assert "algorithm_custom" in str(exc_info.value).lower()


class TestArtifactRef:
    """Tests for ArtifactRef model."""

    def test_basic_artifact_ref(self):
        """Test creating a basic artifact reference."""
        artifact = ArtifactRef(
            role="transcript_txt",
            kind=ArtifactKind.final,
            content_type="text/plain",
            storage=StorageRef(
                scheme=StorageScheme.local,
                uri="file:///data/transcript.txt"
            )
        )

        assert artifact.role == "transcript_txt"
        assert artifact.kind == ArtifactKind.final
        assert artifact.content_type == "text/plain"
        assert len(artifact.artifact_id) == 36  # UUID format

    def test_artifact_with_checksum(self):
        """Test artifact with checksum."""
        artifact = ArtifactRef(
            role="video_slice_1",
            kind=ArtifactKind.final,
            content_type="video/mp4",
            storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/clip.mp4"),
            size_bytes=1024,
            checksum=Checksum(
                algorithm=ChecksumAlgorithm.sha256,
                value="60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752"
            )
        )

        assert artifact.size_bytes == 1024
        assert artifact.checksum.value == "60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752"

    def test_artifact_with_tags(self):
        """Test artifact with routing tags."""
        artifact = ArtifactRef(
            role="transcript_txt",
            kind=ArtifactKind.final,
            content_type="text/plain",
            storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/t.txt"),
            tags={"language": "en", "speaker_count": "2"}
        )

        assert artifact.tags["language"] == "en"
        assert artifact.tags["speaker_count"] == "2"

    def test_role_required(self):
        """Test that role is required and not empty."""
        with pytest.raises(ValidationError):
            ArtifactRef(
                role="",  # Empty role
                kind=ArtifactKind.final,
                content_type="text/plain",
                storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/f.txt")
            )

    def test_artifact_id_must_be_uuid(self):
        """Test that artifact_id must be a valid UUID."""
        with pytest.raises(ValidationError):
            ArtifactRef(
                artifact_id="not-a-uuid",
                role="test",
                kind=ArtifactKind.final,
                content_type="text/plain",
                storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/f.txt")
            )


class TestRunManifest:
    """Tests for RunManifest model."""

    def test_basic_manifest(self):
        """Test creating a basic run manifest."""
        manifest = RunManifest(
            tool=ToolInfo(name="slice_video", version="1.0.0"),
            status=CapabilityStatus.success
        )

        assert manifest.tool.name == "slice_video"
        assert manifest.status == CapabilityStatus.success
        assert len(manifest.run_id) == 36  # UUID format

    def test_manifest_with_artifacts(self):
        """Test manifest with input and output artifacts."""
        input_artifact = ArtifactRef(
            role="video_source",
            kind=ArtifactKind.intermediate,
            content_type="video/mp4",
            storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/in.mp4")
        )

        output_artifact = ArtifactRef(
            role="video_slice_1",
            kind=ArtifactKind.final,
            content_type="video/mp4",
            storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/out.mp4")
        )

        manifest = RunManifest(
            tool=ToolInfo(name="slice_video", version="1.0.0"),
            status=CapabilityStatus.success,
            inputs=[
                ManifestInput(
                    name="source_video",
                    artifact=input_artifact,
                    required=True
                )
            ],
            outputs=[output_artifact]
        )

        assert len(manifest.inputs) == 1
        assert len(manifest.outputs) == 1
        assert manifest.inputs[0].artifact.role == "video_source"
        assert manifest.outputs[0].role == "video_slice_1"

    def test_manifest_timing_consistency(self):
        """Test that manifest validates time ordering."""
        started = datetime.now(timezone.utc)
        finished = started + timedelta(seconds=45)

        manifest = RunManifest(
            tool=ToolInfo(name="test", version="1.0.0"),
            status=CapabilityStatus.success,
            started_at=started,
            finished_at=finished,
            duration_sec=45.0
        )

        assert manifest.finished_at > manifest.started_at

    def test_manifest_invalid_time_order(self):
        """Test that finished_at must be >= started_at."""
        started = datetime.now(timezone.utc)
        finished = started - timedelta(seconds=10)  # Finished before started!

        with pytest.raises(ValidationError) as exc_info:
            RunManifest(
                tool=ToolInfo(name="test", version="1.0.0"),
                status=CapabilityStatus.success,
                started_at=started,
                finished_at=finished
            )

        assert "finished_at" in str(exc_info.value).lower()

    def test_manifest_duration_mismatch(self):
        """Test that duration_sec must match timestamps."""
        started = datetime.now(timezone.utc)
        finished = started + timedelta(seconds=45)

        with pytest.raises(ValidationError) as exc_info:
            RunManifest(
                tool=ToolInfo(name="test", version="1.0.0"),
                status=CapabilityStatus.success,
                started_at=started,
                finished_at=finished,
                duration_sec=100.0  # Doesn't match 45 seconds
            )

        assert "duration_sec" in str(exc_info.value).lower()

    def test_manifest_error_requires_error_field(self):
        """Test that error status requires error field."""
        with pytest.raises(ValidationError) as exc_info:
            RunManifest(
                tool=ToolInfo(name="test", version="1.0.0"),
                status=CapabilityStatus.error
                # Missing error field
            )

        assert "error" in str(exc_info.value).lower()

    def test_manifest_with_provenance(self):
        """Test manifest with provenance information."""
        manifest = RunManifest(
            tool=ToolInfo(name="test", version="1.0.0"),
            status=CapabilityStatus.success,
            provenance=Provenance(
                git_commit="abc123",
                git_branch="main",
                environment="prod",
                runner="n8n"
            )
        )

        assert manifest.provenance.git_commit == "abc123"
        assert manifest.provenance.runner == "n8n"


class TestManifestFixtures:
    """Tests that validate JSON fixtures load correctly."""

    @pytest.fixture
    def fixtures_dir(self):
        """Get path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_load_manifest_success_fixture(self, fixtures_dir):
        """Test loading the success manifest fixture."""
        fixture_path = fixtures_dir / "manifest_success.json"

        with open(fixture_path) as f:
            data = json.load(f)

        manifest = RunManifest.model_validate(data)

        assert manifest.status == CapabilityStatus.success
        assert manifest.tool.name == "slice_video"
        assert len(manifest.outputs) == 2
        assert manifest.provenance.runner == "n8n"

    def test_load_manifest_error_fixture(self, fixtures_dir):
        """Test loading the error manifest fixture."""
        fixture_path = fixtures_dir / "manifest_error.json"

        with open(fixture_path) as f:
            data = json.load(f)

        manifest = RunManifest.model_validate(data)

        assert manifest.status == CapabilityStatus.error
        assert manifest.error is not None
        assert manifest.error.code == "QC_IO_DECODE_ERROR"
        assert len(manifest.outputs) == 0

    def test_load_artifact_local_fixture(self, fixtures_dir):
        """Test loading the local artifact fixture."""
        fixture_path = fixtures_dir / "artifact_ref_local.json"

        with open(fixture_path) as f:
            data = json.load(f)

        artifact = ArtifactRef.model_validate(data)

        assert artifact.role == "transcript_txt"
        assert artifact.storage.scheme == StorageScheme.local
        assert artifact.tags["language"] == "en"

    def test_load_artifact_s3_fixture(self, fixtures_dir):
        """Test loading the S3 artifact fixture."""
        fixture_path = fixtures_dir / "artifact_ref_s3.json"

        with open(fixture_path) as f:
            data = json.load(f)

        artifact = ArtifactRef.model_validate(data)

        assert artifact.role == "video_slice_1"
        assert artifact.storage.scheme == StorageScheme.s3
        assert artifact.storage.bucket == "quack-artifacts-prod"
        assert artifact.tags["quality"] == "1080p"