# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/errors/integration.py
# module: quack_core.core.errors.integration
# role: module
# neighbors: __init__.py, base.py, handlers.py
# exports: QuackIntegrationError, QuackAuthenticationError, QuackApiError, QuackQuotaExceededError
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===


"""
Integration-related error classes for quack_core.
"""

from quack_core.core.errors.base import QuackError


class QuackIntegrationError(QuackError):
    """Base exception for all integration-related errors."""
    pass


class QuackAuthenticationError(QuackIntegrationError):
    """Raised when there's an authentication error with an integration."""

    def __init__(
            self,
            message: str,
            service: str | None = None,
            credentials_path: str | None = None,
            original_error: Exception | None = None,
    ) -> None:
        context: dict[str, object] = {}
        if service is not None:
            context["service"] = service
        if credentials_path is not None:
            context["path"] = credentials_path

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
        # Prepare specific context data
        quota_context: dict[str, object] = {}
        if resource is not None:
            quota_context["resource"] = resource
        if limit is not None:
            quota_context["limit"] = limit

        # Initialize base API error
        super().__init__(
            message=message,
            service=service,
            status_code=429,
            api_method="quota_check",
            original_error=original_error,
        )

        # Explicitly merge the quota-specific context into the error context
        # This ensures resource and limit are visible in diagnostics
        self.context.update(quota_context)

        self.resource: str | None = resource
        self.limit: int | None = limit