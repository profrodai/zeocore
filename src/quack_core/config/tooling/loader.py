# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/tooling/loader.py
# module: quack_core.config.tooling.loader
# role: module
# neighbors: __init__.py, base.py, logger.py
# exports: load_tool_config, update_tool_config
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===



"""
Configuration loading utilities for QuackTools.

This module provides helpers to extract tool-specific config from
an EXISTING QuackConfig object.
"""

from collections.abc import Mapping
from typing import TypeVar

from quack_core.config.models import QuackConfig
from .base import QuackToolConfigModel

T = TypeVar("T", bound=QuackToolConfigModel)


def load_tool_config(
        config: QuackConfig,
        tool_name: str,
        config_model: type[T]
) -> T:
    """
    Extract and validate tool-specific config from the main QuackConfig.

    Args:
        config: The fully loaded QuackConfig object.
        tool_name: The tool name, e.g. 'quackmetadata'.
        config_model: The pydantic model class for the tool's config.

    Returns:
        An instance of the tool's config model.
    """
    # Ensure the tool entry exists in custom, if not, use empty dict to trigger defaults
    if tool_name not in config.custom:
        config.custom[tool_name] = {}

    tool_data = config.custom.get(tool_name, {})

    # Validate against the specific tool model
    # If tool_data is empty, this uses the model's defaults
    tool_config = config_model(**tool_data)

    # Write back the defaults to the main config so they are visible
    config.custom[tool_name] = tool_config.model_dump()

    return tool_config


def update_tool_config(
        config: QuackConfig,
        tool_name: str,
        new_data: Mapping
) -> None:
    """
    Update a tool's config section in the QuackConfig.

    Args:
        config: The QuackConfig object.
        tool_name: e.g. "quackmetadata".
        new_data: New dictionary to merge into config.custom[tool_name].
    """
    old_data = config.custom.get(tool_name, {})
    if isinstance(old_data, Mapping):
        updated = {**old_data, **new_data}
    else:
        updated = new_data
    config.custom[tool_name] = updated