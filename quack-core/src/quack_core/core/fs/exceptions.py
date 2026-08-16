# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/exceptions.py
# === QV-LLM:END ===

"""
Filesystem-specific exceptions for QuackCore.
"""


class QuackFileSystemError(Exception):
    """Base class for filesystem errors."""

    pass


class QuackPathSecurityError(QuackFileSystemError, ValueError):
    """Base class for path security violations."""

    pass


class QuackPathEscapeError(QuackPathSecurityError):
    """Raised when a path attempts to traverse above the base directory (e.g. via '..')."""

    pass


class QuackPathOutsideBaseDirError(QuackPathSecurityError):
    """Raised when an absolute path is outside the configured base directory."""

    pass
