# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/toolkit/mixins/integration_enabled.py
# module: quack_core.toolkit.mixins.integration_enabled
# role: module
# neighbors: __init__.py, env_init.py, lifecycle.py, output_handler.py
# exports: IntegrationEnabledMixin
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

"""
Integration enabled mixin for QuackTool plugins.

This module provides a mixin that enables integration with various services
by providing a generic interface for resolving and accessing integration services.
"""

from typing import Any, Generic, TypeVar

# Import directly to ensure patching can work
import quack_core.integrations.core
from quack_core.integrations.core.base import BaseIntegrationService

T = TypeVar("T", bound=BaseIntegrationService)


class IntegrationEnabledMixin(Generic[T]):
    """
    Mixin that enables integration with a specified service type.

    This mixin provides a generic way to resolve and access integration
    services, such as GoogleDriveService, GitHubService, etc.

    Example:
        ```python
        class MyTool(IntegrationEnabledMixin[GoogleDriveService], BaseQuackToolPlugin):
            def initialize_plugin(self) -> None:
                self._drive = self.resolve_integration(GoogleDriveService)
                # Now self._drive _and_ self._upload_service both refer to a GoogleDriveService instance
        ```
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Prepare both generic and upload‐specific attributes
        self._integration_service: T | None = None
        self._upload_service: T | None = None
        super().__init__(*args, **kwargs)

    def resolve_integration(self, service_type: type[T]) -> T | None:
        """
        Lazily load the integration service of the given type.

        Stores the result for reuse on subsequent calls, and also exposes it
        as `_upload_service` for tools that call `.upload_file(...)` directly.

        Args:
            service_type: The type of integration service to resolve

        Returns:
            The resolved integration service, or None if not available
        """
        service = quack_core.integrations.core.get_integration_service(service_type)

        # Store under the generic handle…
        self._integration_service = service
        # …and also under the upload‐convenience handle
        self._upload_service = service

        # If the service wants initialization, do so
        if service is not None and hasattr(service, "initialize") and callable(service.initialize):
            try:
                service.initialize()
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.error(f"Failed to initialize integration service: {e}")

        return service

    def get_integration_service(self) -> T | None:
        """
        Get the resolved integration service.

        Returns:
            The previously resolved integration service, or None
        """
        return self._integration_service

    @property
    def integration(self) -> T | None:
        """
        Shortcut to get the resolved integration service.

        Returns:
            The previously resolved integration service, or None
        """
        return self.get_integration_service()
