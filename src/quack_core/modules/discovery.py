# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/modules/discovery.py
# module: quack_core.modules.discovery
# role: module
# neighbors: __init__.py, protocols.py, registry.py
# exports: PluginInfo, PluginEntryPoint, LoadResult, PluginLoader, list_available_entry_points, load_enabled_entry_points, load_enabled_modules
# git_branch: refactor/toolkitWorkflow
# git_commit: 21a4e25
# === QV-LLM:END ===



"""
Plugin discovery and loading for quack_core.

This module provides utilities for discovering and loading modules
from entry points and module paths.

Key principles:
- Discovery (listing) does NOT instantiate modules
- Loading (explicit) instantiates and optionally registers modules
- Import has no side effects
- Logging is quiet by default (debug level for discovery)

Following Python 3.13 best practices:
- Native types and collections.abc
- Pydantic for validation
- Structured return types for better error handling
"""

import importlib
import inspect
from importlib.metadata import entry_points

from pydantic import BaseModel, Field, ValidationError

from quack_core.lib.errors import QuackPluginError
from quack_core.lib.logging import LOG_LEVELS, LogLevel, get_logger
from quack_core.modules.protocols import QuackPluginMetadata, QuackPluginProtocol


class PluginInfo(QuackPluginMetadata):
    """
    Plugin information used for validation.

    Extends QuackPluginMetadata with stricter requirements:
    - plugin_id is required (not optional)

    This ensures that all validated modules have a stable identifier
    for deterministic registration.
    """

    plugin_id: str = Field(description="Required stable plugin identifier")


class PluginEntryPoint(BaseModel):
    """
    Metadata about an available entry point.

    This is returned by list_available_entry_points() without
    instantiating the plugin.
    """

    plugin_id: str = Field(description="Entry point name (stable identifier)")
    value: str = Field(description="Entry point value (module:function)")
    group: str = Field(description="Entry point group")


class LoadResult(BaseModel):
    """
    Result of a load operation.

    Provides structured feedback about what succeeded, what failed,
    and any warnings encountered.

    Success semantics:
    - Strict mode: success=True only if ALL requested modules loaded cleanly
    - Non-strict mode: success=True if AT LEAST ONE plugin loaded
                       success=False only if ZERO modules loaded (all failed)

    Warnings indicate non-fatal issues (missing modules in non-strict mode,
    deprecation notices, etc.) and do NOT affect success in non-strict mode
    as long as at least one plugin loaded successfully.
    """

    success: bool = Field(description="Whether the overall operation succeeded")
    loaded: list[str] = Field(
        default_factory=list,
        description="Plugin IDs that were successfully loaded",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings encountered",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Fatal errors encountered",
    )


