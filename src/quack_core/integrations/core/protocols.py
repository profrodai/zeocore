# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/core/protocols.py
# module: quack_core.integrations.core.protocols
# role: protocols
# neighbors: __init__.py, registry.py, results.py, base.py
# exports: AuthProviderProtocol, ConfigProviderProtocol, IntegrationProtocol, StorageIntegrationProtocol
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Protocol definitions for QuackCore integrations.

This module defines the interfaces that all integrations should implement,
ensuring consistent behavior across different services and platforms.
"""

from collections.abc import Mapping
from typing import Any, Protocol, TypeVar, runtime_checkable

from quack_core.integrations.core.results import (
    AuthResult,
    ConfigResult,
    IntegrationResult,
)

T = TypeVar("T")  # Generic type for results


@runtime_checkable
class AuthProviderProtocol(Protocol):
    """Protocol for authentication providers."""

    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        ...

    def authenticate(self) -> AuthResult:
        ...

    def refresh_credentials(self) -> AuthResult:
        ...

    def get_credentials(self) -> object:
        ...

    def save_credentials(self) -> bool:
        ...


@runtime_checkable
class ConfigProviderProtocol(Protocol):
    """Protocol for configuration providers."""

    @property
    def name(self) -> str:
        """Name of the configuration provider."""
        ...

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        ...

    def validate_config(self, config: dict[str, Any]) -> bool:
        ...

    def get_default_config(self) -> dict[str, Any]:
        ...


@runtime_checkable
class IntegrationProtocol(Protocol):
    """Base protocol for all integrations."""

    @property
    def integration_id(self) -> str:
        """
        Unique, stable identifier for the integration (e.g., 'github', 'google.mail').
        Used for configuration and registry lookups.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name of the integration."""
        ...

    @property
    def version(self) -> str:
        """Version of the integration."""
        ...

    def initialize(self) -> IntegrationResult:
        """
        Initialize the integration.

        This method should perform any necessary setup, internal registration,
        or connection checks. It is called explicitly by the loader.
        """
        ...

    def is_available(self) -> bool:
        """Check if the integration is available/healthy."""
        ...


@runtime_checkable
class StorageIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for storage integrations."""

    def upload_file(
            self, file_path: str, remote_path: str | None = None
    ) -> IntegrationResult[str]:
        ...

    def download_file(
            self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        ...

    def list_files(
            self, remote_path: str | None = None, pattern: str | None = None
    ) -> IntegrationResult[list[Mapping]]:
        ...

    def create_folder(
            self, folder_name: str, parent_path: str | None = None
    ) -> IntegrationResult[str]:
        ...