# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/models.py
# module: quack_core.config.models
# role: models
# neighbors: __init__.py, plugin.py, utils.py, loader.py
# exports: LoggingConfig, PathsConfig, GeneralConfig, PluginsConfig, QuackConfig
# git_branch: refactor/toolkitWorkflow
# git_commit: 9e6703a
# === QV-LLM:END ===


"""
Configuration models for quack_core.

This module provides Pydantic models for configuration management.
"""

import sys
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")  # Generic type for flexible typing


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    VALID_LEVELS: ClassVar[list[str]] = [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]

    level: str = Field(default="INFO", description="Logging level")
    file: str | None = Field(default=None, description="Log file path")
    console: bool = Field(default=True, description="Log to console")

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate and normalize logging level."""
        level_name = v.upper()
        if level_name not in cls.VALID_LEVELS:
            return "INFO"
        return level_name

    def setup_logging(self) -> None:
        """Set up logging based on configuration."""
        from quack_core.lib.logging import LOG_LEVELS, configure_logger

        level_name = self.level.upper()
        level = LOG_LEVELS.get(level_name, LOG_LEVELS["INFO"])

        logger = configure_logger("quack-core", level=level, log_file=self.file)

        if not self.console:
            for handler in logger.handlers[:]:
                import logging
                # Check identity of stream to safely target stderr
                if isinstance(handler,
                              logging.StreamHandler) and handler.stream is sys.stderr:
                    logger.removeHandler(handler)


class PathsConfig(BaseModel):
    """
    Configuration for file paths.

    NOTE: Paths are normalized in config.loader; models do not normalize.
    """

    base_dir: str = Field(default="./", description="Base directory")
    output_dir: str = Field(default="./output", description="Output directory")
    assets_dir: str = Field(default="./assets", description="Assets directory")
    data_dir: str = Field(default="./data", description="Data directory")
    temp_dir: str = Field(default="./temp", description="Temporary directory")


class GeneralConfig(BaseModel):
    """General configuration settings."""

    project_name: str = Field(default="QuackCore", description="Name of the project")
    environment: str = Field(
        default="development",
        description="Environment (development, test, production)",
    )
    debug: bool = Field(default=False, description="Debug mode")
    verbose: bool = Field(default=False, description="Verbose output")


class PluginsConfig(BaseModel):
    """Configuration for modules."""

    enabled: list[str] = Field(
        default_factory=list, description="List of enabled modules"
    )
    disabled: list[str] = Field(
        default_factory=list, description="List of disabled modules"
    )
    paths: list[str] = Field(
        default_factory=list, description="Additional plugin search paths"
    )


class QuackConfig(BaseModel):
    """Main configuration for quack_core."""

    general: GeneralConfig = Field(
        default_factory=GeneralConfig, description="General settings"
    )
    paths: PathsConfig = Field(default_factory=PathsConfig, description="Path settings")
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging settings"
    )
    integrations: dict[str, Any] = Field(default_factory=dict,
                                         description="Integration settings")

    plugins: PluginsConfig = Field(
        default_factory=PluginsConfig, description="Plugin settings"
    )
    custom: dict[str, Any] = Field(
        default_factory=dict, description="Custom configuration settings"
    )

    def setup_logging(self) -> None:
        """Set up logging based on configuration."""
        self.logging.setup_logging()

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """
        Convert the configuration to a dictionary.

        Args:
            **kwargs: Arguments passed to model_dump() (e.g. exclude_none=True)

        Returns:
            dict[str, Any]: Dictionary representation of the configuration
        """
        return self.model_dump(**kwargs)

    def get_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled."""
        if plugin_name in self.plugins.disabled:
            return False
        if self.plugins.enabled and plugin_name not in self.plugins.enabled:
            return False
        return True

    def get_custom(self, key: str, default: T | None = None) -> T | None:
        """
        Get a custom configuration value.

        Args:
            key: The configuration key
            default: Default value if the key doesn't exist

        Returns:
            The configuration value
        """
        return self.custom.get(key, default)
