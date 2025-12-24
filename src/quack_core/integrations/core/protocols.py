# quack-core/src/quack_core/integrations/core/protocols.py
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
F = TypeVar("F")  # Generic type for file content


@runtime_checkable
class AuthProviderProtocol(Protocol):
    """Protocol for authentication providers."""

    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        ...

    def authenticate(self) -> AuthResult:
        """
        Authenticate with the external service.

        Returns:
            AuthResult: Result of authentication
        """
        ...

    def refresh_credentials(self) -> AuthResult:
        """
        Refresh authentication credentials if expired.

        Returns:
            AuthResult: Result of refresh operation
        """
        ...

    def get_credentials(self) -> object:
        """
        Get the current authentication credentials.

        Returns:
            object: The authentication credentials
        """
        ...

    def save_credentials(self) -> bool:
        """
        Save the current authentication credentials.

        Returns:
            bool: True if saving was successful
        """
        ...


@runtime_checkable
class ConfigProviderProtocol(Protocol):
    """Protocol for configuration providers."""

    @property
    def name(self) -> str:
        """Name of the configuration provider."""
        ...

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        """
        Load configuration from a file.

        Args:
            config_path: Path to configuration file

        Returns:
            ConfigResult: Result containing configuration data
        """
        ...

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration data.

        Args:
            config: Configuration data to validate

        Returns:
            bool: True if configuration is valid
        """
        ...

    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            dict[str, Any]: Default configuration values
        """
        ...


@runtime_checkable
class IntegrationProtocol(Protocol):
    """Base protocol for all integrations."""

    @property
    def name(self) -> str:
        """Name of the integration."""
        ...

    @property
    def version(self) -> str:
        """Version of the integration."""
        ...

    def initialize(self) -> IntegrationResult:
        """
        Initialize the integration.

        Returns:
            IntegrationResult: Result of initialization
        """
        ...

    def is_available(self) -> bool:
        """
        Check if the integration is available.

        Returns:
            bool: True if integration is available
        """
        ...


@runtime_checkable
class StorageIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for storage integrations."""

    def upload_file(
        self, file_path: str, remote_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Upload a file to the storage service.

        Args:
            file_path: Path to the file to upload
            remote_path: Optional remote path or identifier

        Returns:
            IntegrationResult[str]: Result with the remote file URL or ID
        """
        ...

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Download a file from the storage service.

        Args:
            remote_id: ID or path of the remote file
            local_path: Optional local path to save the file

        Returns:
            IntegrationResult[str]: Result with the local file path
        """
        ...

    def list_files(
        self, remote_path: str | None = None, pattern: str | None = None
    ) -> IntegrationResult[list[Mapping]]:
        """
        List files in the storage service.

        Args:
            remote_path: Optional remote path or folder ID
            pattern: Optional pattern to match filenames

        Returns:
            IntegrationResult[list[Mapping]]: Result with the list of files
        """
        ...

    def create_folder(
        self, folder_name: str, parent_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Create a folder in the storage service.

        Args:
            folder_name: Name of the folder to create
            parent_path: Optional parent folder path or ID

        Returns:
            IntegrationResult[str]: Result with the folder ID or path
        """
        ...
