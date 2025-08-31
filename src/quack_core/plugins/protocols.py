# quack-core/src/quack-core/plugins/protocols.py
"""
Plugin protocols for quack_core.

This module defines the Protocol interfaces for plugins in the QuackCore system,
providing a common interface for all plugins to implement.
"""

from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, Field

T = TypeVar("T")  # Generic return type


class QuackPluginMetadata(BaseModel):
    """Metadata for QuackCore plugins."""

    name: str
    version: str
    description: str
    author: str | None = None
    capabilities: list[str] = Field(default_factory=list)


@runtime_checkable
class QuackPluginProtocol(Protocol):
    """Base protocol for all QuackCore plugins."""

    @property
    def name(self) -> str:
        """
        Get the name of the plugin.

        Returns:
            str: Plugin name
        """
        ...

    def get_metadata(self) -> QuackPluginMetadata:
        """
        Get metadata for the plugin.

        Returns:
            QuackPluginMetadata: Plugin metadata
        """
        ...


class PluginRegistryProtocol(Protocol):
    """Protocol for a plugin registry."""

    def register(self, plugin: QuackPluginProtocol) -> None:
        """
        Register a plugin with the registry.

        Args:
            plugin: Plugin to register
        """
        ...

    def get_plugin(self, name: str) -> QuackPluginProtocol | None:
        """
        Get a plugin by name.

        Args:
            name: Name of the plugin

        Returns:
            The plugin or None if not found
        """
        ...

    def list_plugins(self) -> list[str]:
        """
        Get a list of all registered plugin names.

        Returns:
            List of plugin names
        """
        ...

    def is_registered(self, name: str) -> bool:
        """
        Check if a plugin is registered.

        Args:
            name: Name of the plugin

        Returns:
            True if the plugin is registered
        """
        ...


class PluginLoaderProtocol(Protocol):
    """Protocol for a plugin loader."""

    def load_entry_points(
        self, group: str = "quack-core.plugins"
    ) -> list[QuackPluginProtocol]:
        """
        Load plugins from entry points.

        Args:
            group: Entry point group to load from

        Returns:
            List of loaded plugins
        """
        ...

    def load_plugin(self, module_path: str) -> QuackPluginProtocol:
        """
        Load a plugin from a module path.

        Args:
            module_path: Path to the module containing the plugin

        Returns:
            The loaded plugin
        """
        ...

    def load_plugins(self, modules: list[str]) -> list[QuackPluginProtocol]:
        """
        Load multiple plugins from module paths.

        Args:
            modules: List of module paths

        Returns:
            List of loaded plugins
        """
        ...


@runtime_checkable
class CommandPluginProtocol(QuackPluginProtocol, Protocol):
    """Protocol for plugins that provide commands."""

    def list_commands(self) -> list[str]:
        """
        List all commands provided by this plugin.

        Returns:
            List of command names
        """
        ...

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """
        Get a command by name.

        Args:
            name: Name of the command

        Returns:
            The command function or None if not found
        """
        ...

    def execute_command(self, name: str, *args: object, **kwargs: object) -> T:
        """
        Execute a command.

        Args:
            name: Name of the command
            *args: Positional arguments to pass to the command
            **kwargs: Keyword arguments to pass to the command

        Returns:
            Result of the command
        """
        ...


@runtime_checkable
class WorkflowPluginProtocol(QuackPluginProtocol, Protocol):
    """Protocol for plugins that provide workflows."""

    def list_workflows(self) -> list[str]:
        """
        List all workflows provided by this plugin.

        Returns:
            List of workflow names
        """
        ...

    def get_workflow(self, name: str) -> Callable[..., Any] | None:
        """
        Get a workflow by name.

        Args:
            name: Name of the workflow

        Returns:
            The workflow function or None if not found
        """
        ...

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> T:
        """
        Execute a workflow.

        Args:
            name: Name of the workflow
            *args: Positional arguments to pass to the workflow
            **kwargs: Keyword arguments to pass to the workflow

        Returns:
            Result of the workflow
        """
        ...


@runtime_checkable
class ExtensionPluginProtocol(QuackPluginProtocol, Protocol):
    """Protocol for plugins that extend functionality of other plugins."""

    def get_target_plugin(self) -> str:
        """
        Get the name of the plugin this extension targets.

        Returns:
            Name of the target plugin
        """
        ...

    def get_extensions(self) -> dict[str, Callable[..., Any]]:
        """
        Get all extensions provided by this plugin.

        Returns:
            Dictionary of extension name to extension function
        """
        ...


@runtime_checkable
class ProviderPluginProtocol(QuackPluginProtocol, Protocol):
    """Protocol for plugins that provide services."""

    def get_services(self) -> dict[str, Any]:
        """
        Get all services provided by this plugin.

        Returns:
            Dictionary of service name to service object
        """
        ...

    def get_service(self, name: str) -> T | None:
        """
        Get a service by name.

        Args:
            name: Name of the service

        Returns:
            The service or None if not found
        """
        ...


@runtime_checkable
class ConfigurablePluginProtocol(QuackPluginProtocol, Protocol):
    """Protocol for plugins that can be configured."""

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the plugin.

        Args:
            config: Configuration dictionary
        """
        ...

    def get_config_schema(self) -> dict[str, Any]:
        """
        Get the configuration schema for this plugin.

        Returns:
            Dictionary describing the configuration schema
        """
        ...

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate a configuration dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        ...
