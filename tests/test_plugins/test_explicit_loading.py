# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_plugins/test_explicit_loading.py
# role: tests
# neighbors: __init__.py, test_discovery.py, test_protocols.py, test_registry.py
# exports: TestImportSideEffects, MockTestPlugin, TestExplicitLoading, TestPluginIdStability, TestRegistryClear, TestLoadEnabledModules, TestListAvailableEntryPoints
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===



"""
Tests for explicit plugin loading behavior.

These tests enforce the key principles of the refactored plugin system:
1. Import has no side effects
2. Plugins load only when explicitly requested
3. Registry is empty by default
4. Strict mode enforces fail-fast behavior
5. Non-strict mode continues with warnings

Following Python 3.13 best practices:
- Clear test names describing behavior
- Isolated test state (setUp/tearDown)
- Comprehensive edge case coverage
"""

import sys
import unittest
from unittest.mock import Mock, patch

from quack_core.core.errors import QuackPluginError
from quack_core.modules.protocols import QuackPluginMetadata


class TestImportSideEffects(unittest.TestCase):
    """Test that importing quack_core.modules has no side effects."""

    def setUp(self):
        """Clean up any existing plugin state before each test."""
        # Remove modules module from sys.modules to force fresh import
        modules_to_remove = [
            key for key in sys.modules.keys()
            if key.startswith("quack_core.modules")
        ]
        for module in modules_to_remove:
            del sys.modules[module]

    def test_import_does_not_register_plugins(self):
        """
        Test A: Import has no side effects.

        Importing quack_core.modules must not register any modules.
        The registry should be completely empty after import.
        """
        # Import the module
        import quack_core.modules

        # Verify registry is empty
        self.assertEqual(
            len(quack_core.modules.registry.list_ids()),
            0,
            "Registry should be empty after import, but contains: "
            f"{quack_core.modules.registry.list_ids()}",
        )

        # Verify no modules of any type
        self.assertEqual(len(quack_core.modules.registry.list_command_plugins()), 0)
        self.assertEqual(len(quack_core.modules.registry.list_workflow_plugins()), 0)
        self.assertEqual(len(quack_core.modules.registry.list_extension_plugins()), 0)
        self.assertEqual(len(quack_core.modules.registry.list_provider_plugins()), 0)

        # Verify no commands or workflows registered
        self.assertEqual(len(quack_core.modules.registry.list_commands()), 0)
        self.assertEqual(len(quack_core.modules.registry.list_workflows()), 0)

    def test_import_exports_expected_api(self):
        """Verify the module exports the expected public API."""
        import quack_core.modules

        # Check that explicit loading functions are available
        self.assertTrue(hasattr(quack_core.modules, "list_available_entry_points"))
        self.assertTrue(hasattr(quack_core.modules, "load_enabled_entry_points"))
        self.assertTrue(hasattr(quack_core.modules, "load_enabled_modules"))

        # Check that global instances are available
        self.assertTrue(hasattr(quack_core.modules, "registry"))
        self.assertTrue(hasattr(quack_core.modules, "loader"))

        # Check that classes are available
        self.assertTrue(hasattr(quack_core.modules, "PluginRegistry"))
        self.assertTrue(hasattr(quack_core.modules, "PluginLoader"))


class MockTestPlugin:
    """A minimal test plugin for testing."""

    def __init__(self, plugin_id: str = "test_plugin", name: str = "Test Plugin"):
        self._plugin_id = plugin_id
        self._name = name

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def name(self) -> str:
        return self._name

    def get_metadata(self) -> QuackPluginMetadata:
        return QuackPluginMetadata(
            plugin_id=self._plugin_id,
            name=self._name,
            version="1.0.0",
            description="A test plugin",
            capabilities=["test"],
        )


