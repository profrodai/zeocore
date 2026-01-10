# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_contracts/test_capabilities.py
# role: tests
# neighbors: __init__.py, test_artifacts.py, test_dependency_boundaries.py, test_envelopes.py, test_schema_examples.py
# exports: TestTimeRange, TestSliceVideoModels, TestTranscribeModels, TestDemoCapabilities
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===

"""
Tests for capability models (media, demo).

Validates request/response schemas and demo implementations.
"""

import pytest
from pydantic import ValidationError
from quack_core.contracts import (
    ArtifactKind,
    # Supporting types
    ArtifactRef,
    CapabilityStatus,
    # Demo (models only)
    EchoRequest,
    SlicedClipData,
    SliceVideoRequest,
    SliceVideoResponse,
    StorageRef,
    StorageScheme,
    # Media
    TimeRange,
    TranscribeRequest,
    TranscribeResponse,
    TranscriptionSegment,
    VideoRefRequest,
)

# Import demo implementations directly from their INTERNAL module
# NOTE: Using underscore-prefixed module to access internal examples
from quack_core.contracts.capabilities.demo._impl import (
    echo_text,
    validate_video_ref,
)


class TestTimeRange:
    """Tests for TimeRange model."""

    def test_valid_time_range(self):
        """Test creating a valid time range."""
        tr = TimeRange(start_sec=0, end_sec=30, label="Intro")

        assert tr.start_sec == 0
        assert tr.end_sec == 30
        assert tr.label == "Intro"

    def test_invalid_time_order(self):
        """Test that end_sec must be > start_sec."""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(start_sec=30, end_sec=10)

        assert "greater than" in str(exc_info.value).lower()

    def test_equal_times_invalid(self):
        """Test that equal start and end times are invalid."""
        with pytest.raises(ValidationError):
            TimeRange(start_sec=10, end_sec=10)


class TestSliceVideoModels:
    """Tests for SliceVideo capability models."""

    def test_slice_video_request(self):
        """Test creating a slice video request."""
        source = ArtifactRef(
            role="video_source",
            kind=ArtifactKind.intermediate,
            content_type="video/mp4",
            storage=StorageRef(
                scheme=StorageScheme.local,
                uri="file:///data/input.mp4"
            )
        )

        request = SliceVideoRequest(
            source=source,
            clips=[
                TimeRange(start_sec=0, end_sec=30),
                TimeRange(start_sec=60, end_sec=90)
            ]
        )

        assert len(request.clips) == 2
        assert request.source.role == "video_source"

    def test_slice_video_request_with_options(self):
        """Test slice request with configuration options."""
        source = ArtifactRef(
            role="video_source",
            kind=ArtifactKind.intermediate,
            content_type="video/mp4",
            storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/in.mp4")
        )

        request = SliceVideoRequest(
            source=source,
            clips=[TimeRange(start_sec=0, end_sec=10)],
            preset="fast",
            output_format="webm",
            re_encode=True
        )

        assert request.preset == "fast"
        assert request.output_format == "webm"
        assert request.re_encode is True

    def test_sliced_clip_data(self):
        """Test SlicedClipData model."""
        artifact = ArtifactRef(
            role="video_slice_1",
            kind=ArtifactKind.final,
            content_type="video/mp4",
            storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/clip.mp4")
        )

        clip = SlicedClipData(
            artifact=artifact,
            duration_sec=30.0,
            original_range=TimeRange(start_sec=0, end_sec=30)
        )

        assert clip.duration_sec == 30.0
        assert clip.artifact.role == "video_slice_1"

    def test_slice_video_response(self):
        """Test SliceVideoResponse model."""
        clip_artifact = ArtifactRef(
            role="video_slice_1",
            kind=ArtifactKind.final,
            content_type="video/mp4",
            storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/clip.mp4")
        )

        response = SliceVideoResponse(
            generated_clips=[
                SlicedClipData(
                    artifact=clip_artifact,
                    duration_sec=30.0,
                    original_range=TimeRange(start_sec=0, end_sec=30)
                )
            ],
            metadata={"preset": "fast"}
        )

        assert len(response.generated_clips) == 1
        assert response.metadata["preset"] == "fast"


class TestTranscribeModels:
    """Tests for Transcribe capability models."""

    def test_transcribe_request(self):
        """Test creating a transcribe request."""
        source = ArtifactRef(
            role="video_source",
            kind=ArtifactKind.intermediate,
            content_type="video/mp4",
            storage=StorageRef(scheme=StorageScheme.local, uri="file:///data/video.mp4")
        )

        request = TranscribeRequest(
            source=source,
            language="en",
            detect_speakers=True
        )

        assert request.source.role == "video_source"
        assert request.language == "en"
        assert request.detect_speakers is True

    def test_transcription_segment(self):
        """Test TranscriptionSegment model."""
        segment = TranscriptionSegment(
            start=0.0,
            end=5.2,
            text="Hello, world!",
            speaker="Speaker 1",
            confidence=0.95
        )

        assert segment.text == "Hello, world!"
        assert segment.speaker == "Speaker 1"
        assert segment.confidence == 0.95

    def test_transcribe_response(self):
        """Test TranscribeResponse model."""
        response = TranscribeResponse(
            full_text="Hello, world! This is a test.",
            segments=[
                TranscriptionSegment(
                    start=0.0,
                    end=5.0,
                    text="Hello, world!"
                ),
                TranscriptionSegment(
                    start=5.0,
                    end=8.5,
                    text="This is a test."
                )
            ],
            detected_language="en",
            word_count=6,
            metadata={"model": "whisper-large-v3"}
        )

        assert response.word_count == 6
        assert len(response.segments) == 2
        assert response.detected_language == "en"


class TestDemoCapabilities:
    """
    Tests for demo capability implementations.

    NOTE: These test internal example implementations that are not part
    of the public API. They demonstrate contract usage patterns only.
    """

    def test_echo_text_basic(self):
        """Test basic echo functionality."""
        request = EchoRequest(text="World")
        result = echo_text(request)

        assert result.status == CapabilityStatus.success
        assert result.data == "Hello World"

    def test_echo_text_custom_greeting(self):
        """Test echo with custom greeting."""
        request = EchoRequest(
            text="QuackCore",
            override_greeting="Welcome to"
        )
        result = echo_text(request)

        assert result.data == "Welcome to QuackCore"
        assert result.metadata["greeting"] == "Welcome to"

    def test_validate_video_ref_supported(self):
        """Test video ref validation with supported provider."""
        request = VideoRefRequest(url="https://youtube.com/watch?v=abc123")
        result = validate_video_ref(request)

        assert result.status == CapabilityStatus.success
        assert result.data is True

    def test_validate_video_ref_unsupported(self):
        """Test video ref validation with unsupported provider."""
        request = VideoRefRequest(url="https://example.com/video.mp4")
        result = validate_video_ref(request)

        assert result.status == CapabilityStatus.skipped
        assert result.machine_message == "QC_VAL_UNSUPPORTED_PROVIDER"
        assert "not from a supported provider" in result.human_message
