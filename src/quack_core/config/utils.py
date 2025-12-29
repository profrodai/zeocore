# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/utils.py
# module: quack_core.config.utils
# role: utils
# neighbors: __init__.py, models.py, plugin.py, loader.py
# exports: get_env, get_config_value, validate_required_config, find_project_root
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===


"""
Utility functions for configuration management.

This module provides PURE, STATELESS utility functions.
It does NOT load configuration, read files (except for root finding),
or manage global state.
"""

import os
from collections.abc import Mapping
from typing import Any, TypeVar

T = TypeVar("T")


def get_env() -> str:
    """
    Get the current environment name.

    Returns:
        str: Current environment name (default: 'development')
    """
    return os.environ.get("QUACK_ENV", "development").lower()


def get_config_value(config: Any, path: str, default: T | None = None) -> T | None:
    """
    Get a configuration value by dot-separated path from a config object or dict.

    Args:
        config: Configuration object (QuackConfig) or dictionary.
        path: Dot-separated string of keys (e.g. 'logging.level').
        default: Default value if the path is not found.

    Returns:
        The configuration value if found; otherwise, the default.
    """
    # Convert Pydantic model to dict if necessary
    if hasattr(config, "model_dump"):
        current: Any = config.model_dump()
    else:
        current = config

    parts = path.split(".")

    for part in parts:
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return default
    return current


def validate_required_config(config: Any, required_keys: list[str]) -> list[str]:
    """
    Validate that the configuration contains all required keys.

    Args:
        config: Configuration object.
        required_keys: List of required configuration keys (in dot notation).

    Returns:
        list[str]: A list of keys that are missing.
    """
    missing: list[str] = []
    for key in required_keys:
        if get_config_value(config, key) is None:
            missing.append(key)
    return missing


def find_project_root() -> str:
    """
    Find the project root directory.

    Checks for markers: .git, pyproject.toml, setup.py, requirements.txt.

    Returns:
        str: The project root directory or current working directory.
    """
    cwd = os.getcwd()
    markers = [
        ".git",
        "pyproject.toml",
        "setup.py",
        "poetry.lock",
        "requirements.txt",
    ]

    current_dir = cwd
    while current_dir:
        for marker in markers:
            if os.path.exists(os.path.join(current_dir, marker)):
                return current_dir

        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            # Reached filesystem root
            break
        current_dir = parent

    return cwd