class TestExplicitLoading(unittest.TestCase):
    """Test explicit plugin loading behavior."""

    def setUp(self):
        """Clean registry before each test."""
        from quack_core.modules import registry
        registry.clear()

    def tearDown(self):
        """Clean registry after each test."""
        from quack_core.modules import registry
        registry.clear()

    @patch("quack_core.modules.discovery.entry_points")
    def test_explicit_load_loads_only_requested_plugins(self, mock_entry_points):
        """
        Test B: Explicit load loads only requested modules.

        When we call load_enabled_entry_points with specific plugin IDs,
        only those modules should be loaded and registered.
        """
        from quack_core.modules import load_enabled_entry_points, registry

        # Create mock entry points
        fs_plugin = MockTestPlugin(plugin_id="fs", name="FileSystem")
        paths_plugin = MockTestPlugin(plugin_id="paths", name="Paths")
        config_plugin = MockTestPlugin(plugin_id="config", name="Config")

        # Mock entry point objects
        fs_ep = Mock()
        fs_ep.name = "fs"
        fs_ep.value = "quack_core.core.fs:create_plugin"
        fs_ep.load.return_value = lambda: fs_plugin

        paths_ep = Mock()
        paths_ep.name = "paths"
        paths_ep.value = "quack_core.core.paths:create_plugin"
        paths_ep.load.return_value = lambda: paths_plugin

        config_ep = Mock()
        config_ep.name = "config"
        config_ep.value = "quack_core.core.config:create_plugin"
        config_ep.load.return_value = lambda: config_plugin

        # Setup mock to return all three entry points
        mock_entry_points.return_value = [fs_ep, paths_ep, config_ep]

        # Load only fs plugin explicitly
        result = load_enabled_entry_points(enabled=["fs"])

        # Verify success
        self.assertTrue(result.success)
        self.assertEqual(result.loaded, ["fs"])
        self.assertEqual(len(result.errors), 0)

        # Verify only fs is registered
        registered_ids = registry.list_ids()
        self.assertEqual(len(registered_ids), 1)
        self.assertIn("fs", registered_ids)
        self.assertNotIn("paths", registered_ids)
        self.assertNotIn("config", registered_ids)

        # Verify we can retrieve the plugin
        fs = registry.get_plugin("fs")
        self.assertIsNotNone(fs)
        self.assertEqual(fs.plugin_id, "fs")

    @patch("quack_core.modules.discovery.entry_points")
    def test_strict_missing_plugin_fails_and_loads_nothing(self, mock_entry_points):
        """
        Test C: Strict missing plugin fails and loads nothing.

        In strict mode, if a requested plugin doesn't exist, the entire
        operation should fail and NO modules should be registered.
        This now includes pre-validation, so nothing is attempted.
        """
        from quack_core.modules import load_enabled_entry_points, registry

        # Create mock entry points (only fs exists)
        fs_plugin = MockTestPlugin(plugin_id="fs", name="FileSystem")

        fs_ep = Mock()
        fs_ep.name = "fs"
        fs_ep.value = "quack_core.core.fs:create_plugin"
        fs_ep.load.return_value = lambda: fs_plugin

        mock_entry_points.return_value = [fs_ep]

        # Try to load non-existent plugin in strict mode (before fs)
        result = load_enabled_entry_points(
            enabled=["does_not_exist", "fs"],
            strict=True,
        )

        # Verify failure
        self.assertFalse(result.success)
        self.assertEqual(len(result.loaded), 0)
        self.assertGreater(len(result.errors), 0)
        # Error message should mention all-or-nothing and pre-validation
        self.assertIn("does_not_exist", result.errors[0])
        self.assertIn("all-or-nothing", result.errors[0].lower())

        # Verify registry is EMPTY (nothing was loaded due to strict pre-validation)
        self.assertEqual(len(registry.list_ids()), 0)

        # Verify fs.load() was NEVER called (pre-validation prevents loading)
        fs_ep.load.assert_not_called()

    @patch("quack_core.modules.discovery.entry_points")
    def test_non_strict_missing_plugin_continues(self, mock_entry_points):
        """
        Test D: Non-strict missing plugin continues.

        In non-strict mode, if a requested plugin doesn't exist, a warning
        should be generated but loading should continue with available modules.
        """
        from quack_core.modules import load_enabled_entry_points, registry

        # Create mock entry points (only fs exists)
        fs_plugin = MockTestPlugin(plugin_id="fs", name="FileSystem")

        fs_ep = Mock()
        fs_ep.name = "fs"
        fs_ep.value = "quack_core.core.fs:create_plugin"
        fs_ep.load.return_value = lambda: fs_plugin

        mock_entry_points.return_value = [fs_ep]

        # Try to load with non-existent plugin in non-strict mode
        result = load_enabled_entry_points(
            enabled=["does_not_exist", "fs"],
            strict=False,
        )

        # Verify warnings but partial success
        self.assertTrue(result.success)  # Can still succeed partially
        self.assertEqual(result.loaded, ["fs"])
        self.assertEqual(len(result.errors), 0)
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("does_not_exist", result.warnings[0])

        # Verify fs WAS loaded despite the missing plugin
        registered_ids = registry.list_ids()
        self.assertEqual(len(registered_ids), 1)
        self.assertIn("fs", registered_ids)

    @patch("quack_core.modules.discovery.entry_points")
    def test_load_preserves_order(self, mock_entry_points):
        """Verify that modules are loaded in the order specified."""
        from quack_core.modules import load_enabled_entry_points

        # Create modules
        plugins = [
            MockTestPlugin(plugin_id="alpha", name="Alpha"),
            MockTestPlugin(plugin_id="beta", name="Beta"),
            MockTestPlugin(plugin_id="gamma", name="Gamma"),
        ]

        # Create entry points
        entry_points = []
        for plugin in plugins:
            ep = Mock()
            ep.name = plugin.plugin_id
            ep.value = f"test.{plugin.plugin_id}:create_plugin"
            ep.load.return_value = lambda p=plugin: p
            entry_points.append(ep)

        mock_entry_points.return_value = entry_points

        # Load in specific order (reversed)
        result = load_enabled_entry_points(
            enabled=["gamma", "alpha", "beta"]
        )

        # Verify order is preserved
        self.assertEqual(result.loaded, ["gamma", "alpha", "beta"])

    @patch("quack_core.modules.discovery.entry_points")
    def test_auto_register_false_does_not_register(self, mock_entry_points):
        """Test that auto_register=False prevents automatic registration."""
        from quack_core.modules import load_enabled_entry_points, registry

        # Create mock plugin
        plugin = MockTestPlugin(plugin_id="test", name="Test")

        ep = Mock()
        ep.name = "test"
        ep.value = "test.plugin:create_plugin"
        ep.load.return_value = lambda: plugin

        mock_entry_points.return_value = [ep]

        # Load without auto-registration
        result = load_enabled_entry_points(
            enabled=["test"],
            auto_register=False,
        )

        # Verify load succeeded
        self.assertTrue(result.success)
        self.assertEqual(result.loaded, ["test"])

        # Verify plugin is NOT in registry
        self.assertEqual(len(registry.list_ids()), 0)

    @patch("quack_core.modules.discovery.entry_points")
    def test_plugin_id_must_match_entry_point_name(self, mock_entry_points):
        """Test that plugin_id must match entry point name for deterministic behavior."""
        from quack_core.modules import load_enabled_entry_points, registry

        # Create mock plugin with DIFFERENT plugin_id than entry point name
        plugin = MockTestPlugin(plugin_id="different_id", name="Test")

        ep = Mock()
        ep.name = "entry_point_name"
        ep.value = "test.plugin:create_plugin"
        ep.load.return_value = lambda: plugin

        mock_entry_points.return_value = [ep]

        # Try to load - should fail due to identity mismatch
        result = load_enabled_entry_points(
            enabled=["entry_point_name"],
            strict=True,
        )

        # Verify failure
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        self.assertIn("identity mismatch", result.errors[0].lower())
        self.assertIn("entry_point_name", result.errors[0])
        self.assertIn("different_id", result.errors[0])

        # Verify nothing was registered
        self.assertEqual(len(registry.list_ids()), 0)


