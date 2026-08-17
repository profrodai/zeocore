"""
Error handling utilities for zeo_core.

This module provides custom exception classes for ZeoCore, with helpful context
and error messages for better diagnostics and troubleshooting.
"""

from zeo_core.core.errors.base import (
    ZeoBaseAuthError,
    ZeoConfigurationError,
    ZeoError,
    ZeoFileExistsError,
    ZeoFileNotFoundError,
    ZeoFormatError,
    ZeoIOError,
    ZeoPermissionError,
    ZeoPluginError,
    ZeoValidationError,
    wrap_io_errors,
)
from zeo_core.core.errors.integration import (
    ZeoApiError,
    ZeoAuthenticationError,
    ZeoIntegrationError,
    ZeoQuotaExceededError,
)

__all__ = [
    "ZeoError",
    "ZeoIOError",
    "ZeoFileNotFoundError",
    "ZeoPermissionError",
    "ZeoFileExistsError",
    "ZeoValidationError",
    "ZeoFormatError",
    "ZeoConfigurationError",
    "ZeoPluginError",
    "ZeoBaseAuthError",
    "ZeoIntegrationError",
    "ZeoApiError",
    "ZeoQuotaExceededError",
    "wrap_io_errors",
    "ZeoAuthenticationError",
]
