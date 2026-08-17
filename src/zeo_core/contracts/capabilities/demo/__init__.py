"""
Demo capabilities for testing and examples.

These are minimal demonstrations of the contract patterns.

NOTE: Demo implementations are NOT exported from this module.
They are internal examples only and should not be used in production.
See _impl.py for reference implementations (prefixed with _ to mark as internal).
"""

from zeo_core.contracts.capabilities.demo.models import (
    EchoRequest,
    VideoRefRequest,
)

# DO NOT export implementations - they are for reference/testing only
# from zeo_core.contracts.capabilities.demo._impl import (...)

__all__ = [
    # Models only - implementations are internal examples
    "EchoRequest",
    "VideoRefRequest",
]
