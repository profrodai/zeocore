# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/time.py
# module: quack_core.contracts.common.time
# role: module
# neighbors: __init__.py, enums.py, ids.py, typing.py, versions.py
# exports: utcnow, utcnow_iso
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
Time utilities for contracts.

Provides standardized UTC timestamp generation.
All contracts use UTC to avoid timezone ambiguity.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Get current time in UTC with timezone awareness.

    Returns:
        Timezone-aware datetime in UTC

    Example:
        >>> ts = utcnow()
        >>> ts.tzinfo == timezone.utc
        True
    """
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    """
    Get current time as ISO 8601 formatted string with Z suffix.

    Returns:
        ISO 8601 timestamp string with Z timezone indicator (normalized format)

    Example:
        >>> ts = utcnow_iso()
        >>> ts.endswith('Z')
        True
    """
    # Use replace to normalize +00:00 to Z for consistency
    return utcnow().isoformat().replace('+00:00', 'Z')
