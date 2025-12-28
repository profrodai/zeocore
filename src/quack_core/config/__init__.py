# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/__init__.py
# module: quack_core.config.__init__
# role: module
# neighbors: models.py, plugin.py, utils.py, loader.py
# exports: QuackConfig, GeneralConfig, LoggingConfig, PathsConfig, IntegrationsConfig, GoogleConfig, NotionConfig, PluginsConfig (+9 more)
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
Configuration package for quack_core.

This package provides configuration handling for QuackCore,
with support for loading from files, environment variables,
and merging configurations from different sources.
"""

from typing import Any, Optional

# Import all models directly for users of this package
from quack_core.config.models import (
    GeneralConfig,
    GoogleConfig,
    IntegrationsConfig,
    LoggingConfig,
    NotionConfig,
    PathsConfig,
    PluginsConfig,
    QuackConfig,
)

# Import utility functions but not loader yet
from quack_core.config.utils import (
    get_config_value,
    get_env,
    load_env_config,
    normalize_paths,
    validate_required_config,
)

# Initialize _config as None to enable lazy loading
_config: QuackConfig | None = None


def get_config() -> QuackConfig:
    """
    Get the global configuration instance.

    This function initializes the configuration on first access to avoid circular imports.

    Returns:
        QuackConfig: The global configuration object
    """
    global _config
    if _config is None:
        # Import here to avoid circular imports during module initialization
        from quack_core.config.loader import load_config as _load_config

        _config = _load_config()
    return _config


# Dynamically generated functions for both attribute and function access


class ConfigProxy:
    """
    Proxy class for the global configuration.

    This allows both attribute access (config.paths.base_dir)
    and function call access (config().paths.base_dir).
    """

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to the actual config object."""
        return getattr(get_config(), name)

    def __call__(self) -> QuackConfig:
        """Allow the proxy to be called as a function."""
        return get_config()


# Export a proxy instance for backward compatibility
config = ConfigProxy()


# Functions to be imported from loader
def load_config(
    config_path: str | None = None,
    merge_env: bool = True,
    merge_defaults: bool = True,
) -> QuackConfig:
    """
    Load configuration from a file and merge with environment variables and defaults.

    This is a forward declaration that imports the real function on first use.

    Args:
        config_path: Optional path to a configuration file.
        merge_env: Whether to merge environment variables into the configuration.
        merge_defaults: Whether to merge default configuration values.

    Returns:
        A QuackConfig instance built from the merged configuration.
    """
    from quack_core.config.loader import load_config as _load_config

    return _load_config(config_path, merge_env, merge_defaults)


def merge_configs(base: QuackConfig, override: dict[str, Any]) -> QuackConfig:
    """
    Merge a base configuration with override values.

    This is a forward declaration that imports the real function on first use.

    Args:
        base: Base configuration.
        override: Override values.

    Returns:
        A merged QuackConfig instance.
    """
    from quack_core.config.loader import merge_configs as _merge_configs

    return _merge_configs(base, override)


__all__ = [
    # Classes
    "QuackConfig",
    "GeneralConfig",
    "LoggingConfig",
    "PathsConfig",
    "IntegrationsConfig",
    "GoogleConfig",
    "NotionConfig",
    "PluginsConfig",
    # Functions
    "load_config",
    "merge_configs",
    "get_env",
    "load_env_config",
    "get_config_value",
    "validate_required_config",
    "normalize_paths",
    "get_config",
    # Global instance accessor
    "config",
]
