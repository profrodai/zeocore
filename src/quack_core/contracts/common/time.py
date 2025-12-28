# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/time.py
# module: quack_core.contracts.common.time
# role: module
# neighbors: __init__.py, enums.py, ids.py, typing.py, versions.py
# exports: utcnow, utcnow_iso
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
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
    Get current time as ISO 8601 formatted string.

    Returns:
        ISO 8601 timestamp string with UTC timezone

    Example:
        >>> ts = utcnow_iso()
        >>> 'T' in ts and 'Z' in ts or '+00:00' in ts
        True
    """
    return utcnow().isoformat()