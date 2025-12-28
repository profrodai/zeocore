# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/core/base.py
# module: quack_core.integrations.core.base
# role: module
# neighbors: __init__.py, protocols.py, registry.py, results.py
# exports: BaseAuthProvider, BaseConfigProvider, BaseIntegrationService
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===


"""
Base classes for QuackCore integrations.

This module provides abstract base classes that integration implementations
can inherit from, providing common functionality and ensuring
consistent behavior.
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from quack_core.lib.errors import QuackConfigurationError
from quack_core.integrations.core.protocols import (
    AuthProviderProtocol,
    ConfigProviderProtocol,
    IntegrationProtocol,
)
from quack_core.integrations.core.results import (
    AuthResult,
    ConfigResult,
    IntegrationResult,
)
from quack_core.lib.logging import LOG_LEVELS, LogLevel, get_logger


class BaseAuthProvider(ABC, AuthProviderProtocol):
    """Base class for authentication providers."""

    def __init__(
        self,
        credentials_file: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """
        Initialize the base authentication provider.

        Args:
            credentials_file: Path to credentials file
            log_level: Logging level
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(log_level)

        self.credentials_file = (
            self._resolve_path(credentials_file) if credentials_file else None
        )
        self.authenticated = False

    def _resolve_path(self, file_path: str) -> str:
        """
        Resolve a path relative to the project root if needed.

        Args:
            file_path: Path to resolve

        Returns:
            str: Resolved absolute path
        """
        try:
            from quack_core.lib.fs.service import standalone

            result = standalone.resolve_path(file_path)
            if hasattr(result, "path"):
                return str(result.path)
            return str(result)
        except Exception as e:
            self.logger.warning(f"Could not resolve project path: {e}")
            from quack_core.lib.fs.service import standalone

            normalized_path = standalone.normalize_path(file_path)
            return str(normalized_path)

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the authentication provider."""
        ...

    @abstractmethod
    def authenticate(self) -> AuthResult:
        """
        Authenticate with the external service.

        Returns:
            AuthResult: Result of authentication
        """
        ...

    @abstractmethod
    def refresh_credentials(self) -> AuthResult:
        """
        Refresh authentication credentials if expired.

        Returns:
            AuthResult: Result of refresh operation
        """
        ...

    @abstractmethod
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

        This is a placeholder implementation that should be overridden
        by subclasses to provide actual credential saving.

        Returns:
            bool: True if saving was successful
        """
        self.logger.warning(
            "save_credentials() not implemented in base class. Override in subclass."
        )
        return False

    def _ensure_credentials_directory(self) -> bool:
        """
        Ensure the directory for credentials exists.

        Returns:
            bool: True if directory exists or was created
        """
        if not self.credentials_file:
            return False

        try:
            from quack_core.lib.fs.service import standalone

            parts = standalone.split_path(self.credentials_file)
            # Normalize to a simple list of path components
            if hasattr(parts, "data"):
                seq = parts.data
            elif isinstance(parts, (list, tuple)):
                seq = list(parts)
            else:
                seq = list(parts)

            # Drop the last component (the file name) if present
            dir_parts = seq[:-1] if len(seq) > 1 else seq

            parent_dir = standalone.join_path(*dir_parts)
            result = standalone.create_directory(parent_dir, exist_ok=True)
            return getattr(result, "success", False)
        except Exception as e:
            self.logger.error(f"Unexpected error creating credentials directory: {e}")
            return False


