# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/core/registry.py
# module: quack_core.integrations.core.registry
# role: module
# neighbors: __init__.py, protocols.py, results.py, base.py
# exports: IntegrationRegistry
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""
Registry for QuackCore integrations.

This module provides a pure registry for managing loaded integrations.
It is a simple container and does not perform discovery or side effects.
"""

from typing import Iterable, TypeVar

from quack_core.lib.errors import QuackError
from quack_core.integrations.core.protocols import IntegrationProtocol
from quack_core.lib.logging import LOG_LEVELS, LogLevel, get_logger

T = TypeVar("T", bound=IntegrationProtocol)


class IntegrationRegistry:
    """
    Registry for QuackCore integrations.

    Stores active integrations keyed by their stable integration_id.
    """

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)
        self._integrations: dict[str, IntegrationProtocol] = {}

    def register(self, integration: IntegrationProtocol) -> None:
        """
        Register an integration with the registry.

        Args:
            integration: Integration to register.

        Raises:
            QuackError: If the integration_id is already registered.
        """
        # Fallback for integrations that might not have updated to the new base class yet
        if hasattr(integration, "integration_id"):
            key = integration.integration_id
        else:
            self.logger.warning(
                f"Integration '{integration.name}' lacks 'integration_id'. "
                "Falling back to name, but this is deprecated."
            )
            key = integration.name

        if key in self._integrations:
            raise QuackError(
                f"Integration '{key}' is already registered",
                {"integration_id": key},
            )

        self._integrations[key] = integration
        self.logger.debug(f"Registered integration: {key} ({integration.name})")

    def unregister(self, integration_id: str) -> bool:
        """
        Unregister an integration from the registry.

        Args:
            integration_id: ID of the integration to unregister.

        Returns:
            bool: True if the integration was unregistered, False if not found.
        """
        if integration_id in self._integrations:
            del self._integrations[integration_id]
            self.logger.debug(f"Unregistered integration: {integration_id}")
            return True

        self.logger.warning(
            f"Integration not found for unregistration: {integration_id}")
        return False

    def get_integration(self, integration_id: str) -> IntegrationProtocol | None:
        """
        Get an integration by ID.

        Args:
            integration_id: The unique identifier.

        Returns:
            IntegrationProtocol | None: The integration if found, else None.
        """
        return self._integrations.get(integration_id)

    def get_integration_by_type(self, integration_type: type[T]) -> Iterable[T]:
        """
        Get all integrations of a specific type.

        Args:
            integration_type: Type of integrations to get.

        Returns:
            Iterable[T]: Integrations of the specified type.
        """
        for integration in self._integrations.values():
            if isinstance(integration, integration_type):
                yield integration

    def list_ids(self) -> list[str]:
        """
        Get a list of all registered integration IDs.

        Returns:
            list[str]: List of integration IDs.
        """
        return list(self._integrations.keys())

    def is_registered(self, integration_id: str) -> bool:
        """Check if an integration is registered."""
        return integration_id in self._integrations

    def clear(self) -> None:
        """Clear all registrations. Useful for testing."""
        self._integrations.clear()
        self.logger.debug("Registry cleared")