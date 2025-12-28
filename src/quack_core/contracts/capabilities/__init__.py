# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capabilities/__init__.py
# module: quack_core.contracts.capabilities.__init__
# role: module
# neighbors: contract.py, demo.py
# exports: TimeRange, SliceVideoRequest, SlicedClipData, SliceVideoResponse, TranscribeRequest, TranscriptionSegment, TranscribeResponse, EchoRequest (+3 more)
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
Capability request/response contracts.

This module defines the API schemas for all QuackCore capabilities.
Implementations live in Ring B (quack_core.toolkit), not here.
"""

# Media capabilities
from quack_core.contracts.capabilities.media import (
    TimeRange,
    SliceVideoRequest,
    SlicedClipData,
    SliceVideoResponse,
    TranscribeRequest,
    TranscriptionSegment,
    TranscribeResponse,
)

# Demo capabilities
from quack_core.contracts.capabilities.demo import (
    EchoRequest,
    VideoRefRequest,
    echo_text,
    validate_video_ref,
)

__all__ = [
    # Media
    "TimeRange",
    "SliceVideoRequest",
    "SlicedClipData",
    "SliceVideoResponse",
    "TranscribeRequest",
    "TranscriptionSegment",
    "TranscribeResponse",
    # Demo
    "EchoRequest",
    "VideoRefRequest",
    "echo_text",
    "validate_video_ref",
]