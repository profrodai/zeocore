"""
Envelope models for capability results, errors, and logs.

These models define the standard wrapper structure that ALL capabilities
use to return results. This enables machine branching and audit trails.
"""

from zeo_core.contracts.envelopes.error import CapabilityError
from zeo_core.contracts.envelopes.log import CapabilityLogEvent
from zeo_core.contracts.envelopes.result import CapabilityResult

__all__ = [
    "CapabilityResult",
    "CapabilityError",
    "CapabilityLogEvent",
]
