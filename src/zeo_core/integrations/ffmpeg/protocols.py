"""
Protocol definitions for the ffmpeg integration.

Mirrors `zeo_core.integrations.pandoc.protocols`'s shape: a `runtime_checkable`
Protocol for the main media operations this integration exposes, expressed over
`IntegrationResult` so callers get the same error-handling envelope as every
other zeocore integration.
"""

from typing import Any, Protocol, runtime_checkable

from zeo_core.integrations.core.results import IntegrationResult


@runtime_checkable
class MediaProbeProtocol(Protocol):
    """Protocol for media inspection (ffprobe) operations."""

    def probe(self, input_path: str) -> IntegrationResult[dict[str, Any]]:
        """
        Inspect a media file and return its format/stream metadata.

        Args:
            input_path: Path to the media file to inspect.

        Returns:
            IntegrationResult[dict[str, Any]]: Result containing the probed
            metadata (duration, streams, codecs, etc.) as a plain dict.
        """
        ...


@runtime_checkable
class MediaConversionProtocol(Protocol):
    """Protocol for the main ffmpeg render/transcode operations."""

    def convert(
        self, input_path: str, output_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Convert a media file to the format implied by `output_path`'s extension.

        Args:
            input_path: Path to the source media file.
            output_path: Optional destination path.

        Returns:
            IntegrationResult[str]: Result containing the output file path.
        """
        ...

    def transcode_h264(
        self,
        input_path: str,
        output_path: str | None = None,
        *,
        crf: int = 23,
        preset: str = "medium",
    ) -> IntegrationResult[str]:
        """
        Transcode a video to H.264/AAC.

        Args:
            input_path: Path to the source video file.
            output_path: Optional destination path.
            crf: Constant rate factor (lower is higher quality).
            preset: x264 encoder preset.

        Returns:
            IntegrationResult[str]: Result containing the output file path.
        """
        ...

    def extract_audio(
        self, input_path: str, output_path: str | None = None, *, codec: str = "copy"
    ) -> IntegrationResult[str]:
        """
        Extract the audio track from a media file.

        Args:
            input_path: Path to the source media file.
            output_path: Optional destination path.
            codec: Audio codec to encode with, or "copy" for a stream copy.

        Returns:
            IntegrationResult[str]: Result containing the output file path.
        """
        ...

    def thumbnail(
        self, input_path: str, output_path: str | None = None, *, time: float = 1.0
    ) -> IntegrationResult[str]:
        """
        Extract a single-frame thumbnail from a video.

        Args:
            input_path: Path to the source video file.
            output_path: Optional destination path.
            time: Timestamp in seconds to grab the frame from.

        Returns:
            IntegrationResult[str]: Result containing the output file path.
        """
        ...
