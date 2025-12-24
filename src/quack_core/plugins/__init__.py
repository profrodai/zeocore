# quack-core/src/quack_core/plugins/__init__.py
"""
Plugin system for quack_core.

This package provides a plugin system for QuackCore, allowing
modules to be dynamically loaded and registered at runtime.
"""

from quack_core.plugins.discovery import PluginLoader, loader
from quack_core.plugins.protocols import (
    CommandPluginProtocol,
    ConfigurablePluginProtocol,
    ExtensionPluginProtocol,
    PluginLoaderProtocol,
    PluginRegistryProtocol,
    ProviderPluginProtocol,
    QuackPluginProtocol,
    WorkflowPluginProtocol,
)
from quack_core.plugins.registry import PluginRegistry, registry

# Initialize the plugin system by loading core plugins
# This is done on import so that the registry is populated with core plugins
core_plugins = loader.load_entry_points()
for plugin in core_plugins:
    registry.register(plugin)

__all__ = [
    "PluginRegistry",
    "PluginLoader",
    # Classes
    "PluginRegistryProtocol",
    "PluginLoaderProtocol",
    # Protocol interfaces
    "QuackPluginProtocol",
    "CommandPluginProtocol",
    "WorkflowPluginProtocol",
    "ExtensionPluginProtocol",
    "ProviderPluginProtocol",
    "ConfigurablePluginProtocol",
    # Global instances
    "registry",
    "loader",
]
