"""
Capability request/response contracts.

This module defines the API schemas for all QuackCore capabilities.
Implementations live in Ring B (quack_core.tools), not here.
"""

# Media capabilities
# Demo capabilities (models only - implementations are examples, not exported)
from quack_core.contracts.capabilities.demo.models import (
    EchoRequest,
    VideoRefRequest,
)

"""
from quack_core.contracts.capabilities.media import (
    SlicedClipData,
    SliceVideoRequest,
    SliceVideoResponse,
    TimeRange,
    TranscribeRequest,
    TranscribeResponse,
    TranscriptionSegment,
)
"""
__all__ = [
    # Media
    # "TimeRange",
    # "SliceVideoRequest",
    # "SlicedClipData",
    # "SliceVideoResponse",
    # "TranscribeRequest",
    # "TranscriptionSegment",
    # "TranscribeResponse",
    # Demo (models only)
    "EchoRequest",
    "VideoRefRequest",
]
