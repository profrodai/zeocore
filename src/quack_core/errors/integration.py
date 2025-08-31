# quack-core/src/quack-core/errors/integration.py
"""
Integration-related error classes for quack_core.

This module provides custom exception classes for integration errors,
with specific types for authentication, configuration, and other issues.
"""

from quack_core.errors.base import QuackError


class QuackIntegrationError(QuackError):
    """Base exception for all integration-related errors."""

    def __init__(
        self,
        message: str,
        context: dict[str, object] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize an integration error.

        Args:
            message: The error message
            context: Additional context information (optional)
            original_error: The original exception that caused this error (optional)
        """
        super().__init__(message, context, original_error)


class QuackAuthenticationError(QuackIntegrationError):
    """Raised when there's an authentication error with an integration."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        credentials_path: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize an authentication error.

        Args:
            message: The error message
            service: The service name (e.g., "Google Drive", "Gmail") (optional)
            credentials_path: The path to the credentials file (optional)
            original_error: The original exception that caused this error (optional)
        """
        context: dict[str, object] = {}
        if service is not None:
            context["service"] = service
        if credentials_path is not None:
            context["credentials_path"] = credentials_path

        super().__init__(message, context, original_error)
        self.service: str | None = service
        self.credentials_path: str | None = credentials_path


class QuackApiError(QuackIntegrationError):
    """Raised when there's an error with an external API."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        status_code: int | None = None,
        api_method: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize an API error.

        Args:
            message: The error message
            service: The service name (e.g., "Google Drive", "Gmail") (optional)
            status_code: The HTTP status code (optional)
            api_method: The API method that was called (optional)
            original_error: The original exception that caused this error (optional)
        """
        context: dict[str, object] = {}
        if service is not None:
            context["service"] = service
        if status_code is not None:
            context["status_code"] = status_code
        if api_method is not None:
            context["api_method"] = api_method

        super().__init__(message, context, original_error)
        self.service: str | None = service
        self.status_code: int | None = status_code
        self.api_method: str | None = api_method


class QuackQuotaExceededError(QuackApiError):
    """Raised when an API quota is exceeded."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        resource: str | None = None,
        limit: int | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize a quota exceeded error.

        Args:
            message: The error message
            service: The service name (e.g., "Google Drive", "Gmail") (optional)
            resource: The resource that hit the quota limit (optional)
            limit: The quota limit (optional)
            original_error: The original exception that caused this error (optional)
        """
        context: dict[str, object] = {}
        if service is not None:
            context["service"] = service
        if resource is not None:
            context["resource"] = resource
        if limit is not None:
            context["limit"] = limit

        super().__init__(message, service, 429, "quota_check", original_error)
        self.resource: str | None = resource
        self.limit: int | None = limit