class PluginLoader:
    """
    Loader for QuackCore modules.

    Provides both discovery (listing available modules without instantiation)
    and explicit loading (instantiating and optionally registering modules).

    Design principles:
    - Discovery returns metadata only
    - Loading is explicit and controlled
    - No automatic registration on import
    - Clear error handling with structured results
    """

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        """
        Initialize the plugin loader.

        Args:
            log_level: Logging level for loader operations
        """
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)

    def _validate_plugin(
            self, plugin: QuackPluginProtocol, module_path: str
    ) -> QuackPluginProtocol:
        """
        Validate that the plugin has the required attributes using pydantic.

        Args:
            plugin: The plugin instance to validate
            module_path: The module path from which the plugin was loaded

        Returns:
            The validated plugin instance

        Raises:
            QuackPluginError: If validation fails
        """
        try:
            # Check for plugin_id (required for new modules)
            if not hasattr(plugin, "plugin_id"):
                raise AttributeError(
                    "Plugin must implement plugin_id property. "
                    "This is required for stable plugin identity."
                )

            # Check for name (backward compatibility)
            if not hasattr(plugin, "name"):
                raise AttributeError("Plugin has no 'name' attribute")

            # Validate the get_metadata method and its return value
            if not hasattr(plugin, "get_metadata") or not callable(
                    plugin.get_metadata
            ):
                # For backward compatibility, create minimal metadata
                metadata = QuackPluginMetadata(
                    plugin_id=plugin.plugin_id,
                    name=plugin.name,
                    version="0.1.0",
                    description=f"Plugin from {module_path}",
                    capabilities=[],
                )
            else:
                metadata = plugin.get_metadata()

                # Validate metadata type
                if not isinstance(metadata, QuackPluginMetadata):
                    if isinstance(metadata, dict):
                        metadata = QuackPluginMetadata(**metadata)
                    else:
                        raise TypeError(
                            f"get_metadata() must return a QuackPluginMetadata object, "
                            f"got {type(metadata)}"
                        )

            # Validate using stricter PluginInfo model
            validation_dict = metadata.model_dump()
            # Ensure plugin_id is set from the plugin instance if not in metadata
            if not validation_dict.get("plugin_id"):
                validation_dict["plugin_id"] = plugin.plugin_id

            PluginInfo(**validation_dict)

        except (ValidationError, AttributeError, TypeError) as e:
            raise QuackPluginError(
                f"Plugin from module {module_path} "
                f"does not have valid plugin info: {e}",
                plugin_path=module_path,
            ) from e

        return plugin

    def _load_from_factory(
            self, module: object, module_path: str
    ) -> QuackPluginProtocol | None:
        """
        Attempt to load a plugin using factory functions defined in the module.

        Note: Only looks for create_plugin, NOT create_integration.
        Integrations must use a separate loader.

        Args:
            module: The imported module
            module_path: The module path

        Returns:
            The loaded plugin if found, otherwise None
        """
        # Only look for create_plugin (removed create_integration)
        func_name = "create_plugin"

        if func_name in getattr(module, "__dict__", {}):
            factory = getattr(module, func_name)
            if callable(factory):
                try:
                    plugin = factory()
                    plugin = self._validate_plugin(plugin, module_path)
                    self.logger.debug(
                        f"Loaded plugin {plugin.name} from "
                        f"module {module_path} using factory {func_name}"
                    )
                    return plugin
                except Exception as e:
                    self.logger.error(
                        f"Error in factory function {func_name} "
                        f"in module {module_path}: {e}"
                    )
        return None

    def _load_from_class(
            self, module: object, module_path: str
    ) -> QuackPluginProtocol | None:
        """
        Attempt to load a plugin by searching for specific classes in the module.

        Note: Only looks for MockPlugin class, NOT MockIntegration.

        Args:
            module: The imported module
            module_path: The module path

        Returns:
            The loaded plugin if found, otherwise None
        """
        class_name = "MockPlugin"

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name == class_name:
                try:
                    plugin = obj()
                    plugin = self._validate_plugin(plugin, module_path)
                    self.logger.debug(
                        f"Loaded plugin {plugin.name} from "
                        f"module {module_path} using class {class_name}"
                    )
                    return plugin
                except Exception as e:
                    self.logger.error(
                        f"Error initializing plugin class {name} "
                        f"in module {module_path}: {e}"
                    )
        return None

    def _load_from_dict(
            self, module: object, module_path: str
    ) -> QuackPluginProtocol | None:
        """
        As a fallback, attempt to load a plugin by checking the module's __dict__.

        Note: Only looks for MockPlugin, NOT MockIntegration.

        Args:
            module: The imported module
            module_path: The module path

        Returns:
            The loaded plugin if found, otherwise None
        """
        attr = "MockPlugin"

        if attr in getattr(module, "__dict__", {}):
            try:
                plugin_class = getattr(module, attr)
                plugin = plugin_class()
                plugin = self._validate_plugin(plugin, module_path)
                self.logger.debug(
                    f"Loaded plugin {plugin.name} from "
                    f"module {module_path} using attribute {attr}"
                )
                return plugin
            except Exception as e:
                self.logger.error(
                    f"Error initializing plugin from "
                    f"attribute {attr} in module {module_path}: {e}"
                )
        return None

    def load_plugin(self, module_path: str) -> QuackPluginProtocol:
        """
        Load a plugin from a module path.

        This method first searches for a factory function called 'create_plugin'.
        If not found, it searches for a class named "MockPlugin", and finally
        checks the module's __dict__ for this attribute.

        Note: Does NOT look for integration-related names (create_integration,
        MockIntegration). Integrations must use a separate loader.

        Args:
            module_path: Path to the module containing the plugin

        Returns:
            The loaded plugin instance

        Raises:
            QuackPluginError: If the plugin cannot be loaded
        """
        self.logger.debug(f"Loading plugin from module: {module_path}")

        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise QuackPluginError(
                f"Failed to import module {module_path}: {e}",
                plugin_path=module_path,
                original_error=e,
            ) from e

        # Try factory function first
        plugin = self._load_from_factory(module, module_path)
        if plugin is not None:
            return plugin

        # Try class lookup
        plugin = self._load_from_class(module, module_path)
        if plugin is not None:
            return plugin

        # Try dict lookup as fallback
        plugin = self._load_from_dict(module, module_path)
        if plugin is not None:
            return plugin

        raise QuackPluginError(
            f"No plugin found in module {module_path}. "
            f"Expected create_plugin() factory or MockPlugin class.",
            plugin_path=module_path,
        )

    def load_plugins(self, modules: list[str]) -> list[QuackPluginProtocol]:
        """
        Load multiple modules from module paths.

        Note: This does NOT register the modules. Use load_enabled_modules()
        for explicit loading with registration.

        Args:
            modules: List of module paths

        Returns:
            List of loaded plugin instances
        """
        plugins: list[QuackPluginProtocol] = []

        for module_path in modules:
            try:
                plugin = self.load_plugin(module_path)
                plugins.append(plugin)
            except QuackPluginError as e:
                self.logger.error(
                    f"Failed to load plugin from module {module_path}: {e}"
                )

        return plugins

    def load_entry_points(
            self, group: str = "quack_core.modules"
    ) -> list[QuackPluginProtocol]:
        """
        Load modules from entry points.

        ⚠️  LEGACY METHOD - PREFER load_enabled_entry_points()

        This method instantiates modules but does NOT register them.
        It exists for backward compatibility only.

        Recommended alternatives:
        - list_available_entry_points() for discovery without instantiation
        - load_enabled_entry_points() for explicit loading with registration

        Logging is at DEBUG level to avoid noise during discovery.

        Args:
            group: Entry point group to load from

        Returns:
            List of loaded plugin instances
        """
        # Log deprecation warning on first use
        if not hasattr(self, '_load_entry_points_warned'):
            self.logger.warning(
                "load_entry_points() is a legacy method. "
                "Prefer list_available_entry_points() for discovery or "
                "load_enabled_entry_points() for explicit loading."
            )
            self._load_entry_points_warned = True

        self.logger.debug(f"Loading modules from entry points group: {group}")
        plugins: list[QuackPluginProtocol] = []

        try:
            discovered_eps: list = []
            try:
                eps = entry_points(group=group)
                discovered_eps = list(eps)
                self.logger.debug(
                    f"Found {len(discovered_eps)} entry points in group '{group}'"
                )

                for ep in discovered_eps:
                    self.logger.debug(f"Entry point: {ep.name} from {ep.value}")
            except (ImportError, AttributeError) as e:
                self.logger.debug(f"Error getting entry points: {e}")
                return plugins

            for ep in discovered_eps:
                try:
                    self.logger.debug(
                        f"Loading entry point: {ep.name} from {ep.value}"
                    )
                    factory = ep.load()
                    if callable(factory):
                        plugin = factory()
                        plugin = self._validate_plugin(plugin, ep.value)
                        plugins.append(plugin)

                        # Use DEBUG level instead of INFO (quieter by default)
                        self.logger.debug(
                            f"Loaded plugin '{plugin.name}' from entry point '{ep.name}'"
                        )
                except Exception as e:
                    self.logger.error(f"Failed to load entry point {ep.name}: {e}")
        except Exception as e:
            self.logger.error(f"Error loading entry points: {e}")

        return plugins

    def list_available_entry_points(
            self, group: str = "quack_core.modules"
    ) -> list[PluginEntryPoint]:
        """
        List available entry points WITHOUT instantiating them.

        This is pure discovery - no modules are created or registered.
        Use this to see what's available before explicitly loading.

        Args:
            group: Entry point group to query

        Returns:
            List of entry point metadata
        """
        self.logger.debug(f"Discovering entry points in group: {group}")
        available: list[PluginEntryPoint] = []

        try:
            eps = entry_points(group=group)
            for ep in eps:
                available.append(
                    PluginEntryPoint(
                        plugin_id=ep.name,
                        value=ep.value,
                        group=group,
                    )
                )

            self.logger.debug(
                f"Discovered {len(available)} entry points in group '{group}'"
            )
        except (ImportError, AttributeError) as e:
            self.logger.debug(f"Error discovering entry points: {e}")

        return available

    def load_enabled_entry_points(
            self,
            enabled: list[str],
            group: str = "quack_core.modules",
            strict: bool = True,
            auto_register: bool = True,
    ) -> LoadResult:
        """
        Load and optionally register only the specified modules from entry points.

        This is the primary explicit loading API. It:
        1. Loads only the modules specified in the enabled list
        2. Preserves the order of the enabled list
        3. Optionally registers modules in the global registry
        4. Returns structured results with clear error reporting

        Strict mode behavior:
        - strict=True: All-or-nothing - first error stops loading and rolls back
        - strict=False: Best-effort - continues on error, warnings for failures

        Important: Entry point names MUST match plugin.plugin_id for correctness.

        Args:
            enabled: List of plugin IDs to load (e.g., ["fs", "paths"])
            group: Entry point group to load from
            strict: If True, fail fast on first error with rollback
            auto_register: If True, automatically register loaded modules

        Returns:
            LoadResult with success status, loaded modules, warnings, and errors
        """
        from quack_core.modules.registry import registry

        self.logger.info(
            f"Loading enabled modules: {enabled} (strict={strict}, "
            f"auto_register={auto_register})"
        )

        result = LoadResult(success=True)
        # Track registered IDs for rollback (may differ from entry point names)
        registered_ids: list[str] = []

        # Get all available entry points
        try:
            eps = entry_points(group=group)
            ep_map = {ep.name: ep for ep in eps}
        except (ImportError, AttributeError) as e:
            result.success = False
            result.errors.append(f"Failed to load entry points: {e}")
            return result

        # In strict mode, pre-validate all requested modules exist
        if strict:
            missing = [pid for pid in enabled if pid not in ep_map]
            if missing:
                result.success = False
                result.errors.append(
                    f"Missing modules in strict mode: {missing}. "
                    f"No modules loaded (all-or-nothing)."
                )
                self.logger.error(result.errors[0])
                return result

        # Load modules in the order specified
        for ep_name in enabled:
            if ep_name not in ep_map:
                # Should only happen in non-strict mode (strict pre-validates)
                warning_msg = f"Plugin '{ep_name}' not found in entry points"
                result.warnings.append(warning_msg)
                self.logger.warning(warning_msg)
                continue

            # Load the plugin
            ep = ep_map[ep_name]
            try:
                self.logger.debug(f"Loading plugin '{ep_name}' from {ep.value}")
                factory = ep.load()

                if not callable(factory):
                    raise ValueError(f"Entry point {ep_name} is not callable")

                plugin = factory()
                plugin = self._validate_plugin(plugin, ep.value)

                # Get the actual plugin_id that will be used for registration
                actual_plugin_id = getattr(plugin, "plugin_id", None) or plugin.name

                # IMPORTANT: Enforce that plugin_id matches entry point name
                if actual_plugin_id != ep_name:
                    raise ValueError(
                        f"Plugin identity mismatch: entry point name is '{ep_name}' "
                        f"but plugin.plugin_id is '{actual_plugin_id}'. "
                        f"These must match for deterministic behavior."
                    )

                # Register if requested
                if auto_register:
                    registry.register(plugin)
                    registered_ids.append(actual_plugin_id)
                    self.logger.debug(
                        f"Registered plugin '{actual_plugin_id}' (name: {plugin.name})"
                    )
                else:
                    self.logger.debug(
                        f"Loaded plugin '{actual_plugin_id}' (name: {plugin.name})"
                    )

                result.loaded.append(actual_plugin_id)

            except Exception as e:
                error_msg = f"Failed to load plugin '{ep_name}': {e}"

                if strict:
                    result.success = False
                    result.errors.append(error_msg)
                    self.logger.error(error_msg)
                    # In strict mode, rollback all successfully registered modules
                    if auto_register and registered_ids:
                        self.logger.warning(
                            f"Strict mode failure - rolling back {len(registered_ids)} "
                            f"registered modules: {registered_ids}"
                        )
                        for registered_id in registered_ids:
                            try:
                                registry.unregister(registered_id)
                            except Exception as unregister_error:
                                self.logger.error(
                                    f"Failed to unregister '{registered_id}' during "
                                    f"rollback: {unregister_error}"
                                )
                    result.loaded.clear()
                    return result
                else:
                    # Non-strict: log as warning and continue
                    result.warnings.append(error_msg)
                    self.logger.warning(error_msg)

        # Determine final success state
        # In non-strict mode: success if we loaded at least one plugin
        # (warnings don't affect success unless nothing loaded)
        if not strict and not result.loaded and result.warnings:
            result.success = False

        # Summary log at INFO level
        if result.success:
            self.logger.info(
                f"Successfully loaded {len(result.loaded)} plugin(s): {result.loaded}"
            )
            if result.warnings:
                self.logger.info(f"With {len(result.warnings)} warning(s)")
        else:
            self.logger.error(
                f"Failed to load modules. "
                f"Loaded: {len(result.loaded)}, Errors: {len(result.errors)}"
            )

        return result

    def load_enabled_modules(
            self,
            modules: list[str],
            strict: bool = True,
            auto_register: bool = True,
    ) -> LoadResult:
        """
        Load and optionally register modules from explicit module paths.

        Similar to load_enabled_entry_points but for module paths instead
        of entry points.

        Args:
            modules: List of module paths (e.g., ["quack_core.lib.fs.plugin"])
            strict: If True, fail fast on first error with rollback
            auto_register: If True, automatically register loaded modules

        Returns:
            LoadResult with success status, loaded modules, warnings, and errors
        """
        from quack_core.modules.registry import registry

        self.logger.info(
            f"Loading modules from modules: {modules} (strict={strict}, "
            f"auto_register={auto_register})"
        )

        result = LoadResult(success=True)
        # Track registered IDs for rollback
        registered_ids: list[str] = []

        for module_path in modules:
            try:
                plugin = self.load_plugin(module_path)

                # Get the actual plugin_id that will be used for registration
                actual_plugin_id = getattr(plugin, "plugin_id", None) or plugin.name

                # Register if requested
                if auto_register:
                    registry.register(plugin)
                    registered_ids.append(actual_plugin_id)
                    self.logger.debug(
                        f"Registered plugin from '{module_path}' "
                        f"(id: {actual_plugin_id}, name: {plugin.name})"
                    )
                else:
                    self.logger.debug(
                        f"Loaded plugin from '{module_path}' "
                        f"(id: {actual_plugin_id}, name: {plugin.name})"
                    )

                result.loaded.append(actual_plugin_id)

            except Exception as e:
                error_msg = f"Failed to load plugin from '{module_path}': {e}"

                if strict:
                    result.success = False
                    result.errors.append(error_msg)
                    self.logger.error(error_msg)
                    # In strict mode, rollback all successfully registered modules
                    if auto_register and registered_ids:
                        self.logger.warning(
                            f"Strict mode failure - rolling back {len(registered_ids)} "
                            f"registered modules: {registered_ids}"
                        )
                        for registered_id in registered_ids:
                            try:
                                registry.unregister(registered_id)
                            except Exception as unregister_error:
                                self.logger.error(
                                    f"Failed to unregister '{registered_id}' during "
                                    f"rollback: {unregister_error}"
                                )
                    result.loaded.clear()
                    return result
                else:
                    result.warnings.append(error_msg)
                    self.logger.warning(error_msg)

        # Determine final success state
        # In non-strict mode: success if we loaded at least one plugin
        if not strict and not result.loaded and result.warnings:
            result.success = False

        # Summary log at INFO level
        if result.success:
            self.logger.info(
                f"Successfully loaded {len(result.loaded)} plugin(s) from modules: "
                f"{result.loaded}"
            )
            if result.warnings:
                self.logger.info(f"With {len(result.warnings)} warning(s)")
        else:
            self.logger.error(
                f"Failed to load modules from modules. "
                f"Loaded: {len(result.loaded)}, Errors: {len(result.errors)}"
            )

        return result

    def discover_plugins(
            self,
            entry_point_group: str = "quack_core.modules",
            additional_modules: list[str] | None = None,
    ) -> list[QuackPluginProtocol]:
        """
        Discover modules from entry points and additional modules.

        WARNING: This is a legacy method kept for backward compatibility.
        It instantiates modules but does NOT register them.

        For new code, use:
        - list_available_entry_points() for discovery without instantiation
        - load_enabled_entry_points() for explicit loading with registration

        Args:
            entry_point_group: Entry point group to load from
            additional_modules: Additional module paths to load

        Returns:
            List of discovered plugin instances
        """
        self.logger.debug("Using legacy discover_plugins method")

        plugins: list[QuackPluginProtocol] = self.load_entry_points(entry_point_group)

        if additional_modules is not None:
            module_plugins = self.load_plugins(additional_modules)
            plugins.extend(module_plugins)

        return plugins


