# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/core/__init__.py
# module: quack_core.integrations.core.__init__
# role: module
# neighbors: protocols.py, registry.py, results.py, base.py
# exports: BaseAuthProvider, BaseConfigProvider, BaseIntegrationService, AuthProviderProtocol, ConfigProviderProtocol, IntegrationProtocol, StorageIntegrationProtocol, AuthResult (+7 more)
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

"""
Integrations package for quack_core.

This package provides a framework for connecting QuackCore to external services
and platforms, with a modular approach that allows for community contributions.
"""

from typing import TypeVar, cast

from quack_core.integrations.boot import get_global_registry, load_integrations
from quack_core.integrations.core.base import (
    BaseAuthProvider,
    BaseConfigProvider,
    BaseIntegrationService,
)
from quack_core.integrations.core.protocols import (
    AuthProviderProtocol,
    ConfigProviderProtocol,
    IntegrationProtocol,
    StorageIntegrationProtocol,
)
from quack_core.integrations.core.registry import IntegrationRegistry
from quack_core.integrations.core.results import (
    AuthResult,
    ConfigResult,
    IntegrationLoadReport,
    IntegrationResult,
)

T = TypeVar("T", bound=BaseIntegrationService)


def get_integration_service(service_type: type[T]) -> T | None:
    """
    Get an integration service of the specified type from the GLOBAL registry.

    NOTE: This is a convenience function. For better testability, prefer
    passing dependencies explicitly.
    """
    registry = get_global_registry()
    for service in registry.get_integration_by_type(service_type):
        if isinstance(service, service_type):
            return cast(T, service)
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
    "IntegrationLoadReport",
    # Registry & Boot
    "IntegrationRegistry",
    "get_global_registry",
    "load_integrations",
    # Utility functions
    "get_integration_service",
]
