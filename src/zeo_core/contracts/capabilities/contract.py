"""
DEPRECATED: Import from zeo_core.contracts instead.

This module is a temporary compatibility shim to allow gradual migration.
It will be removed in a future version.

New code should use:
    from zeo_core.contracts import CapabilityResult, CapabilityError, ...

Instead of:
    from zeo_core.contracts.capabilities.contract import CapabilityResult, ...
"""

# Re-export from new canonical locations
from zeo_core.contracts.common import (
    CapabilityStatus,
    LogLevel,
)
from zeo_core.contracts.envelopes import (
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
