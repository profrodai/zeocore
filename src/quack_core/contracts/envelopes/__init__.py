# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/envelopes/__init__.py
# module: quack_core.contracts.envelopes.__init__
# role: module
# neighbors: error.py, log.py, result.py
# exports: CapabilityResult, CapabilityError, CapabilityLogEvent
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""
Envelope models for capability results, errors, and logs.

These models define the standard wrapper structure that ALL capabilities
use to return results. This enables machine branching and audit trails.
"""

from quack_core.contracts.envelopes.result import CapabilityResult
from quack_core.contracts.envelopes.error import CapabilityError
from quack_core.contracts.envelopes.log import CapabilityLogEvent

__all__ = [
    "CapabilityResult",
    "CapabilityError",
    "CapabilityLogEvent",
]