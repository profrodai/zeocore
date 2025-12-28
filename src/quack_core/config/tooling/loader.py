# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/tooling/loader.py
# module: quack_core.config.tooling.loader
# role: module
# neighbors: __init__.py, base.py, logger.py
# exports: load_tool_config, update_tool_config
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""
Configuration loading utilities for QuackTools.

This module provides utilities for loading and updating QuackTool-specific
configurations within the main QuackConfig object.
"""

from collections.abc import Mapping

from quack_core.config import load_config
from quack_core.config.models import QuackConfig

from .base import QuackToolConfigModel


def load_tool_config(
    tool_name: str,
    config_model: type[QuackToolConfigModel],
    config_path: str | None = None
) -> tuple[QuackConfig, QuackToolConfigModel]:
    """
    Load and inject tool-specific config into QuackConfig.

    If the tool doesn't already have config stored in quack_config.custom,
    this function will add the default values from config_model.

    Args:
        tool_name: The tool name, e.g. 'quackmetadata'
        config_model: The pydantic model class for the tool's config
        config_path: Optional path to a QuackConfig file

    Returns:
        Tuple of (QuackConfig object, tool-specific config model)
    """
    config = load_config(config_path)

    if tool_name not in config.custom:
        config.custom[tool_name] = config_model().model_dump()

    tool_data = config.custom.get(tool_name, {})
    tool_config = config_model(**tool_data)

    return config, tool_config


def update_tool_config(
    config: QuackConfig,
    tool_name: str,
    new_data: Mapping
) -> None:
    """
    Update a tool's config section in the QuackConfig.

    Args:
        config: The QuackConfig object
        tool_name: e.g. "quackmetadata"
        new_data: New dictionary to merge into config.custom[tool_name]
    """
    old_data = config.custom.get(tool_name, {})
    if isinstance(old_data, Mapping):
        updated = {**old_data, **new_data}
    else:
        updated = new_data
    config.custom[tool_name] = updated
