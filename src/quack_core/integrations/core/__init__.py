# quack-core/src/quack-core/integrations/core/__init__.py
"""
Integrations package for QuackCore.

This package provides a framework for connecting QuackCore to external services
and platforms, with a modular approach that allows for community contributions.
"""

import logging
from typing import TypeVar, cast

from quackcore.integrations.core.base import (
    BaseAuthProvider,
    BaseConfigProvider,
    BaseIntegrationService,
)
from quackcore.integrations.core.protocols import (
    AuthProviderProtocol,
    ConfigProviderProtocol,
    IntegrationProtocol,
    StorageIntegrationProtocol,
)
from quackcore.integrations.core.registry import IntegrationRegistry
from quackcore.integrations.core.results import (
    AuthResult,
    ConfigResult,
    IntegrationResult,
)

# Create a global registry instance
registry = IntegrationRegistry()

# Initialize by discovering integrations
try:
    registry.discover_integrations()
except Exception as e:
    logging.getLogger(__name__).warning(f"Error discovering integrations: {e}")


# Generic type for service
T = TypeVar("T", bound=BaseIntegrationService)


def get_integration_service(service_type: type[T]) -> T | None:
    """
    Get an integration service of the specified type.

    This function searches the registry for an integration service that matches
    the specified type and returns the first one found.

    Args:
        service_type: The type of integration service to retrieve

    Returns:
        T | None: An instance of the requested service type, or None if not found
    """
    logger = logging.getLogger(__name__)

    # Search for services matching the requested type
    for service in registry.get_integration_by_type(service_type):
        # Return the first one found, cast to the requested type
        if isinstance(service, service_type):
            logger.debug(f"Found integration service: {service.name}")
            return cast(T, service)

    # Log the failure to find a matching service
    logger.debug(f"No integration service found for type: {service_type.__name__}")
    return None


__all__ = [
    # Base classes
    "BaseAuthProvider",
    "BaseConfigProvider",
    "BaseIntegrationService",
    # Protocols
    "AuthProviderProtocol",
    "ConfigProviderProtocol",
    "IntegrationProtocol",
    "StorageIntegrationProtocol",
    # Results
    "AuthResult",
    "ConfigResult",
    "IntegrationResult",
    # Registry
    "IntegrationRegistry",
    "registry",
    # Utility functions
    "get_integration_service",
]
