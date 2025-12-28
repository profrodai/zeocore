# === QV-LLM:BEGIN ===
# path: quack-core/examples/explicit_plugin_loading_example.py
# role: module
# neighbors: config_tooling_test.py, http_adapter_usage.py, toolkit_usage.py
# exports: example_1_discovery, example_2_explicit_loading, example_3_error_handling, example_4_configuration_driven, example_5_plugin_metadata, example_6_lifecycle_management, example_7_testing_pattern, main
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===



"""
Example: Explicit Plugin Loading Best Practices

This example demonstrates the recommended patterns for using the
refactored QuackCore plugin system with explicit loading.

Key concepts demonstrated:
1. Discovery without instantiation
2. Explicit, controlled loading
3. Configuration-driven plugin enablement
4. Error handling and validation
5. Plugin lifecycle management
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def example_1_discovery():
    """
    Example 1: Discover available plugins without loading them.

    This is useful for:
    - Showing users what plugins are available
    - Validating configuration before loading
    - Building plugin selection UIs
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Discovery Without Loading")
    print("=" * 70 + "\n")

    from quack_core.plugins import list_available_entry_points, registry

    # Verify registry is empty (no auto-loading)
    print(f"Registry state before discovery: {len(registry.list_ids())} plugins")

    # Discover what's available
    available = list_available_entry_points()

    print(f"\nDiscovered {len(available)} available plugins:")
    for ep in available:
        print(f"  - {ep.plugin_id} (from {ep.value})")

    # Registry should still be empty (discovery doesn't instantiate)
    print(f"\nRegistry state after discovery: {len(registry.list_ids())} plugins")
    print("✓ Discovery completed without side effects")


def example_2_explicit_loading():
    """
    Example 2: Explicitly load specific plugins.

    This is the recommended approach for application startup.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Explicit Loading")
    print("=" * 70 + "\n")

    from quack_core.plugins import load_enabled_entry_points, registry

    # Clear any previous state
    registry.clear()

    # Define which plugins to load
    enabled_plugins = ["fs", "paths", "config"]

    print(f"Loading plugins: {enabled_plugins}")

    # Load with strict error handling
    result = load_enabled_entry_points(
        enabled=enabled_plugins,
        strict=True,
        auto_register=True,
    )

    # Check results
    if result.success:
        print(f"✓ Successfully loaded {len(result.loaded)} plugins:")
        for plugin_id in result.loaded:
            plugin = registry.get_plugin(plugin_id)
            metadata = plugin.get_metadata()
            print(f"  - {plugin_id}: {metadata.name} v{metadata.version}")
    else:
        print(f"✗ Loading failed with {len(result.errors)} errors:")
        for error in result.errors:
            print(f"  - {error}")

    # Show warnings even on success
    if result.warnings:
        print(f"\n⚠ {len(result.warnings)} warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")


def example_3_error_handling():
    """
    Example 3: Error handling in strict vs. non-strict mode.

    Demonstrates the difference between fail-fast and continue-on-error.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Error Handling (Strict vs. Non-Strict)")
    print("=" * 70 + "\n")

    from quack_core.plugins import load_enabled_entry_points, registry

    # Clear previous state
    registry.clear()

    # Plugins to load (includes one that doesn't exist)
    plugins_with_typo = ["fs", "patsss", "config"]  # "patsss" doesn't exist

    print("Attempting to load plugins with a typo:")
    print(f"  {plugins_with_typo}\n")

    # Try in strict mode first
    print("--- STRICT MODE (fail-fast) ---")
    registry.clear()

    result_strict = load_enabled_entry_points(
        enabled=plugins_with_typo,
        strict=True,
    )

    if result_strict.success:
        print(f"✓ Loaded: {result_strict.loaded}")
    else:
        print(f"✗ Failed: {result_strict.errors[0]}")
        print(f"  Loaded: {result_strict.loaded} (none - rolled back)")

    print(f"  Registry has {len(registry.list_ids())} plugins")

    # Try in non-strict mode
    print("\n--- NON-STRICT MODE (continue-on-error) ---")
    registry.clear()

    result_relaxed = load_enabled_entry_points(
        enabled=plugins_with_typo,
        strict=False,
    )

    if result_relaxed.success:
        print(f"✓ Partially loaded: {result_relaxed.loaded}")
    else:
        print(f"⚠ Completed with warnings: {result_relaxed.loaded}")

    if result_relaxed.warnings:
        print(f"  Warnings: {result_relaxed.warnings[0]}")

    print(f"  Registry has {len(registry.list_ids())} plugins")


