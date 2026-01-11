# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/plugin.py
# module: quack_core.config.plugin
# role: plugin
# neighbors: __init__.py, models.py, utils.py, loader.py
# exports: ConfigPlugin, QuackConfigPlugin, create_plugin
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===


"""
Plugin interface for the configuration module.

This module provides a LAZY configuration plugin.
Instantiation is cheap; loading is explicit.
"""

from typing import Any, Protocol, TypeVar

from quack_core.config.loader import load_config, merge_configs
from quack_core.config.models import QuackConfig
from quack_core.config.utils import get_config_value

T = TypeVar("T")


class ConfigPlugin(Protocol):
    """Protocol for configuration modules."""

    @property
    def name(self) -> str: ...

    def load_config(
        self,
        config_path: str | None = None,
        merge_env: bool = True,
        merge_defaults: bool = True,
    ) -> QuackConfig: ...

    def merge_configs(self, base: QuackConfig, override: dict[str, Any]) -> QuackConfig: ...

    def get_value(self, path: str, default: T | None = None) -> T | None: ...

    def get_base_dir(self) -> str: ...


class QuackConfigPlugin:
    """Implementation of the configuration plugin protocol."""

    def __init__(self) -> None:
        """
        Initialize the plugin.
        NOTE: Does NOT load config automatically.
        """
        self._config: QuackConfig | None = None

    @property
    def name(self) -> str:
        return "config"

    def load_config(
        self,
        config_path: str | None = None,
        merge_env: bool = True,
        merge_defaults: bool = True,
    ) -> QuackConfig:
        """
        Explicitly load the configuration.
        """
        self._config = load_config(
            config_path=config_path,
            merge_env=merge_env,
            merge_defaults=merge_defaults,
        )
        return self._config

    def merge_configs(self, base: QuackConfig, override: dict[str, Any]) -> QuackConfig:
        return merge_configs(base, override)

    def get_value(self, path: str, default: T | None = None) -> T | None:
        if self._config is None:
            # We could auto-load here, but strict kernel philosophy suggests
            # we should raise or return default if not initialized.
            # For developer experience, we'll raise to indicate setup order issues.
            raise RuntimeError(
                "ConfigPlugin: Config has not been loaded yet. Call load_config() first."
            )
        return get_config_value(self._config, path, default)

    def get_base_dir(self) -> str:
        if self._config is None:
            raise RuntimeError("ConfigPlugin: Config not loaded.")
        return self._config.paths.base_dir

    def get_output_dir(self) -> str:
        if self._config is None:
            raise RuntimeError("ConfigPlugin: Config not loaded.")
        return self._config.paths.output_dir


def create_plugin() -> ConfigPlugin:
    """Create a new instance of the configuration plugin."""
    return QuackConfigPlugin()
