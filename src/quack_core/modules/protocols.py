# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/modules/protocols.py
# module: quack_core.modules.protocols
# role: protocols
# neighbors: __init__.py, registry.py, discovery.py
# exports: QuackPluginMetadata, QuackPluginProtocol, PluginRegistryProtocol, PluginLoaderProtocol, CommandPluginProtocol, WorkflowPluginProtocol, ExtensionPluginProtocol, ProviderPluginProtocol (+1 more)
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===



"""
Plugin protocols for quack_core.

This module defines the Protocol interfaces for modules in the QuackCore system,
providing a common interface for all modules to implement.

Following Python 3.13 best practices:
- Uses native types and collections.abc
- Pydantic for validation
- Runtime checkable protocols for structural subtyping
"""

from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, Field

T = TypeVar("T")  # Generic return type


class QuackPluginMetadata(BaseModel):
    """
    Metadata for QuackCore modules.

    The plugin_id field provides a stable identifier that should match
    the entry point name or module path, ensuring deterministic registration.
    """

    plugin_id: str | None = Field(
        default=None,
        description="Stable plugin identifier (matches entry point name)",
    )
    name: str = Field(description="Human-readable plugin name")
    version: str = Field(description="Plugin version (semver recommended)")
    description: str = Field(description="Brief description of plugin functionality")
    author: str | None = Field(default=None, description="Plugin author")
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of capabilities this plugin provides",
    )


@runtime_checkable
class QuackPluginProtocol(Protocol):
    """
    Base protocol for all QuackCore modules.

    All modules must implement:
    - plugin_id: Stable identifier (typically matches entry point name)
    - name: Human-readable name
    - get_metadata(): Returns structured metadata
    """

    @property
    def plugin_id(self) -> str:
        """
        Get the stable identifier for this plugin.

        This should match the entry point name or module path used to load
        the plugin, ensuring deterministic registration and lookup.

        Returns:
            str: Plugin identifier (e.g., "fs", "paths", "config")
        """
        ...

    @property
    def name(self) -> str:
        """
        Get the human-readable name of the plugin.

        This may differ from plugin_id and is used for display purposes.

        Returns:
            str: Plugin display name
        """
        ...

    def get_metadata(self) -> QuackPluginMetadata:
        """
        Get structured metadata for the plugin.

        Returns:
            QuackPluginMetadata: Plugin metadata including id, version, capabilities
        """
        ...


class PluginRegistryProtocol(Protocol):
    """
    Protocol for a plugin registry.

    The registry maintains a collection of loaded modules, indexed by
    their stable plugin_id. All operations use plugin_id as the key.
    """

    def register(self, plugin: QuackPluginProtocol) -> None:
        """
        Register a plugin with the registry.

        Args:
            plugin: Plugin to register

        Raises:
            QuackPluginError: If plugin is already registered
        """
        ...

    def get_plugin(self, plugin_id: str) -> QuackPluginProtocol | None:
        """
        Get a plugin by its stable identifier.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            The plugin or None if not found
        """
        ...

    def list_ids(self) -> list[str]:
        """
        Get a list of all registered plugin IDs.

        Returns:
            List of plugin IDs (stable identifiers)
        """
        ...

    def list_plugins(self) -> list[str]:
        """
        Get a list of all registered plugin IDs.

        Alias for list_ids() for backward compatibility.

        Returns:
            List of plugin IDs
        """
        ...

    def is_registered(self, plugin_id: str) -> bool:
        """
        Check if a plugin is registered.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            True if the plugin is registered
        """
        ...

    def clear(self) -> None:
        """
        Clear all registered modules.

        This is primarily useful for testing to ensure a clean state.
        """
        ...


class PluginLoaderProtocol(Protocol):
    """
    Protocol for a plugin loader.

    The loader provides both discovery (listing available modules)
    and explicit loading (instantiating and registering specific modules).
    """

    def load_entry_points(
            self, group: str = "quack_core.modules"
    ) -> list[QuackPluginProtocol]:
        """
        Load modules from entry points.

        This method instantiates modules but does NOT register them.
        Use load_enabled_entry_points() for explicit loading with registration.

        Args:
            group: Entry point group to load from

        Returns:
            List of loaded plugin instances
        """
        ...

    def load_plugin(self, module_path: str) -> QuackPluginProtocol:
        """
        Load a plugin from a module path.

        Args:
            module_path: Path to the module containing the plugin

        Returns:
            The loaded plugin instance

        Raises:
            QuackPluginError: If plugin cannot be loaded
        """
        ...

    def load_plugins(self, modules: list[str]) -> list[QuackPluginProtocol]:
        """
        Load multiple modules from module paths.

        Args:
            modules: List of module paths

        Returns:
            List of loaded plugin instances
        """
        ...


@runtime_checkable
class CommandPluginProtocol(QuackPluginProtocol, Protocol):
    """
    Protocol for modules that provide commands.

    Command modules expose executable commands that can be invoked
    by name with arguments.
    """

    def list_commands(self) -> list[str]:
        """
        List all commands provided by this plugin.

        Returns:
            List of command names
        """
        ...

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """
        Get a command callable by name.

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
            Result of the command execution
        """
        ...


@runtime_checkable
class WorkflowPluginProtocol(QuackPluginProtocol, Protocol):
    """
    Protocol for modules that provide workflows.

    Workflow modules expose multi-step processes that can be
    invoked by name with arguments.
    """

    def list_workflows(self) -> list[str]:
        """
        List all workflows provided by this plugin.

        Returns:
            List of workflow names
        """
        ...

    def get_workflow(self, name: str) -> Callable[..., Any] | None:
        """
        Get a workflow callable by name.

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
            Result of the workflow execution
        """
        ...


@runtime_checkable
class ExtensionPluginProtocol(QuackPluginProtocol, Protocol):
    """
    Protocol for modules that extend functionality of other modules.

    Extension modules augment or modify the behavior of a target plugin.
    """

    def get_target_plugin(self) -> str:
        """
        Get the plugin_id of the plugin this extension targets.

        Returns:
            Plugin ID of the target plugin
        """
        ...

    def get_extensions(self) -> dict[str, Callable[..., Any]]:
        """
        Get all extensions provided by this plugin.

        Returns:
            Dictionary mapping extension name to extension function
        """
        ...


@runtime_checkable
class ProviderPluginProtocol(QuackPluginProtocol, Protocol):
    """
    Protocol for modules that provide services.

    Provider modules expose services that can be consumed by other
    parts of the system.
    """

    def get_services(self) -> dict[str, Any]:
        """
        Get all services provided by this plugin.

        Returns:
            Dictionary mapping service name to service object
        """
        ...

    def get_service(self, name: str) -> T | None:
        """
        Get a specific service by name.

        Args:
            name: Name of the service

        Returns:
            The service object or None if not found
        """
        ...


@runtime_checkable
class ConfigurablePluginProtocol(QuackPluginProtocol, Protocol):
    """
    Protocol for modules that can be configured.

    Configurable modules accept configuration dictionaries and
    can validate them against a schema.
    """

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the plugin.

        Args:
            config: Configuration dictionary

        Raises:
            ValueError: If configuration is invalid
        """
        ...

    def get_config_schema(self) -> dict[str, Any]:
        """
        Get the configuration schema for this plugin.

        Returns:
            Dictionary describing the configuration schema (JSON Schema format)
        """
        ...

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate a configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        ...