class BaseConfigProvider(ABC, ConfigProviderProtocol):
    """Base class for configuration providers."""

    DEFAULT_CONFIG_LOCATIONS = [
        "./config/integration_config.yaml",
        "./quack_config.yaml",
        "~/.quack/config.yaml",
    ]

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        """
        Initialize the base configuration provider.

        Args:
            log_level: Logging level
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(log_level)

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the configuration provider."""
        ...

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        """
        Load configuration from a file.

        Args:
            config_path: Path to configuration file.

        Returns:
            ConfigResult: Result containing configuration data.

        Raises:
            QuackConfigurationError: If the configuration file cannot be found or
                                      if reading the YAML fails.
        """
        if not config_path:
            config_path = self._find_config_file()
            if not config_path:
                raise QuackConfigurationError(
                    "Configuration file not found in default locations."
                )

        from quack_core.lib.fs.service import standalone

        file_info = standalone.get_file_info(config_path)
        if not file_info.success or not file_info.exists:
            raise QuackConfigurationError(
                f"Configuration file not found: {config_path}",
                config_path=str(config_path),
            )

        yaml_result = standalone.read_yaml(config_path)
        if not yaml_result.success:
            raise QuackConfigurationError(
                f"Failed to read YAML configuration: {yaml_result.error}",
                config_path=str(config_path),
            )

        config_data = yaml_result.data
        integration_config = self._extract_config(config_data)

        if not self.validate_config(integration_config):
            return ConfigResult.error_result("Configuration validation failed")

        return ConfigResult.success_result(
            content=integration_config,
            message="Successfully loaded configuration",
            config_path=str(config_path),
        )

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract integration-specific configuration from the full config data.

        Args:
            config_data: Full configuration data

        Returns:
            dict[str, Any]: Integration-specific configuration
        """
        integration_name = self.name.lower().replace(" ", "_")
        return config_data.get(integration_name, {})

    def _find_config_file(self) -> str | None:
        """
        Find a configuration file in standard locations.

        Returns:
            str | None: Path to the configuration file if found, None otherwise.
        """
        env_var = f"QUACK_{self.name.upper()}_CONFIG"
        if config_path := os.environ.get(env_var):
            from quack_core.lib.fs.service import standalone

            expanded_path = standalone.expand_user_vars(config_path)
            # Extract path from result
            if hasattr(expanded_path, "data"):
                expanded_path = expanded_path.data

            file_info = standalone.get_file_info(expanded_path)
            if file_info.success and file_info.exists:
                return str(expanded_path)

        project_root = None
        try:
            from quack_core.lib.paths import service as paths

            if hasattr(paths, "get_project_root"):
                project_root_result = paths.get_project_root()
                # Extract path from result
                if project_root_result.success and project_root_result.path:
                    project_root = project_root_result.path
        except Exception as e:
            self.logger.debug(
                f"Project root not found, checking only direct paths: {e}")

        from quack_core.lib.fs.service import standalone

        for location in self.DEFAULT_CONFIG_LOCATIONS:
            expanded_location = standalone.expand_user_vars(location)
            # Extract data from result
            if hasattr(expanded_location, "data"):
                expanded_location = expanded_location.data

            if not os.path.isabs(str(expanded_location)) and project_root:
                join_result = standalone.join_path(project_root, expanded_location)
                # Extract path from result
                if hasattr(join_result, "data"):
                    expanded_location = join_result.data

            file_info = standalone.get_file_info(expanded_location)
            if file_info.success and file_info.exists:
                return str(expanded_location)

        if project_root:
            candidate_result = standalone.join_path(project_root, "quack_config.yaml")
            # Extract path from result
            if hasattr(candidate_result, "data"):
                candidate = candidate_result.data
            else:
                candidate = candidate_result

            candidate = standalone.expand_user_vars(candidate)
            # Extract from result
            if hasattr(candidate, "data"):
                candidate = candidate.data

            file_info = standalone.get_file_info(candidate)
            if file_info.success and file_info.exists:
                return str(candidate)

        return None

    def _resolve_path(self, file_path: str) -> str:
        """
        Resolve a path relative to the project root if needed.

        Args:
            file_path: Path to resolve.

        Returns:
            str: Resolved absolute path.
        """
        try:
            from quack_core.lib.fs.service import standalone

            result = standalone.resolve_path(file_path)
            if hasattr(result, "path"):
                return str(result.path)
            return str(result)
        except Exception as e:
            self.logger.warning(f"Could not resolve project path: {e}")
            return file_path

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration data.

        Args:
            config: Configuration data to validate

        Returns:
            bool: True if configuration is valid
        """
        ...

    @abstractmethod
    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            dict[str, Any]: Default configuration values
        """
        ...


class BaseIntegrationService(ABC, IntegrationProtocol):
    """Base class for integration services."""

    def __init__(
        self,
        config_provider: ConfigProviderProtocol | None = None,
        auth_provider: AuthProviderProtocol | None = None,
        config: dict[str, Any] | None = None,
        config_path: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """
        Initialize the base integration service.

        Args:
            config_provider: Configuration provider
            auth_provider: Authentication provider
            config: Configuration data
            config_path: Path to configuration file
            log_level: Logging level
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(log_level)
        self.log_level = log_level

        self.config_provider = config_provider
        self.auth_provider = auth_provider
        self.config = config
        self._initialized = False

        self.config_path = None
        if config_path:
            self._set_config_path(config_path)

    def _set_config_path(self, config_path: str) -> None:
        """
        Set the configuration path.

        This method is separated to allow easier patching in tests.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        try:
            from quack_core.lib.fs.service import standalone

            result = standalone.resolve_path(config_path)
            self.config_path = str(result.path) if hasattr(result, "path") else str(
                result
            )
            self.logger.debug(f"Set config path to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Error setting config path: {e}")
            self.config_path = config_path

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the integration."""
        ...

    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"

    def initialize(self) -> IntegrationResult:
        """
        Initialize the integration.

        Returns:
            IntegrationResult: Result of initialization
        """
        if self._initialized:
            self.logger.debug(f"{self.name} integration already initialized")
            return IntegrationResult.success_result(
                message=f"{self.name} integration already initialized"
            )

        try:
            if not self.config and self.config_provider:
                config_result = self.config_provider.load_config(self.config_path)
                if not config_result.success:
                    raise QuackConfigurationError(
                        f"Failed to load configuration: {config_result.error}",
                        config_path=self.config_path,
                    )
                self.config = config_result.content
                if config_result.config_path and not self.config_path:
                    self._set_config_path(config_result.config_path)

            if self.auth_provider and not getattr(
                self.auth_provider, "authenticated", False
            ):
                auth_result = self.auth_provider.authenticate()
                if not auth_result.success:
                    return IntegrationResult.error_result(
                        f"Failed to authenticate {self.name}: {auth_result.error}"
                    )

            self._initialized = True
            return IntegrationResult.success_result(
                message=f"{self.name} integration initialized successfully"
            )
        except QuackConfigurationError as e:
            self.logger.error(f"Configuration error during initialization: {e}")
            return IntegrationResult.error_result(str(e))
        except Exception as e:
            self.logger.error(f"Failed to initialize integration: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize {self.name} integration: {str(e)}"
            )

    def is_available(self) -> bool:
        """Check if the integration is available."""
        return self._initialized

    def _ensure_initialized(self) -> IntegrationResult | None:
        """
        Ensure the integration is initialized.

        Returns:
            IntegrationResult | None: Error result if initialization fails,
                                        None if initialized
        """
        if not self._initialized:
            self.logger.info(f"Auto-initializing {self.name} integration")
            init_result = self.initialize()
            if not init_result.success:
                return init_result
        return None
