"""
Configuration loading utilities for ZeoTools.

This module provides helpers to extract tool-specific config from
an EXISTING ZeoConfig object.
"""

from collections.abc import Mapping
from typing import TypeVar

from zeo_core.config.models import ZeoConfig

from .base import ZeoToolConfigModel

T = TypeVar("T", bound=ZeoToolConfigModel)


def load_tool_config(config: ZeoConfig, tool_name: str, config_model: type[T]) -> T:
    """
    Extract and validate tool-specific config from the main ZeoConfig.

    Args:
        config: The fully loaded ZeoConfig object.
        tool_name: The tool name, e.g. 'zeometadata'.
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


def update_tool_config(config: ZeoConfig, tool_name: str, new_data: Mapping) -> None:
    """
    Update a tool's config section in the ZeoConfig.

    Args:
        config: The ZeoConfig object.
        tool_name: e.g. "zeometadata".
        new_data: New dictionary to merge into config.custom[tool_name].
    """
    old_data = config.custom.get(tool_name, {})
    updated: Mapping = (
        {**old_data, **new_data} if isinstance(old_data, Mapping) else new_data
    )
    config.custom[tool_name] = updated
