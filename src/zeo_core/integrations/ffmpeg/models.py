"""
Data models for the ffmpeg integration.

`ffmpeg-zeo` already ships well-typed Pydantic/dataclass models for its own
domain (`ffmpeg_zeo.ProbeResult`, `ffmpeg_zeo.RunResult`, `ffmpeg_zeo.Progress`).
This module deliberately does NOT re-wrap them -- FFmpegIntegration returns
plain dicts derived from those models inside `IntegrationResult.content` so
callers get zeocore's own envelope without a second, competing set of media
models to keep in sync with upstream. `RenderMetrics` below is the one model
genuinely specific to this wrapper (mirrors pandoc's `ConversionMetrics`).
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RenderMetrics(BaseModel):
    """Metrics for ffmpeg render/transcode operations."""

    start_time: datetime = Field(
        default_factory=datetime.now,
        description="Time when metrics collection started",
    )
    total_attempts: int = Field(
        default=0, description="Total number of render attempts"
    )
    successful_renders: int = Field(
        default=0, description="Number of successful renders"
    )
    failed_renders: int = Field(default=0, description="Number of failed renders")
    errors: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary mapping input paths to error messages",
    )
