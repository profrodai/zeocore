# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/loader.py
# module: quack_core.config.loader
# role: module
# neighbors: __init__.py, models.py, plugin.py, utils.py
# exports: load_yaml_config, find_config_file, load_config, merge_configs
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===


"""
Configuration loading authority for quack_core.

This module is the SINGLE source of truth for:
1. Loading configuration from YAML.
2. Merging Environment variables.
3. Merging Defaults.
4. Normalizing paths.
5. Validating the final model.

It contains NO side effects (logging, file creation) other than reading the config file.
"""

import os
from typing import Any, TypeVar

import yaml
from quack_core.config.models import QuackConfig
from quack_core.config.utils import find_project_root
from quack_core.lib.errors import QuackConfigurationError, wrap_io_errors

T = TypeVar("T")

# Default configuration values
# NOTE: logging.file is None by default to avoid polluting project roots.
DEFAULT_CONFIG_VALUES: dict[str, Any] = {
    "logging": {
        "level": "INFO",
        "file": None,
        "console": True,
    },
    "paths": {
        # base_dir is calculated dynamically if not provided
        "output_dir": "output",
        "assets_dir": "assets",
        "data_dir": "data",
        "temp_dir": "temp",
    },
    "general": {
        "project_name": "QuackCore",
        "environment": "development",
        "debug": False,
    },
    "plugins": {
        "enabled": [],
        "disabled": [],
        "paths": [],
    },
}

DEFAULT_CONFIG_LOCATIONS = [
    "./quack_config.yaml",
    "./config/quack_config.yaml",
    "~/.quack/config.yaml",
    "/etc/quack/config.yaml",
]

ENV_PREFIX = "QUACK_"


@wrap_io_errors
def load_yaml_config(path: str) -> dict[str, Any]:
    """
    Load a YAML configuration file.

    Args:
        path: Path to YAML file.

    Returns:
        Dictionary with configuration values.

    Raises:
        QuackConfigurationError: If the file cannot be loaded/parsed.
    """
    try:
        # Use direct file operations to avoid circular imports
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


def _normalize_path(value: str, base_dir: str = "./") -> str:
    """Normalize a path relative to a base directory."""
    if os.path.isabs(value):
        return os.path.normpath(value)
    return os.path.normpath(os.path.join(base_dir, value))


def _normalize_config_paths(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize all paths in the configuration dictionary.
    This creates absolute paths based on 'paths.base_dir'.

    CRITICAL: Only normalizes Kernel-known paths.
    Domain/Vendor paths must be normalized by their respective integrations.
    """
    # 1. Determine Base Dir
    paths_section = config_dict.get("paths", {})
    base_dir = paths_section.get("base_dir")

    if not base_dir:
        base_dir = find_project_root()

    # Ensure base_dir is absolute
    base_dir = os.path.abspath(os.path.expanduser(base_dir))
    paths_section["base_dir"] = base_dir

    # 2. Normalize standard path keys
    for key in ["output_dir", "assets_dir", "data_dir", "temp_dir"]:
        if key in paths_section and isinstance(paths_section[key], str):
            paths_section[key] = _normalize_path(paths_section[key], base_dir)

    # 3. Normalize logging file
    logging_section = config_dict.get("logging", {})
    if "file" in logging_section and logging_section["file"]:
        logging_section["file"] = _normalize_path(logging_section["file"], base_dir)

    # 4. Normalize plugin paths
    plugins_section = config_dict.get("plugins", {})
    if "paths" in plugins_section and isinstance(plugins_section["paths"], list):
        plugins_section["paths"] = [
            _normalize_path(p, base_dir) for p in plugins_section["paths"]
        ]

    return config_dict


def _is_float(value: str) -> bool:
    """Check if string represents a float."""
    try:
        float(value)
        return "." in value and not value.endswith(".")
    except ValueError:
        return False


def _convert_env_value(value: str) -> bool | int | float | str:
    """
    Convert an environment variable string value to an appropriate type.
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
    Format: QUACK_SECTION__KEY=value
    """
    config: dict[str, Any] = {}
    for key, value in os.environ.items():
        if key.startswith(ENV_PREFIX):
            key_parts = key[len(ENV_PREFIX):].lower().split("__")
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
    """Find a configuration file in standard locations."""
    # Check environment variable
    if config_path := os.environ.get("QUACK_CONFIG"):
        expanded = os.path.expanduser(config_path)
        if os.path.exists(expanded):
            return expanded

    # Check default locations
    for location in DEFAULT_CONFIG_LOCATIONS:
        expanded = os.path.expanduser(location)
        if os.path.exists(expanded):
            return expanded

    # Check project root
    root = find_project_root()
    for name in ["quack_config.yaml", "config/quack_config.yaml"]:
        candidate = os.path.join(root, name)
        if os.path.exists(candidate):
            return candidate

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
        merge_env: Whether to merge environment variables.
        merge_defaults: Whether to merge default values.

    Returns:
        A QuackConfig instance.

    Raises:
        QuackConfigurationError: If explicit config path is invalid.
    """
    # 1. Start with empty or defaults
    config_dict: dict[str, Any] = (
        _deep_merge({}, DEFAULT_CONFIG_VALUES) if merge_defaults else {}
    )

    # 2. Load YAML (if found/provided)
    loaded_yaml: dict[str, Any] = {}
    if config_path:
        expanded = os.path.expanduser(config_path)
        if not os.path.exists(expanded):
            raise QuackConfigurationError(
                f"Configuration file not found: {expanded}", expanded
            )
        loaded_yaml = load_yaml_config(expanded)
    else:
        found = find_config_file()
        if found:
            loaded_yaml = load_yaml_config(found)

    config_dict = _deep_merge(config_dict, loaded_yaml)

    # 3. Merge Env
    if merge_env:
        env_config = _get_env_config()
        config_dict = _deep_merge(config_dict, env_config)

    # 4. Normalize Paths (The single source of path truth)
    config_dict = _normalize_config_paths(config_dict)

    # 5. Validate and Return
    return QuackConfig.model_validate(config_dict)


def merge_configs(base: QuackConfig, override: dict[str, Any]) -> QuackConfig:
    """Merge a base QuackConfig object with an override dictionary."""
    base_dict = base.model_dump()
    merged = _deep_merge(base_dict, override)

    # Re-normalize just in case overrides introduced relative paths
    merged = _normalize_config_paths(merged)

    return QuackConfig.model_validate(merged)
