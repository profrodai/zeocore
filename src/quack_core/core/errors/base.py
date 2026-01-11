# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/errors/base.py
# module: quack_core.core.errors.base
# role: module
# neighbors: __init__.py, handlers.py, integration.py
# exports: QuackError, QuackIOError, QuackFileNotFoundError, QuackPermissionError, QuackFileExistsError, QuackValidationError, QuackFormatError, QuackConfigurationError (+3 more)
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===


"""
Base error classes for quack_core.

This module defines the base exception hierarchy for all errors in the QuackCore
ecosystem, providing consistent error handling and detailed diagnostic information.
"""

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TypeVar

R = TypeVar("R")  # Generic return type for wrapped functions


class QuackError(Exception):
    """Base exception for all errors in the QuackCore ecosystem."""

    def __init__(
        self,
        message: str,
        context: dict[str, object] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize a QuackError.

        Args:
            message: The error message
            context: Additional context information (optional)
            original_error: The original exception that caused this error (optional)
        """
        self.context: dict[str, object] = context or {}
        self.original_error: Exception | None = original_error

        formatted_message = message
        if context:
            context_str = ", ".join(f"{k}={v!r}" for k, v in context.items())
            formatted_message = f"{message} (context: {context_str})"

        super().__init__(formatted_message)


class QuackIOError(QuackError):
    """Base exception for all input/output related errors."""

    def __init__(
        self,
        message: str,
        path: str | Path | None = None,
        original_error: Exception | None = None,
    ) -> None:
        context: dict[str, object] = {}
        if path is not None:
            context["path"] = str(path)

        super().__init__(message, context, original_error)
        self.path: str | None = str(path) if path else None


class QuackFileNotFoundError(QuackIOError):
    """Raised when a file or directory does not exist."""

    def __init__(
        self,
        path: str | Path,
        message: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        if message is None:
            message = f"File or directory not found: {path}"
        super().__init__(message, path, original_error)


class QuackPermissionError(QuackIOError):
    """Raised when permission is denied for a file operation."""

    def __init__(
        self,
        path: str | Path,
        operation: str,
        message: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        if message is None:
            message = f"Permission denied for {operation} operation on {path}"
        # Bypass QuackIOError init to set specific context manually
        QuackError.__init__(
            self, message, {"path": str(path), "op": operation}, original_error
        )
        self.path = str(path) if path else None
        self.operation: str = operation


class QuackFileExistsError(QuackIOError):
    """Raised when trying to create a file or directory that already exists."""

    def __init__(
        self,
        path: str | Path,
        message: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        if message is None:
            message = f"File or directory already exists: {path}"
        super().__init__(message, path, original_error)


class QuackValidationError(QuackError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        path: str | Path | None = None,
        errors: dict[str, list[str]] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        context: dict[str, object] = {}
        if path is not None:
            context["path"] = str(path)
        if errors is not None:
            context["errors"] = errors

        super().__init__(message, context, original_error)
        self.path: str | None = str(path) if path else None
        self.errors: dict[str, list[str]] = errors or {}


class QuackFormatError(QuackIOError):
    """Raised when there's an error in file format or parsing."""

    def __init__(
        self,
        path: str | Path,
        format_name: str,
        message: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        if message is None:
            message = f"Invalid {format_name} format in {path}"
        super().__init__(message, str(path), original_error)
        self.format_name: str = format_name


class QuackConfigurationError(QuackError):
    """Raised when there's an error in configuration."""

    def __init__(
        self,
        message: str,
        config_path: str | Path | None = None,
        config_key: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        context: dict[str, object] = {}
        if config_path is not None:
            context["path"] = str(config_path)
        if config_key is not None:
            context["key"] = config_key

        super().__init__(message, context, original_error)
        self.config_path: str | None = str(config_path) if config_path else None
        self.config_key: str | None = config_key


class QuackPluginError(QuackError):
    """Raised when there's an error with a plugin."""

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        plugin_path: str | Path | None = None,
        original_error: Exception | None = None,
    ) -> None:
        context: dict[str, object] = {}
        if plugin_name is not None:
            context["plugin_name"] = plugin_name
        if plugin_path is not None:
            context["path"] = str(plugin_path)

        super().__init__(message, context, original_error)
        self.plugin_name: str | None = plugin_name
        self.plugin_path: str | None = str(plugin_path) if plugin_path else None


class QuackBaseAuthError(QuackError):
    """Raised when there's an authentication error."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        credentials_path: str | Path | None = None,
        original_error: Exception | None = None,
    ) -> None:
        context: dict[str, object] = {}
        if service is not None:
            context["service"] = service
        if credentials_path is not None:
            context["path"] = str(credentials_path)

        super().__init__(message, context, original_error)
        self.service: str | None = service
        self.credentials_path: str | None = (
            str(credentials_path) if credentials_path else None
        )


def _exception_converter(e: Exception) -> Exception:
    """
    Convert a standard exception to a QuackCore custom exception.
    """
    if isinstance(e, ValueError):
        return QuackValidationError(str(e), original_error=e)
    if isinstance(e, FileNotFoundError):
        path = getattr(e, "filename", None)
        return QuackFileNotFoundError(path or "unknown", original_error=e)
    if isinstance(e, PermissionError):
        path = getattr(e, "filename", None)
        return QuackPermissionError(path or "unknown", "access", original_error=e)
    if isinstance(e, FileExistsError):
        path = getattr(e, "filename", None)
        return QuackFileExistsError(path or "unknown", original_error=e)
    if isinstance(e, IsADirectoryError):
        path = getattr(e, "filename", None)
        return QuackIOError(f"Path is a directory: {path}", path, original_error=e)
    if isinstance(e, NotADirectoryError):
        path = getattr(e, "filename", None)
        return QuackIOError(f"Path is not a directory: {path}", path, original_error=e)
    if isinstance(e, OSError):
        path = getattr(e, "filename", None)
        return QuackIOError(str(e), path, original_error=e)
    return QuackError(str(e), original_error=e)


def wrap_io_errors(func: Callable[..., R]) -> Callable[..., R]:
    """
    Decorator to wrap standard IO exceptions with QuackCore's custom exceptions.
    """

    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> R:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Fix: Use tuple for isinstance check
            if isinstance(
                e,
                (
                    QuackError,
                    QuackIOError,
                    QuackFileNotFoundError,
                    QuackFileExistsError,
                    QuackPermissionError,
                ),
            ):
                raise
            raise _exception_converter(e) from e

    return wrapper