class TestPluginIdStability(unittest.TestCase):
    """Test that plugin_id is used as the stable identifier."""

    def setUp(self):
        """Clean registry before each test."""
        from quack_core.modules import registry
        registry.clear()

    def tearDown(self):
        """Clean registry after each test."""
        from quack_core.modules import registry
        registry.clear()

    def test_registry_uses_plugin_id_not_name(self):
        """Verify that registry keys on plugin_id, not name."""
        from quack_core.modules import registry

        # Create plugin where plugin_id differs from name
        plugin = MockTestPlugin(plugin_id="my_plugin_id", name="Different Display Name")

        # Register
        registry.register(plugin)

        # Verify we can retrieve by plugin_id
        retrieved = registry.get_plugin("my_plugin_id")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.plugin_id, "my_plugin_id")
        self.assertEqual(retrieved.name, "Different Display Name")

        # Verify we CANNOT retrieve by name
        by_name = registry.get_plugin("Different Display Name")
        self.assertIsNone(by_name)

    def test_registry_list_ids_returns_plugin_ids(self):
        """Verify that list_ids returns plugin_id values, not names."""
        from quack_core.modules import registry

        # Register modules with different IDs and names
        registry.register(MockTestPlugin(plugin_id="id_one", name="Name One"))
        registry.register(MockTestPlugin(plugin_id="id_two", name="Name Two"))

        ids = registry.list_ids()

        # Should contain plugin_ids
        self.assertIn("id_one", ids)
        self.assertIn("id_two", ids)

        # Should NOT contain names
        self.assertNotIn("Name One", ids)
        self.assertNotIn("Name Two", ids)

    def test_duplicate_plugin_id_raises_error(self):
        """Verify that registering duplicate plugin_id raises error."""
        from quack_core.modules import registry

        # Register first plugin
        registry.register(MockTestPlugin(plugin_id="duplicate", name="First"))

        # Attempt to register second plugin with same ID
        with self.assertRaises(QuackPluginError) as ctx:
            registry.register(MockTestPlugin(plugin_id="duplicate", name="Second"))

        self.assertIn("duplicate", str(ctx.exception).lower())
        self.assertIn("already registered", str(ctx.exception).lower())