def example_4_configuration_driven():
    """
    Example 4: Load plugins based on configuration.

    This is the recommended pattern for production applications.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Configuration-Driven Loading")
    print("=" * 70 + "\n")

    from quack_core.plugins import load_enabled_entry_points, registry

    # Clear previous state
    registry.clear()

    # Simulated configuration (in practice, load from YAML/JSON)
    config = {
        "environment": "production",
        "plugins": {
            "enabled": ["fs", "paths", "config"],
            "strict_loading": True,
        },
    }

    print(f"Loading configuration for: {config['environment']}")
    print(f"Enabled plugins: {config['plugins']['enabled']}")
    print(f"Strict mode: {config['plugins']['strict_loading']}\n")

    # Load based on config
    result = load_enabled_entry_points(
        enabled=config["plugins"]["enabled"],
        strict=config["plugins"]["strict_loading"],
    )

    if result.success:
        print(f"✓ Application ready with {len(result.loaded)} plugins")

        # Verify specific capabilities
        print("\nVerifying capabilities:")

        # Check if we have filesystem support
        if registry.is_registered("fs"):
            print("  ✓ Filesystem plugin available")

        # Check if we have path utilities
        if registry.is_registered("paths"):
            print("  ✓ Path utilities available")

        # List all available commands (if any command plugins loaded)
        commands = registry.list_commands()
        if commands:
            print(f"  ✓ {len(commands)} commands available: {commands}")
    else:
        print(f"✗ Application startup failed: {result.errors}")
        print("  Cannot continue - exiting")
        # In real app: sys.exit(1)


def example_5_plugin_metadata():
    """
    Example 5: Working with plugin metadata and capabilities.

    Shows how to query plugin information and find plugins by capability.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Plugin Metadata and Capabilities")
    print("=" * 70 + "\n")

    from quack_core.plugins import load_enabled_entry_points, registry

    # Clear and load some plugins
    registry.clear()
    load_enabled_entry_points(["fs", "paths", "config"])

    print("Loaded plugins:\n")

    for plugin_id in registry.list_ids():
        plugin = registry.get_plugin(plugin_id)
        metadata = plugin.get_metadata()

        print(f"Plugin: {plugin_id}")
        print(f"  Name: {metadata.name}")
        print(f"  Version: {metadata.version}")
        print(f"  Description: {metadata.description}")

        if metadata.author:
            print(f"  Author: {metadata.author}")

        if metadata.capabilities:
            print(f"  Capabilities: {', '.join(metadata.capabilities)}")

        print()

    # Find plugins by capability
    print("Finding plugins with 'filesystem' capability:")
    fs_plugins = registry.find_plugins_by_capability("filesystem")

    if fs_plugins:
        for plugin in fs_plugins:
            print(f"  - {plugin.plugin_id}")
    else:
        print("  (none found)")


def example_6_lifecycle_management():
    """
    Example 6: Plugin lifecycle management.

    Demonstrates loading, unloading, and reloading plugins.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Plugin Lifecycle Management")
    print("=" * 70 + "\n")

    from quack_core.plugins import load_enabled_entry_points, registry

    # Start fresh
    registry.clear()
    print("Starting with empty registry")
    print(f"  Plugins: {registry.list_ids()}\n")

    # Load initial set
    print("Loading initial plugins: ['fs', 'paths']")
    load_enabled_entry_points(["fs", "paths"])
    print(f"  Plugins: {registry.list_ids()}\n")

    # Unload one plugin
    print("Unloading 'paths' plugin")
    registry.unregister("paths")
    print(f"  Plugins: {registry.list_ids()}\n")

    # Load additional plugin
    print("Loading 'config' plugin")
    load_enabled_entry_points(["config"])
    print(f"  Plugins: {registry.list_ids()}\n")

    # Clear all
    print("Clearing all plugins")
    registry.clear()
    print(f"  Plugins: {registry.list_ids()}\n")

    print("✓ Lifecycle management complete")


def example_7_testing_pattern():
    """
    Example 7: Testing pattern with isolated plugin state.

    Shows how to structure tests with proper plugin isolation.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Testing Pattern")
    print("=" * 70 + "\n")

    from quack_core.plugins import load_enabled_entry_points, registry

    def simulate_test_case_1():
        """Simulated test case 1."""
        # setUp: Clean state
        registry.clear()

        # Load only what this test needs
        load_enabled_entry_points(["fs"])

        # Test logic
        assert registry.is_registered("fs"), "FS plugin should be loaded"
        assert not registry.is_registered("paths"), "Paths should not be loaded"

        print("✓ Test case 1 passed")

        # tearDown: Clean up
        registry.clear()

    def simulate_test_case_2():
        """Simulated test case 2."""
        # setUp: Clean state
        registry.clear()

        # This test needs different plugins
        load_enabled_entry_points(["paths", "config"])

        # Test logic
        assert not registry.is_registered("fs"), "FS should not be loaded"
        assert registry.is_registered("paths"), "Paths plugin should be loaded"
        assert registry.is_registered("config"), "Config plugin should be loaded"

        print("✓ Test case 2 passed")

        # tearDown: Clean up
        registry.clear()

    print("Running isolated test cases:\n")
    simulate_test_case_1()
    simulate_test_case_2()

    print("\n✓ All tests passed with proper isolation")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("QuackCore Explicit Plugin Loading Examples")
    print("=" * 70)

    examples = [
        ("Discovery", example_1_discovery),
        ("Explicit Loading", example_2_explicit_loading),
        ("Error Handling", example_3_error_handling),
        ("Configuration-Driven", example_4_configuration_driven),
        ("Plugin Metadata", example_5_plugin_metadata),
        ("Lifecycle Management", example_6_lifecycle_management),
        ("Testing Pattern", example_7_testing_pattern),
    ]

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            logger.error(f"Example '{name}' failed: {e}", exc_info=True)

    print("\n" + "=" * 70)
    print("Examples Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()