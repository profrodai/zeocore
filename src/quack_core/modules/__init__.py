# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/modules/__init__.py
# module: quack_core.modules.__init__
# role: module
# neighbors: protocols.py, registry.py, discovery.py
# exports: PluginRegistry, PluginLoader, PluginRegistryProtocol, PluginLoaderProtocol, QuackPluginProtocol, CommandPluginProtocol, WorkflowPluginProtocol, ExtensionPluginProtocol (+10 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 9e6703a
# === QV-LLM:END ===



"""
Plugin system for quack_core.

This package provides a plugin system for QuackCore, allowing
modules to be dynamically loaded and registered at runtime.

KEY DESIGN PRINCIPLES:
======================
1. Importing this module has NO side effects (no auto-discovery, no auto-registration)
2. Plugins are loaded ONLY via explicit enable lists (operator-controlled)
3. Discovery lists what's available WITHOUT instantiating anything
4. Plugins and Integrations are kept separate (no mixing in the loader)
5. Logging is quiet by default (debug level unless explicitly raised)

USAGE PATTERNS:
===============

# Discovery (listing available modules without loading):
from quack_core.modules import list_available_entry_points
available = list_available_entry_points()
# Returns: [PluginEntryPoint(plugin_id="fs", value="...", group="..."), ...]

# Explicit loading (the recommended approach):
from quack_core.modules import load_enabled_entry_points
result = load_enabled_entry_points(
    enabled=["fs", "paths", "config"],
    strict=True,  # Fail fast on errors
    auto_register=True,  # Register in global registry
)
if result.success:
    print(f"Loaded: {result.loaded}")
else:
    print(f"Errors: {result.errors}")

# Direct registry access:
from quack_core.modules import registry
plugin = registry.get_plugin("fs")
all_plugins = registry.list_ids()

# Manual loading without auto-registration:
from quack_core.modules import loader
plugin = loader.load_plugin("my_module.plugin")
registry.register(plugin)

MIGRATION GUIDE:
================
If you have code that relies on automatic plugin loading on import,
you need to update it to use explicit loading:

OLD (automatic):
    import quack_core.modules  # Plugins auto-loaded

NEW (explicit):
    from quack_core.modules import load_enabled_entry_points
    load_enabled_entry_points(["fs", "paths"])  # Explicit control

Following Python 3.13 best practices:
- No module-level side effects
- Explicit > implicit
- Clear separation of discovery vs. loading
- Structured error handling
"""

# Import protocols (these are just type definitions, no side effects)
# Import core classes (instantiation only, no execution)
from quack_core.modules.discovery import (
    LoadResult,
    PluginEntryPoint,
    PluginLoader,
    list_available_entry_points,
    load_enabled_entry_points,
    load_enabled_modules,
    loader,
)
from quack_core.modules.protocols import (
    CommandPluginProtocol,
    ConfigurablePluginProtocol,
    ExtensionPluginProtocol,
    PluginLoaderProtocol,
    PluginRegistryProtocol,
    ProviderPluginProtocol,
    QuackPluginMetadata,
    QuackPluginProtocol,
    WorkflowPluginProtocol,
)
from quack_core.modules.registry import PluginRegistry, registry

# NO AUTOMATIC LOADING
# The following block has been REMOVED to ensure import has no side effects:
#
# core_plugins = loader.load_entry_points()
# for plugin in core_plugins:
#     registry.register(plugin)
#
# Plugins must now be loaded explicitly using:
# - load_enabled_entry_points(["fs", "paths", ...])
# - load_enabled_modules(["module.path", ...])
# - Or manually via loader.load_plugin() + registry.register()

__all__ = [
    # Core classes
    "PluginRegistry",
    "PluginLoader",
    # Protocol interfaces
    "PluginRegistryProtocol",
    "PluginLoaderProtocol",
    "QuackPluginProtocol",
    "CommandPluginProtocol",
    "WorkflowPluginProtocol",
    "ExtensionPluginProtocol",
    "ProviderPluginProtocol",
    "ConfigurablePluginProtocol",
    # Data models
    "QuackPluginMetadata",
    "PluginEntryPoint",
    "LoadResult",
    # Explicit loading functions (NEW - recommended API)
    "list_available_entry_points",
    "load_enabled_entry_points",
    "load_enabled_modules",
    # Global instances
    "registry",
    "loader",
]
