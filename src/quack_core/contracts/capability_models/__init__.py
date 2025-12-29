# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capability_models/__init__.py
# module: quack_core.contracts.capability_models.__init__
# role: module
# neighbors: contract.py
# exports: TimeRange, SliceVideoRequest, SlicedClipData, SliceVideoResponse, TranscribeRequest, TranscriptionSegment, TranscribeResponse, EchoRequest (+1 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""
Capability request/response contracts.

This module defines the API schemas for all QuackCore capability_models.
Implementations live in Ring B (quack_core.capabilities), not here.
"""

# Media capability_models
from quack_core.contracts.capability_models.media import (
    TimeRange,
    SliceVideoRequest,
    SlicedClipData,
    SliceVideoResponse,
    TranscribeRequest,
    TranscriptionSegment,
    TranscribeResponse,
)

# Demo capability_models (models only - implementations are examples, not exported)
from quack_core.contracts.capability_models.demo.models import (
    EchoRequest,
    VideoRefRequest,
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
    # Demo (models only)
    "EchoRequest",
    "VideoRefRequest",
]