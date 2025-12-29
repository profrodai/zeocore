# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/modules/registry.py
# module: quack_core.modules.registry
# role: module
# neighbors: __init__.py, protocols.py, discovery.py
# exports: PluginRegistry
# git_branch: refactor/toolkitWorkflow
# git_commit: 21647d6
# === QV-LLM:END ===



"""
Plugin registry for quack_core.

This module provides a registry for managing QuackCore modules, using
stable plugin_id values as keys for deterministic behavior.

Following Python 3.13 best practices:
- Clear separation of concerns
- Type hints for all public APIs
- Structured error handling
- Thread-safe operations where needed
"""

from typing import TypeVar

from quack_core.lib.errors import QuackPluginError
from quack_core.lib.logging import LOG_LEVELS, LogLevel, get_logger
from quack_core.modules.protocols import (
    CommandPluginProtocol,
    ExtensionPluginProtocol,
    ProviderPluginProtocol,
    QuackPluginProtocol,
    WorkflowPluginProtocol,
)

T = TypeVar("T")  # Generic for return types


class PluginRegistry:
    """
    Registry for QuackCore modules.

    The registry maintains a collection of loaded modules, indexed by their
    stable plugin_id. This ensures deterministic behavior and prevents
    conflicts from name collisions.

    Key design principles:
    - plugin_id is the primary key (stable, matches entry point name)
    - name is for display purposes only
    - Registration is explicit, never automatic
    - Clear state management for testing
    """

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        """
        Initialize the plugin registry.

        Args:
            log_level: Logging level for registry operations
        """
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)

        # Main plugin registry (keyed by plugin_id)
        self._plugins: dict[str, QuackPluginProtocol] = {}

        # Type-specific registries (keyed by plugin_id)
        self._command_plugins: dict[str, CommandPluginProtocol] = {}
        self._workflow_plugins: dict[str, WorkflowPluginProtocol] = {}
        self._extension_plugins: dict[str, ExtensionPluginProtocol] = {}
        self._provider_plugins: dict[str, ProviderPluginProtocol] = {}

        # Lookup registries for fast access
        # Commands and workflows map from their name to the providing plugin
        self._commands: dict[str, CommandPluginProtocol] = {}
        self._workflows: dict[str, WorkflowPluginProtocol] = {}
        # Extensions map from target plugin_id to list of extension modules
        self._extensions: dict[str, list[ExtensionPluginProtocol]] = {}

    def _get_plugin_id(self, plugin: QuackPluginProtocol) -> str:
        """
        Get the stable plugin_id from a plugin.

        Handles backward compatibility for modules that don't yet implement
        plugin_id by falling back to name with a warning.

        Args:
            plugin: Plugin to get ID from

        Returns:
            The plugin_id (or name as fallback)
        """
        # Try to get plugin_id first
        if hasattr(plugin, "plugin_id"):
            plugin_id = plugin.plugin_id
            if plugin_id:
                return plugin_id

        # Fallback to name with warning
        self.logger.warning(
            f"Plugin {plugin.name} does not implement plugin_id, "
            f"using name as fallback. This may cause instability."
        )
        return plugin.name

    def register(self, plugin: QuackPluginProtocol) -> None:
        """
        Register a plugin with the registry.

        Args:
            plugin: Plugin to register

        Raises:
            QuackPluginError: If plugin is already registered
        """
        plugin_id = self._get_plugin_id(plugin)

        if plugin_id in self._plugins:
            raise QuackPluginError(
                f"Plugin '{plugin_id}' is already registered",
                plugin_name=plugin_id,
            )

        # Register in main registry
        self._plugins[plugin_id] = plugin
        self.logger.debug(f"Registered plugin: {plugin_id} (name: {plugin.name})")

        # Register in type-specific registries
        self._register_by_type(plugin, plugin_id)

    def _register_by_type(
            self, plugin: QuackPluginProtocol, plugin_id: str
    ) -> None:
        """
        Register the plugin in appropriate type-specific registries.

        Args:
            plugin: Plugin to register
            plugin_id: Stable plugin identifier
        """
        if isinstance(plugin, CommandPluginProtocol):
            self._command_plugins[plugin_id] = plugin
            self._register_commands(plugin, plugin_id)

        if isinstance(plugin, WorkflowPluginProtocol):
            self._workflow_plugins[plugin_id] = plugin
            self._register_workflows(plugin, plugin_id)

        if isinstance(plugin, ExtensionPluginProtocol):
            self._extension_plugins[plugin_id] = plugin
            self._register_extension(plugin, plugin_id)

        if isinstance(plugin, ProviderPluginProtocol):
            self._provider_plugins[plugin_id] = plugin

    def _register_commands(
            self, plugin: CommandPluginProtocol, plugin_id: str
    ) -> None:
        """
        Register commands provided by a command plugin.

        Args:
            plugin: Command plugin to register
            plugin_id: Stable plugin identifier
        """
        commands = plugin.list_commands()
        for command in commands:
            if command in self._commands:
                existing_plugin_id = self._get_plugin_id(self._commands[command])
                self.logger.warning(
                    f"Command '{command}' from plugin '{plugin_id}' "
                    f"overrides existing implementation from '{existing_plugin_id}'"
                )
            self._commands[command] = plugin

        self.logger.debug(
            f"Registered command plugin '{plugin_id}' with commands: {commands}"
        )

    def _register_workflows(
            self, plugin: WorkflowPluginProtocol, plugin_id: str
    ) -> None:
        """
        Register workflows provided by a workflow plugin.

        Args:
            plugin: Workflow plugin to register
            plugin_id: Stable plugin identifier
        """
        workflows = plugin.list_workflows()
        for workflow in workflows:
            if workflow in self._workflows:
                existing_plugin_id = self._get_plugin_id(self._workflows[workflow])
                self.logger.warning(
                    f"Workflow '{workflow}' from plugin '{plugin_id}' "
                    f"overrides existing implementation from '{existing_plugin_id}'"
                )
            self._workflows[workflow] = plugin

        self.logger.debug(
            f"Registered workflow plugin '{plugin_id}' with workflows: {workflows}"
        )

    def _register_extension(
            self, plugin: ExtensionPluginProtocol, plugin_id: str
    ) -> None:
        """
        Register an extension plugin for a target plugin.

        Args:
            plugin: Extension plugin to register
            plugin_id: Stable plugin identifier
        """
        target = plugin.get_target_plugin()
        self._extensions.setdefault(target, []).append(plugin)
        self.logger.debug(
            f"Registered extension plugin '{plugin_id}' targeting '{target}'"
        )

    def unregister(self, plugin_id: str) -> None:
        """
        Unregister a plugin by its ID.

        Args:
            plugin_id: Stable plugin identifier

        Raises:
            QuackPluginError: If plugin is not registered
        """
        if plugin_id not in self._plugins:
            raise QuackPluginError(
                f"Plugin '{plugin_id}' is not registered",
                plugin_name=plugin_id,
            )

        plugin = self._plugins.pop(plugin_id)
        self._unregister_by_type(plugin, plugin_id)

        self.logger.debug(f"Unregistered plugin: {plugin_id}")

    def _unregister_by_type(
            self, plugin: QuackPluginProtocol, plugin_id: str
    ) -> None:
        """
        Remove the plugin from type-specific registries.

        Args:
            plugin: Plugin to unregister
            plugin_id: Stable plugin identifier
        """
        if isinstance(plugin, CommandPluginProtocol):
            self._command_plugins.pop(plugin_id, None)
            for command in plugin.list_commands():
                # Only remove if this plugin still owns the command
                if command in self._commands:
                    owner_id = self._get_plugin_id(self._commands[command])
                    if owner_id == plugin_id:
                        self._commands.pop(command, None)

        if isinstance(plugin, WorkflowPluginProtocol):
            self._workflow_plugins.pop(plugin_id, None)
            for workflow in plugin.list_workflows():
                # Only remove if this plugin still owns the workflow
                if workflow in self._workflows:
                    owner_id = self._get_plugin_id(self._workflows[workflow])
                    if owner_id == plugin_id:
                        self._workflows.pop(workflow, None)

        if isinstance(plugin, ExtensionPluginProtocol):
            self._extension_plugins.pop(plugin_id, None)
            target = plugin.get_target_plugin()
            if target in self._extensions:
                self._extensions[target] = [
                    p for p in self._extensions[target]
                    if self._get_plugin_id(p) != plugin_id
                ]
                if not self._extensions[target]:
                    self._extensions.pop(target, None)

        if isinstance(plugin, ProviderPluginProtocol):
            self._provider_plugins.pop(plugin_id, None)

    def clear(self) -> None:
        """
        Clear all registered modules.

        This removes all modules from the registry and resets all internal
        state. Primarily useful for testing to ensure a clean slate.
        """
        self._plugins.clear()
        self._command_plugins.clear()
        self._workflow_plugins.clear()
        self._extension_plugins.clear()
        self._provider_plugins.clear()
        self._commands.clear()
        self._workflows.clear()
        self._extensions.clear()
        self.logger.debug("Cleared all registered modules")

    def execute_command(
            self, command: str, *args: object, **kwargs: object
    ) -> object:
        """
        Execute a command by name.

        Args:
            command: Name of the command
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the command execution

        Raises:
            QuackPluginError: If the command is not found
        """
        plugin = self._commands.get(command)
        if not plugin:
            raise QuackPluginError(
                f"Command '{command}' not found",
                plugin_name=None,
            )
        return plugin.execute_command(command, *args, **kwargs)

    def execute_workflow(
            self, workflow: str, *args: object, **kwargs: object
    ) -> object:
        """
        Execute a workflow by name.

        Args:
            workflow: Name of the workflow
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the workflow execution

        Raises:
            QuackPluginError: If the workflow is not found
        """
        plugin = self._workflows.get(workflow)
        if not plugin:
            raise QuackPluginError(
                f"Workflow '{workflow}' not found",
                plugin_name=None,
            )
        return plugin.execute_workflow(workflow, *args, **kwargs)

    def get_plugin(self, plugin_id: str) -> QuackPluginProtocol | None:
        """
        Get a plugin by its stable identifier.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            The plugin or None if not found
        """
        return self._plugins.get(plugin_id)

    def list_ids(self) -> list[str]:
        """
        Get a list of all registered plugin IDs.

        Returns:
            List of plugin IDs (stable identifiers)
        """
        return list(self._plugins.keys())

    def list_plugins(self) -> list[str]:
        """
        Get a list of all registered plugin IDs.

        Alias for list_ids() for backward compatibility.

        Returns:
            List of plugin IDs
        """
        return self.list_ids()

    def is_registered(self, plugin_id: str) -> bool:
        """
        Check if a plugin is registered.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            True if the plugin is registered
        """
        return plugin_id in self._plugins

    def get_command_plugin(self, plugin_id: str) -> CommandPluginProtocol | None:
        """
        Get a command plugin by its ID.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            The command plugin or None if not found
        """
        return self._command_plugins.get(plugin_id)

    def get_workflow_plugin(self, plugin_id: str) -> WorkflowPluginProtocol | None:
        """
        Get a workflow plugin by its ID.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            The workflow plugin or None if not found
        """
        return self._workflow_plugins.get(plugin_id)

    def get_extension_plugin(self, plugin_id: str) -> ExtensionPluginProtocol | None:
        """
        Get an extension plugin by its ID.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            The extension plugin or None if not found
        """
        return self._extension_plugins.get(plugin_id)

    def get_provider_plugin(self, plugin_id: str) -> ProviderPluginProtocol | None:
        """
        Get a provider plugin by its ID.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            The provider plugin or None if not found
        """
        return self._provider_plugins.get(plugin_id)

    def list_command_plugins(self) -> list[str]:
        """
        Get a list of all registered command plugin IDs.

        Returns:
            List of command plugin IDs
        """
        return list(self._command_plugins.keys())

    def list_workflow_plugins(self) -> list[str]:
        """
        Get a list of all registered workflow plugin IDs.

        Returns:
            List of workflow plugin IDs
        """
        return list(self._workflow_plugins.keys())

    def list_extension_plugins(self) -> list[str]:
        """
        Get a list of all registered extension plugin IDs.

        Returns:
            List of extension plugin IDs
        """
        return list(self._extension_plugins.keys())

    def list_provider_plugins(self) -> list[str]:
        """
        Get a list of all registered provider plugin IDs.

        Returns:
            List of provider plugin IDs
        """
        return list(self._provider_plugins.keys())

    def list_commands(self) -> list[str]:
        """
        Get a list of all registered command names.

        Returns:
            List of command names
        """
        return list(self._commands.keys())

    def list_workflows(self) -> list[str]:
        """
        Get a list of all registered workflow names.

        Returns:
            List of workflow names
        """
        return list(self._workflows.keys())

    def get_command_plugin_for_command(
            self, command: str
    ) -> CommandPluginProtocol | None:
        """
        Get the plugin that provides a specific command.

        Args:
            command: Name of the command

        Returns:
            The command plugin or None if not found
        """
        return self._commands.get(command)

    def get_workflow_plugin_for_workflow(
            self, workflow: str
    ) -> WorkflowPluginProtocol | None:
        """
        Get the plugin that provides a specific workflow.

        Args:
            workflow: Name of the workflow

        Returns:
            The workflow plugin or None if not found
        """
        return self._workflows.get(workflow)

    def get_extensions_for_plugin(
            self, target: str
    ) -> list[ExtensionPluginProtocol]:
        """
        Get all extensions targeting a specific plugin.

        Args:
            target: Plugin ID of the target plugin

        Returns:
            List of extension modules targeting the specified plugin
        """
        return self._extensions.get(target, [])

    def find_plugins_by_capability(
            self, capability: str
    ) -> list[QuackPluginProtocol]:
        """
        Find modules that advertise a specific capability.

        Args:
            capability: Capability to look for

        Returns:
            List of modules that have the specified capability
        """
        result: list[QuackPluginProtocol] = []

        for plugin in self._plugins.values():
            try:
                metadata = plugin.get_metadata()
                if capability in metadata.capabilities:
                    result.append(plugin)
            except Exception as e:
                plugin_id = self._get_plugin_id(plugin)
                self.logger.warning(
                    f"Error getting metadata from plugin '{plugin_id}': {e}"
                )

        return result

    def get_plugin_module_path(self, plugin: QuackPluginProtocol) -> str | None:
        """
        Get the module path for a plugin.

        Args:
            plugin: The plugin to get the module path for

        Returns:
            The module path or None if it cannot be determined
        """
        if hasattr(plugin, "__module__"):
            return plugin.__module__
        return None

    def reload_plugin(self, plugin_id: str) -> QuackPluginProtocol:
        """
        Reload a plugin by its ID.

        This unregisters the plugin, reloads its module, and registers
        the new instance.

        Args:
            plugin_id: Stable plugin identifier

        Returns:
            The newly loaded plugin

        Raises:
            QuackPluginError: If the plugin is not registered or cannot be reloaded
        """
        from quack_core.modules.discovery import loader

        if plugin_id not in self._plugins:
            raise QuackPluginError(
                f"Plugin '{plugin_id}' is not registered",
                plugin_name=plugin_id,
            )

        plugin = self._plugins[plugin_id]
        module_path = self.get_plugin_module_path(plugin)

        if not module_path:
            raise QuackPluginError(
                f"Cannot determine module path for plugin '{plugin_id}'",
                plugin_name=plugin_id,
            )

        # Unregister the current plugin
        self.unregister(plugin_id)

        # Reload the module and load the new plugin
        try:
            import importlib

            importlib.reload(importlib.import_module(module_path))
            new_plugin = loader.load_plugin(module_path)

            # Register the new plugin
            self.register(new_plugin)

            self.logger.info(f"Successfully reloaded plugin '{plugin_id}'")
            return new_plugin
        except Exception as e:
            self.logger.error(f"Error reloading plugin '{plugin_id}': {e}")
            raise QuackPluginError(
                f"Failed to reload plugin '{plugin_id}': {e}",
                plugin_name=plugin_id,
            ) from e


# Global registry instance
registry = PluginRegistry()
