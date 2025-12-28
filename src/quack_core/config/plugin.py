# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/plugin.py
# module: quack_core.config.plugin
# role: plugin
# neighbors: __init__.py, models.py, utils.py, loader.py
# exports: ConfigPlugin, QuackConfigPlugin, create_plugin
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""
Plugin interface for the configuration module.

This module defines the plugin interface for the configuration module,
allowing QuackCore to expose configuration functionality to other modules.
"""

from typing import Any, Protocol, TypeVar

from quack_core.config.loader import load_config, merge_configs
from quack_core.config.models import QuackConfig
from quack_core.config.utils import get_config_value, normalize_paths

T = TypeVar("T")  # Generic type for flexible typing


class ConfigPlugin(Protocol):
    """Protocol for configuration plugins."""

    @property
    def name(self) -> str:
        """Name of the plugin."""
        ...

    def load_config(
        self,
        config_path: str | None = None,
        merge_env: bool = True,
        merge_defaults: bool = True,
    ) -> QuackConfig:
        """
        Load configuration from a file and merge with environment and defaults.

        Args:
            config_path: Path to configuration file (optional)
            merge_env: Whether to merge with environment variables
            merge_defaults: Whether to merge default configuration values

        Returns:
            QuackConfig: Loaded configuration
        """
        ...

    def merge_configs(self, base: QuackConfig, override: dict[str, Any]) -> QuackConfig:
        """
        Merge a base configuration with override values.

        Args:
            base: Base configuration.
            override: Override values.

        Returns:
            A merged QuackConfig instance.
        """
        ...

    def get_value(self, path: str, default: T | None = None) -> T | None:
        """
        Get a configuration value by path.

        The path is a dot-separated string of keys, e.g. 'logging.level'

        Args:
            path: Path to the configuration value
            default: Default value if the path is not found

        Returns:
            Configuration value
        """
        ...

    def get_base_dir(self) -> str:
        """
        Get the base directory from the configuration.

        Returns:
            str: The base directory as a normalized string.
        """
        ...

    def get_output_dir(self) -> str:
        """
        Get the output directory from the configuration.

        Returns:
            str: The output directory as a normalized string.
        """
        ...


class QuackConfigPlugin:
    """Implementation of the configuration plugin protocol."""

    def __init__(self) -> None:
        """Initialize the plugin."""
        # load_config and normalize_paths work entirely in the string space.
        self._config = load_config()
        self._config = normalize_paths(self._config)

    @property
    def name(self) -> str:
        """Name of the plugin."""
        return "config"

    def load_config(
        self,
        config_path: str | None = None,
        merge_env: bool = True,
        merge_defaults: bool = True,
    ) -> QuackConfig:
        """
        Load configuration from a file and merge with environment and defaults.

        Args:
            config_path: Path to configuration file (optional)
            merge_env: Whether to merge with environment variables
            merge_defaults: Whether to merge default configuration values

        Returns:
            QuackConfig: Loaded configuration
        """
        # When a config_path is provided, ensure it is a string
        self._config = load_config(
            config_path=str(config_path) if config_path else None,
            merge_env=merge_env,
            merge_defaults=merge_defaults,
        )
        self._config = normalize_paths(self._config)
        return self._config

    def merge_configs(self, base: QuackConfig, override: dict[str, Any]) -> QuackConfig:
        """
        Merge a base configuration with override values.

        Args:
            base: Base configuration.
            override: Override values.

        Returns:
            A merged QuackConfig instance.
        """
        return merge_configs(base, override)

    def get_value(self, path: str, default: T | None = None) -> T | None:
        """
        Get a configuration value by path.

        Args:
            path: Dot-separated path to the configuration value (e.g. 'logging.level')
            default: Default value if the key is not found

        Returns:
            The configuration value.
        """
        return get_config_value(self._config, path, default)

    def get_base_dir(self) -> str:
        """
        Get the base directory from the configuration.

        Returns:
            str: The base directory as a normalized string.
        """
        # Here, the _config.paths.base_dir is stored as a string.
        return self._config.paths.base_dir

    def get_output_dir(self) -> str:
        """
        Get the output directory from the configuration.

        Returns:
            str: The output directory as a normalized string.
        """
        return self._config.paths.output_dir


def create_plugin() -> ConfigPlugin:
    """
    Create a new instance of the configuration plugin.

    Returns:
        A new ConfigPlugin instance.
    """
    return QuackConfigPlugin()
