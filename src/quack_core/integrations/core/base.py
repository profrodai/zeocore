# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/core/base.py
# module: quack_core.integrations.core.base
# role: module
# neighbors: __init__.py, protocols.py, registry.py, results.py
# exports: BaseAuthProvider, BaseConfigProvider, BaseIntegrationService
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
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
from quack_core.lib.errors import QuackConfigurationError
from quack_core.lib.logging import LOG_LEVELS, LogLevel, get_logger


class BaseAuthProvider(ABC, AuthProviderProtocol):
    """Base class for authentication providers."""

    def __init__(
        self,
        credentials_file: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(log_level)

        self.credentials_file = (
            self._resolve_path(credentials_file) if credentials_file else None
        )
        self.authenticated = False

    def _resolve_path(self, file_path: str) -> str:
        try:
            from quack_core.core.fs.service import standalone
            result = standalone.resolve_path(file_path)
            return standalone.coerce_path_str(result)
        except Exception as e:
            self.logger.warning(f"Could not resolve project path: {e}")
            from quack_core.core.fs.service import standalone
            normalized = standalone.normalize_path(file_path)
            return standalone.coerce_path_str(normalized)

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def authenticate(self) -> AuthResult: ...

    @abstractmethod
    def refresh_credentials(self) -> AuthResult: ...

    @abstractmethod
    def get_credentials(self) -> object: ...

    def save_credentials(self) -> bool:
        self.logger.warning(
            "save_credentials() not implemented in base class. Override in subclass."
        )
        return False

    def _ensure_credentials_directory(self) -> bool:
        if not self.credentials_file:
            return False
        try:
            from quack_core.core.fs.service import standalone
            cred_path = standalone.coerce_path(self.credentials_file)
            parent_dir = cred_path.parent
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
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(log_level)

    @property
    @abstractmethod
    def name(self) -> str: ...

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        from quack_core.core.fs.service import standalone

        if not config_path:
            config_path = self._find_config_file()
            if not config_path:
                raise QuackConfigurationError(
                    "Configuration file not found in default locations."
                )

        config_path_str = standalone.coerce_path_str(config_path)

        file_info = standalone.get_file_info(config_path_str)
        if not file_info.success or not file_info.exists:
            raise QuackConfigurationError(
                f"Configuration file not found: {config_path_str}",
                config_path=config_path_str,
            )

        yaml_result = standalone.read_yaml(config_path_str)
        if not yaml_result.success:
            raise QuackConfigurationError(
                f"Failed to read YAML configuration: {yaml_result.error}",
                config_path=config_path_str,
            )

        config_data = yaml_result.data
        integration_config = self._extract_config(config_data)

        if not self.validate_config(integration_config):
            return ConfigResult.error_result("Configuration validation failed")

        return ConfigResult.success_result(
            content=integration_config,
            message="Successfully loaded configuration",
            config_path=config_path_str,
        )

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        integration_name = self.name.lower().replace(" ", "_")
        return config_data.get(integration_name, {})

    def _find_config_file(self) -> str | None:
        from quack_core.core.fs.service import standalone

        # 1. Check Environment Variable
        env_var = f"QUACK_{self.name.upper()}_CONFIG"
        if config_path := os.environ.get(env_var):
            expanded_path = standalone.expand_user_vars(config_path)
            path_str = standalone.coerce_path_str(expanded_path)
            file_info = standalone.get_file_info(path_str)
            if file_info.success and file_info.exists:
                return path_str

        # 2. Determine Project Root
        project_root = None
        try:
            from quack_core.lib.paths import service as paths
            if hasattr(paths, "get_project_root"):
                root_result = paths.get_project_root()
                if root_result.success:
                    # Explicitly use .path from result for strict correctness
                    project_root = standalone.coerce_path(root_result.path)
        except Exception as e:
            self.logger.debug(f"Project root lookup failed, checking only direct paths: {e}")

        # 3. Check Default Locations
        for location in self.DEFAULT_CONFIG_LOCATIONS:
            expanded = standalone.expand_user_vars(location)
            candidate_path = standalone.coerce_path(expanded)

            if not candidate_path.is_absolute() and project_root:
                candidate_path = project_root / candidate_path

            candidate_str = standalone.coerce_path_str(candidate_path)
            file_info = standalone.get_file_info(candidate_str)
            if file_info.success and file_info.exists:
                return candidate_str

        # 4. Fallback: check project root default file
        if project_root:
            fallback = project_root / "quack_config.yaml"
            fallback_str = standalone.coerce_path_str(fallback)
            file_info = standalone.get_file_info(fallback_str)
            if file_info.success and file_info.exists:
                return fallback_str

        return None

    def _resolve_path(self, file_path: str) -> str:
        try:
            from quack_core.core.fs.service import standalone
            result = standalone.resolve_path(file_path)
            return standalone.coerce_path_str(result)
        except Exception as e:
            self.logger.warning(f"Could not resolve project path: {e}")
            return file_path

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool: ...

    @abstractmethod
    def get_default_config(self) -> dict[str, Any]: ...


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
        self.config_path = config_path
        try:
            from quack_core.core.fs.service import standalone
            result = standalone.resolve_path(config_path)
            self.config_path = standalone.coerce_path_str(result)
            self.logger.debug(f"Set config path to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Error setting config path: {e}")
            self.config_path = config_path

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def integration_id(self) -> str:
        return self.name.lower().replace(" ", ".")

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> IntegrationResult:
        if self._initialized:
            self.logger.debug(f"{self.integration_id} integration already initialized")
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
        return self._initialized

    def _ensure_initialized(self) -> IntegrationResult | None:
        if not self._initialized:
            self.logger.info(f"Auto-initializing {self.name} integration")
            init_result = self.initialize()
            if not init_result.success:
                return init_result
        return None
