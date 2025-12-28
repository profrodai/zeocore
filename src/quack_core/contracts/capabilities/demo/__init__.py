# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capabilities/demo/__init__.py
# module: quack_core.contracts.capabilities.demo.__init__
# role: module
# neighbors: models.py, impl.py
# exports: EchoRequest, VideoRefRequest, echo_text, validate_video_ref
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
Demo capabilities for testing and examples.

These are minimal demonstrations of the contract patterns.
"""

from quack_core.contracts.capabilities.demo.models import (
    EchoRequest,
    VideoRefRequest,
)
from quack_core.contracts.capabilities.demo.impl import (
    echo_text,
    validate_video_ref,
)

__all__ = [
    # Models
    "EchoRequest",
    "VideoRefRequest",
    # Implementations (optional)
    "echo_text",
    "validate_video_ref",
]