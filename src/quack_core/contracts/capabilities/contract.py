# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capabilities/contract.py
# module: quack_core.contracts.capabilities.contract
# role: module
# neighbors: __init__.py
# exports: CapabilityStatus, LogLevel, CapabilityLogEvent, CapabilityError, CapabilityResult
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""
DEPRECATED: Import from quack_core.contracts instead.

This module is a temporary compatibility shim to allow gradual migration.
It will be removed in a future version.

New code should use:
    from quack_core.contracts import CapabilityResult, CapabilityError, ...

Instead of:
    from quack_core.contracts.capabilities.contract import CapabilityResult, ...
"""

# Re-export from new canonical locations
from quack_core.contracts.common import (
    CapabilityStatus,
    LogLevel,
)
from quack_core.contracts.envelopes import (
    CapabilityError,
    CapabilityLogEvent,
    CapabilityResult,
)

__all__ = [
    "CapabilityStatus",
    "LogLevel",
    "CapabilityLogEvent",
    "CapabilityError",
    "CapabilityResult",
]

# Note: DeprecationWarning is documented in docstring but not emitted at runtime
# to avoid noise during migration period. The import will work but code reviewers
# should be encouraged to update imports to the new location.