# Global loader instance
loader = PluginLoader()


# Top-level convenience functions for explicit loading
def list_available_entry_points(
        group: str = "quack_core.modules",
) -> list[PluginEntryPoint]:
    """
    List available plugin entry points without instantiating them.

    This is pure discovery - use it to see what's available before
    explicitly loading modules.

    Args:
        group: Entry point group to query

    Returns:
        List of entry point metadata
    """
    return loader.list_available_entry_points(group)


def load_enabled_entry_points(
        enabled: list[str],
        group: str = "quack_core.modules",
        strict: bool = True,
        auto_register: bool = True,
) -> LoadResult:
    """
    Load and optionally register only the specified modules.

    This is the primary API for explicit plugin loading. It:
    - Loads only the modules specified in the enabled list
    - Preserves the order of the enabled list
    - Optionally registers modules in the global registry
    - Returns structured results with clear error reporting

    Args:
        enabled: List of plugin IDs to load
        group: Entry point group to load from
        strict: If True, fail fast on first error
        auto_register: If True, automatically register loaded modules

    Returns:
        LoadResult with success status, loaded modules, warnings, and errors
    """
    return loader.load_enabled_entry_points(enabled, group, strict, auto_register)


def load_enabled_modules(
        modules: list[str],
        strict: bool = True,
        auto_register: bool = True,
) -> LoadResult:
    """
    Load and optionally register modules from explicit module paths.

    Args:
        modules: List of module paths
        strict: If True, fail fast on first error
        auto_register: If True, automatically register loaded modules

    Returns:
        LoadResult with success status, loaded modules, warnings, and errors
    """
    return loader.load_enabled_modules(modules, strict, auto_register)