# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/envelopes/__init__.py
# === QV-LLM:END ===

"""
Envelope models for capability results, errors, and logs.

These models define the standard wrapper structure that ALL capabilities
use to return results. This enables machine branching and audit trails.
"""

from quack_core.contracts.envelopes.error import CapabilityError
from quack_core.contracts.envelopes.log import CapabilityLogEvent
from quack_core.contracts.envelopes.result import CapabilityResult

__all__ = [
    "CapabilityResult",
    "CapabilityError",
    "CapabilityLogEvent",
]
