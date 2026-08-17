"""
Tests for capability models (demo).

Validates demo request/response schemas and demo implementations.

NOTE: This file previously also covered a "media" capability surface
(TimeRange, SliceVideoRequest, SlicedClipData, SliceVideoResponse,
TranscribeRequest, TranscriptionSegment, TranscribeResponse) imported from
`quack_core.contracts`. That surface was never implemented: no
`quack_core.contracts.capabilities.media` module has ever existed in this
repo's history (`capabilities/__init__.py` has always imported it inside a
commented-out block, and `contracts/__init__.py`'s own `__all__` never
declared the names stable). The video-processing functionality the names
describe (`slice_video`, `probe`, `extract_frames`, ...) lives in the
separate `quackmedia` library (see `docs/legacy/quackmedia-video.md`), not
in `quack_core.contracts`. Per RULING-118's standard (retire speculative
test coverage for a module that was never built rather than build stub
models solely to satisfy a test), the media test classes were removed
here. If a real Capability/Tool wraps quackmedia through
`quack_core.contracts.capabilities.media` in the future, that integration
is where new coverage for these models should start.
"""

from quack_core.contracts import CapabilityStatus, EchoRequest, VideoRefRequest

# Import demo implementations directly from their INTERNAL module
# NOTE: Using underscore-prefixed module to access internal examples
from quack_core.contracts.capabilities.demo._impl import (
    echo_text,
    validate_video_ref,
)


class TestDemoCapabilities:
    """
    Tests for demo capability implementations.

    NOTE: These test internal example implementations that are not part
    of the public API. They demonstrate contract usage patterns only.
    """

    def test_echo_text_basic(self) -> None:
        """Test basic echo functionality."""
        request = EchoRequest(text="World")
        result = echo_text(request)

        assert result.status == CapabilityStatus.success
        assert result.data == "Hello World"

    def test_echo_text_custom_greeting(self) -> None:
        """Test echo with custom greeting."""
        request = EchoRequest(text="QuackCore", override_greeting="Welcome to")
        result = echo_text(request)

        assert result.data == "Welcome to QuackCore"
        assert result.metadata["greeting"] == "Welcome to"

    def test_validate_video_ref_supported(self) -> None:
        """Test video ref validation with supported provider."""
        request = VideoRefRequest(url="https://youtube.com/watch?v=abc123")
        result = validate_video_ref(request)

        assert result.status == CapabilityStatus.success
        assert result.data is True

    def test_validate_video_ref_unsupported(self) -> None:
        """Test video ref validation with unsupported provider."""
        request = VideoRefRequest(url="https://example.com/video.mp4")
        result = validate_video_ref(request)

        assert result.status == CapabilityStatus.skipped
        assert result.machine_message == "QC_VAL_UNSUPPORTED_PROVIDER"
        assert "not from a supported provider" in result.human_message
