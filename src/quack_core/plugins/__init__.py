# quack-core/src/quack-core/plugins/__init__.py
"""
Plugin system for QuackCore.

This package provides a plugin system for QuackCore, allowing
modules to be dynamically loaded and registered at runtime.
"""

from quackcore.plugins.discovery import PluginLoader, loader
from quackcore.plugins.protocols import (
    CommandPluginProtocol,
    ConfigurablePluginProtocol,
    ExtensionPluginProtocol,
    PluginLoaderProtocol,
    PluginRegistryProtocol,
    ProviderPluginProtocol,
    QuackPluginProtocol,
    WorkflowPluginProtocol,
)
from quackcore.plugins.registry import PluginRegistry, registry

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