class TestRegistryClear(unittest.TestCase):
    """Test the registry clear() method."""

    def test_clear_removes_all_plugins(self):
        """Verify that clear() removes all modules from registry."""
        from quack_core.modules import registry

        # Register multiple modules
        registry.register(MockTestPlugin(plugin_id="one", name="One"))
        registry.register(MockTestPlugin(plugin_id="two", name="Two"))
        registry.register(MockTestPlugin(plugin_id="three", name="Three"))

        # Verify they're registered
        self.assertEqual(len(registry.list_ids()), 3)

        # Clear
        registry.clear()

        # Verify everything is gone
        self.assertEqual(len(registry.list_ids()), 0)
        self.assertEqual(len(registry.list_command_plugins()), 0)
        self.assertEqual(len(registry.list_workflow_plugins()), 0)
        self.assertEqual(len(registry.list_extension_plugins()), 0)
        self.assertEqual(len(registry.list_provider_plugins()), 0)

    def test_clear_allows_re_registration(self):
        """Verify that clear() allows re-registering previously registered modules."""
        from quack_core.modules import registry

        plugin = MockTestPlugin(plugin_id="test", name="Test")

        # Register
        registry.register(plugin)
        self.assertEqual(len(registry.list_ids()), 1)

        # Clear
        registry.clear()
        self.assertEqual(len(registry.list_ids()), 0)

        # Re-register (should not raise error)
        registry.register(plugin)
        self.assertEqual(len(registry.list_ids()), 1)


class TestLoadEnabledModules(unittest.TestCase):
    """Test load_enabled_modules function."""

    def setUp(self):
        """Clean registry before each test."""
        from quack_core.modules import registry
        registry.clear()

    def tearDown(self):
        """Clean registry after each test."""
        from quack_core.modules import registry
        registry.clear()

    @patch("quack_core.modules.discovery.importlib.import_module")
    def test_load_enabled_modules_succeeds(self, mock_import):
        """Test successful loading of modules from module paths."""
        from quack_core.modules import load_enabled_modules, registry

        # Create a mock module with a create_plugin factory
        mock_module = Mock()
        plugin = MockTestPlugin(plugin_id="test_module", name="Test Module")
        mock_module.create_plugin = lambda: plugin
        mock_module.__dict__ = {"create_plugin": mock_module.create_plugin}

        mock_import.return_value = mock_module

        # Load
        result = load_enabled_modules(
            modules=["test.module.plugin"],
            strict=True,
            auto_register=True,
        )

        # Verify success
        self.assertTrue(result.success)
        self.assertEqual(result.loaded, ["test_module"])

        # Verify registration
        self.assertIn("test_module", registry.list_ids())

    @patch("quack_core.modules.discovery.importlib.import_module")
    def test_load_enabled_modules_strict_failure(self, mock_import):
        """Test that strict mode fails on first error."""
        from quack_core.modules import load_enabled_modules, registry

        # First module fails to import
        mock_import.side_effect = ImportError("Module not found")

        # Load in strict mode
        result = load_enabled_modules(
            modules=["bad.module"],
            strict=True,
            auto_register=True,
        )

        # Verify failure
        self.assertFalse(result.success)
        self.assertEqual(len(result.loaded), 0)
        self.assertGreater(len(result.errors), 0)

        # Verify nothing registered
        self.assertEqual(len(registry.list_ids()), 0)


class TestListAvailableEntryPoints(unittest.TestCase):
    """Test list_available_entry_points function."""

    @patch("quack_core.modules.discovery.entry_points")
    def test_list_available_does_not_instantiate(self, mock_entry_points):
        """Verify that listing entry points does not instantiate modules."""
        from quack_core.modules import list_available_entry_points

        # Create mock entry points
        ep1 = Mock()
        ep1.name = "fs"
        ep1.value = "quack_core.core.fs:create_plugin"

        ep2 = Mock()
        ep2.name = "paths"
        ep2.value = "quack_core.core.paths:create_plugin"

        mock_entry_points.return_value = [ep1, ep2]

        # List available
        available = list_available_entry_points()

        # Verify we got metadata
        self.assertEqual(len(available), 2)
        self.assertEqual(available[0].plugin_id, "fs")
        self.assertEqual(available[1].plugin_id, "paths")

        # Verify load() was NEVER called (no instantiation)
        ep1.load.assert_not_called()
        ep2.load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
