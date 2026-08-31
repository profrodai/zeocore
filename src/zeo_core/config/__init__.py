"""
Configuration package for zeo_core.

This package provides configuration handling for ZeoCore.
It adheres to a strict "Kernel" philosophy:
1. No implicit I/O on import.
2. Configuration is loaded only when explicitly requested.
3. Deterministic behavior.
"""

from typing import Any

from zeo_core.config.dotenv_loader import load_dotenv_file

# Import all models directly for users of this package
from zeo_core.config.models import (
    GeneralConfig,
    LoggingConfig,
    PathsConfig,
    PluginsConfig,
    ZeoConfig,
)

# Import stateless utility functions
from zeo_core.config.utils import (
    get_config_value,
    get_env,
    validate_required_config,
)

# Initialize _config as None to ensure no implicit loading
_config: ZeoConfig | None = None


def get_config() -> ZeoConfig:
    """
    Get the global configuration instance (Legacy/Convenience).

    NOTE: Global state is discouraged in the Core Kernel.
    Prefer instantiating a ConfigService or using the Plugin architecture
    explicitly in new code.

    Returns:
        ZeoConfig: The global configuration object
    """
    global _config
    if _config is None:
        # Import here to avoid circular imports during module initialization
        from zeo_core.config.loader import load_config as _load_config

        _config = _load_config()
    return _config


class ConfigProxy:
    """
    Proxy class for the global configuration (Legacy).

    This allows both attribute access (config.paths.base_dir)
    and function call access (config().paths.base_dir).
    """

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 -- genuinely dynamic: forwards to an arbitrary attribute of the underlying config, return type depends on the attribute name
        """Forward attribute access to the actual config object."""
        return getattr(get_config(), name)

    def __call__(self) -> ZeoConfig:
        """Allow the proxy to be called as a function."""
        return get_config()


# Export a proxy instance for backward compatibility
config = ConfigProxy()


def load_config(
    config_path: str | None = None,
    merge_env: bool = True,
    merge_defaults: bool = True,
) -> ZeoConfig:
    """
    Load configuration from a file and merge with environment variables and defaults.

    This is the canonical entry point for configuration loading.

    Args:
        config_path: Optional path to a configuration file.
        merge_env: Whether to merge environment variables into the configuration.
        merge_defaults: Whether to merge default configuration values.

    Returns:
        A ZeoConfig instance built from the merged configuration.
    """
    from zeo_core.config.loader import load_config as _load_config

    return _load_config(config_path, merge_env, merge_defaults)


def merge_configs(base: ZeoConfig, override: dict[str, Any]) -> ZeoConfig:
    """
    Merge a base configuration with override values.

    Args:
        base: Base configuration.
        override: Override values.

    Returns:
        A merged ZeoConfig instance.
    """
    from zeo_core.config.loader import merge_configs as _merge_configs

    return _merge_configs(base, override)


__all__ = [
    # Classes
    "ZeoConfig",
    "GeneralConfig",
    "LoggingConfig",
    "PathsConfig",
    "PluginsConfig",
    # Functions
    "load_config",
    "load_dotenv_file",
    "merge_configs",
    "get_env",
    "get_config_value",
    "validate_required_config",
    "get_config",
    # Global instance accessor
    "config",
]
