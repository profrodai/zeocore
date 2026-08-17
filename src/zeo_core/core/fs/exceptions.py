"""
Filesystem-specific exceptions for ZeoCore.
"""


class ZeoFileSystemError(Exception):
    """Base class for filesystem errors."""

    pass


class ZeoPathSecurityError(ZeoFileSystemError, ValueError):
    """Base class for path security violations."""

    pass


class ZeoPathEscapeError(ZeoPathSecurityError):
    """Raised when a path attempts to traverse above the base directory
    (e.g. via '..')."""

    pass


class ZeoPathOutsideBaseDirError(ZeoPathSecurityError):
    """Raised when an absolute path is outside the configured base directory."""

    pass
