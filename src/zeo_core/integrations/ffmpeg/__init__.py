"""
FFmpeg integration for zeo_core.

This package provides an integration for media probing and rendering/transcoding,
wrapping the org's own `ffmpeg-zeo` PyPI package
(github.com/zeroemployeeorg/ffmpeg-zeo) rather than the raw ffmpeg binary
directly -- `ffmpeg-zeo` already owns typed filter-graph construction, binary
discovery, and subprocess execution; this integration adapts its API onto
zeocore's `IntegrationProtocol`/`IntegrationResult` conventions.
"""

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.ffmpeg.config import FFmpegConfig, FFmpegConfigProvider
from zeo_core.integrations.ffmpeg.models import RenderMetrics
from zeo_core.integrations.ffmpeg.service import FFmpegIntegration

__all__ = [
    # Main integration class
    "FFmpegIntegration",
    # Configuration
    "FFmpegConfig",
    "FFmpegConfigProvider",
    # Models
    "RenderMetrics",
    # Factory function for integration discovery
    "create_integration",
]


def create_integration() -> IntegrationProtocol:
    """
    Create and return an FFmpeg integration instance.

    This function is used as an entry point for automatic integration discovery.

    Returns:
        IntegrationProtocol: Configured FFmpeg integration
    """
    return FFmpegIntegration()
