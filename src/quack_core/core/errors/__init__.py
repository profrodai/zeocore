# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/errors/__init__.py
# module: quack_core.core.errors.__init__
# role: module
# neighbors: base.py, handlers.py, integration.py
# exports: QuackError, QuackIOError, QuackFileNotFoundError, QuackPermissionError, QuackFileExistsError, QuackValidationError, QuackFormatError, QuackConfigurationError (+7 more)
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

"""
Error handling utilities for quack_core.

This module provides custom exception classes for QuackCore, with helpful context
and error messages for better diagnostics and troubleshooting.
"""

from quack_core.core.errors.base import (
    QuackBaseAuthError,
    QuackConfigurationError,
    QuackError,
    QuackFileExistsError,
    QuackFileNotFoundError,
    QuackFormatError,
    QuackIOError,
    QuackPermissionError,
    QuackPluginError,
    QuackValidationError,
    wrap_io_errors,
)
from quack_core.core.errors.integration import (
    QuackApiError,
    QuackAuthenticationError,
    QuackIntegrationError,
    QuackQuotaExceededError,
)

__all__ = [
    "QuackError",
    "QuackIOError",
    "QuackFileNotFoundError",
    "QuackPermissionError",
    "QuackFileExistsError",
    "QuackValidationError",
    "QuackFormatError",
    "QuackConfigurationError",
    "QuackPluginError",
    "QuackBaseAuthError",
    "QuackIntegrationError",
    "QuackApiError",
    "QuackQuotaExceededError",
    "wrap_io_errors",
    "QuackAuthenticationError",
]