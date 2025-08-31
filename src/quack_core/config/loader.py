# quack-core/src/quack-core/config/loader.py
"""
Configuration loading utilities for quack_core.

This module provides utilities for loading and merging configurations
from various sources, with support for environment-specific overrides.
"""

import os
from typing import Any, TypeVar

import yaml

from quack_core.config.models import QuackConfig
from quack_core.errors import QuackConfigurationError, wrap_io_errors
from quack_core.logging import get_logger

T = TypeVar("T")  # Generic type for flexible typing

# Default configuration values to be merged when merge_defaults is True.
DEFAULT_CONFIG_VALUES: dict[str, Any] = {
    "logging": {
        "level": "INFO",
        "file": "logs/quack-core.log",
    },
    "paths": {
        "base_dir": os.path.join(os.path.expanduser("~"), ".quack-core"),
    },
    "general": {
        "project_name": "QuackCore",
    },
}

DEFAULT_CONFIG_LOCATIONS = [
    "./quack_config.yaml",
    "./config/quack_config.yaml",
    "~/.quack/config.yaml",
    "/etc/quack/config.yaml",
]

ENV_PREFIX = "QUACK_"

logger = get_logger(__name__)


@wrap_io_errors
def load_yaml_config(path: str) -> dict[str, Any]:
    """
    Load a YAML configuration file.

    Args:
        path: Path to YAML file.

    Returns:
        Dictionary with configuration values.

    Raises:
        QuackConfigurationError: If the file cannot be loaded.
    """
    try:
        # Use direct file operations to avoid circular imports with fs module
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            content = f.read()

        config = yaml.safe_load(content)
        return config or {}
    except (yaml.YAMLError, OSError) as e:
        raise QuackConfigurationError(f"Failed to load YAML config: {e}", path) from e


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary.
        override: Override dictionary.

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _is_float(value: str) -> bool:
    """
    Check if the string represents a float number.

    Args:
        value: The string to check.

    Returns:
        True if the string can be interpreted as a float, False otherwise.
    """
    try:
        float(value)
        return "." in value and not value.endswith(".")
    except ValueError:
        return False


def _convert_env_value(value: str) -> bool | int | float | str:
    """
    Convert an environment variable string value to an appropriate type.

    Args:
        value: The environment variable value as string.

    Returns:
        The value converted to bool, int, float, or left as string.
    """
    v_lower = value.lower()
    if v_lower == "true":
        return True
    if v_lower == "false":
        return False
    if value.startswith("-") and value[1:].isdigit():
        return int(value)
    if value.isdigit():
        return int(value)
    if _is_float(value):
        return float(value)
    return value


def _get_env_config() -> dict[str, Any]:
    """
    Get configuration from environment variables.

    Environment variables should be in the format:
    QUACK_SECTION__KEY=value

    Returns:
        Dictionary with configuration values.
    """
    config: dict[str, Any] = {}
    for key, value in os.environ.items():
        if key.startswith(ENV_PREFIX):
            key_parts = key[len(ENV_PREFIX) :].lower().split("__")
            if len(key_parts) < 2:
                continue
            typed_value = _convert_env_value(value)
            current = config
            for i, part in enumerate(key_parts):
                if i == len(key_parts) - 1:
                    current[part] = typed_value
                else:
                    current.setdefault(part, {})
                    current = current[part]
    return config


def find_config_file() -> str | None:
    """
    Find a configuration file in standard locations.

    Returns:
        The path to the configuration file if found, or None.
    """
    # Check environment variable first.
    if config_path := os.environ.get("QUACK_CONFIG"):
        expanded = os.path.expanduser(config_path)
        if os.path.exists(expanded):
            return expanded

    # Check default locations.
    for location in DEFAULT_CONFIG_LOCATIONS:
        expanded = os.path.expanduser(location)
        if os.path.exists(expanded):
            return expanded

    # Try to find project root and check for config there.
    try:
        # Import locally to avoid circular imports
        from quack_core.paths import service as paths

        root = paths.get_project_root()
        for name in ["quack_config.yaml", "config/quack_config.yaml"]:
            candidate = os.path.join(root, name)
            if os.path.exists(candidate):
                return candidate
    except Exception as e:
        logger.debug("Failed to find project root: %s", e)

    return None


def load_config(
    config_path: str | None = None,
    merge_env: bool = True,
    merge_defaults: bool = True,
) -> QuackConfig:
    """
    Load configuration from a file and merge with environment variables and defaults.

    Args:
        config_path: Optional path to a configuration file.
        merge_env: Whether to merge environment variables into the configuration.
        merge_defaults: Whether to merge default configuration values.

    Returns:
        A QuackConfig instance built from the merged configuration.

    Raises:
        QuackConfigurationError: If no configuration could be loaded.
    """
    config_dict: dict[str, Any] = {}

    if config_path:
        expanded = os.path.expanduser(config_path)
        if not os.path.exists(expanded):
            raise QuackConfigurationError(
                f"Configuration file not found: {expanded}", expanded
            )
        config_dict = load_yaml_config(expanded)
    else:
        found = find_config_file()
        if found:
            config_dict = load_yaml_config(found)

    if merge_env:
        env_config = _get_env_config()
        config_dict = _deep_merge(config_dict, env_config)

    if merge_defaults:
        config_dict = _deep_merge(DEFAULT_CONFIG_VALUES, config_dict)

    return QuackConfig.model_validate(config_dict)


def merge_configs(base: QuackConfig, override: dict[str, Any]) -> QuackConfig:
    """
    Merge a base configuration with override values.

    Args:
        base: Base configuration.
        override: Override values.

    Returns:
        A merged QuackConfig instance.
    """
    base_dict = base.model_dump()
    merged = _deep_merge(base_dict, override)
    return QuackConfig.model_validate(merged)
