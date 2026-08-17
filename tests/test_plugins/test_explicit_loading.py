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
from unittest.mock import MagicMock, Mock, patch

from zeo_core.core.errors import ZeoPluginError
from zeo_core.modules.protocols import ZeoPluginMetadata


class TestImportSideEffects(unittest.TestCase):
    """Test that importing zeo_core.modules has no side effects."""

    def setUp(self) -> None:
        """Clean up any existing plugin state before each test.

        Purging zeo_core.modules* from sys.modules forces the next `import` to
        build FRESH class objects (ZeoPluginMetadata, PluginRegistry, etc.) -
        genuinely distinct from whatever any OTHER already-imported module (e.g.
        zeo_core.core.fs.plugin, or discovery.py's own already-bound reference)
        is holding onto. Without a restore, that split leaks into every test that
        runs afterward in the same process: a plugin's get_metadata() can return
        an instance of the reloaded class while validation code elsewhere still
        checks isinstance() against the pre-purge class, producing
        "got <class '...ZeoPluginMetadata'>" errors that look like the classes
        differ even though they print identically (paid: TestExplicitLoading's
        entry-point tests failed exactly this way only when this file's full
        suite ran, never in isolation - the missing teardown was the reason).
        Save the pre-purge modules and restore them in tearDown so the purge
        does not survive past this class's own tests.
        """
        self._saved_modules = {
            key: sys.modules[key]
            for key in sys.modules
            if key.startswith("zeo_core.modules")
        }
        modules_to_remove = [
            key for key in sys.modules.keys() if key.startswith("zeo_core.modules")
        ]
        for module in modules_to_remove:
            del sys.modules[module]

    def tearDown(self) -> None:
        """Restore the pre-purge zeo_core.modules* sys.modules entries.

        Undoes setUp's purge so later test classes in this process see the
        SAME class objects they started with, instead of inheriting whatever
        fresh reload test_import_does_not_register_plugins/
        test_import_exports_expected_api triggered.
        """
        # Drop whatever got (re)imported during the test
        reimported = [
            key for key in sys.modules.keys() if key.startswith("zeo_core.modules")
        ]
        for module in reimported:
            del sys.modules[module]
        # Restore exactly what was there before setUp ran
        sys.modules.update(self._saved_modules)

    def test_import_does_not_register_plugins(self) -> None:
        """
        Test A: Import has no side effects.

        Importing zeo_core.modules must not register any modules.
        The registry should be completely empty after import.
        """
        # Import the module
        import zeo_core.modules

        # Verify registry is empty
        self.assertEqual(
            len(zeo_core.modules.registry.list_ids()),
            0,
            "Registry should be empty after import, but contains: "
            f"{zeo_core.modules.registry.list_ids()}",
        )

        # Verify no modules of any type
        self.assertEqual(len(zeo_core.modules.registry.list_command_plugins()), 0)
        self.assertEqual(len(zeo_core.modules.registry.list_workflow_plugins()), 0)
        self.assertEqual(len(zeo_core.modules.registry.list_extension_plugins()), 0)
        self.assertEqual(len(zeo_core.modules.registry.list_provider_plugins()), 0)

        # Verify no commands or workflows registered
        self.assertEqual(len(zeo_core.modules.registry.list_commands()), 0)
        self.assertEqual(len(zeo_core.modules.registry.list_workflows()), 0)

    def test_import_exports_expected_api(self) -> None:
        """Verify the module exports the expected public API."""
        import zeo_core.modules

        # Check that explicit loading functions are available
        self.assertTrue(hasattr(zeo_core.modules, "list_available_entry_points"))
        self.assertTrue(hasattr(zeo_core.modules, "load_enabled_entry_points"))
        self.assertTrue(hasattr(zeo_core.modules, "load_enabled_modules"))

        # Check that global instances are available
        self.assertTrue(hasattr(zeo_core.modules, "registry"))
        self.assertTrue(hasattr(zeo_core.modules, "loader"))

        # Check that classes are available
        self.assertTrue(hasattr(zeo_core.modules, "PluginRegistry"))
        self.assertTrue(hasattr(zeo_core.modules, "PluginLoader"))


class MockTestPlugin:
    """A minimal test plugin for testing."""

    def __init__(
        self, plugin_id: str = "test_plugin", name: str = "Test Plugin"
    ) -> None:
        self._plugin_id = plugin_id
        self._name = name

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def name(self) -> str:
        return self._name

    def get_metadata(self) -> ZeoPluginMetadata:
        return ZeoPluginMetadata(
            plugin_id=self._plugin_id,
            name=self._name,
            version="1.0.0",
            description="A test plugin",
            capabilities=["test"],
        )


class TestExplicitLoading(unittest.TestCase):
    """Test explicit plugin loading behavior."""

    def setUp(self) -> None:
        """Clean registry before each test."""
        from zeo_core.modules import registry

        registry.clear()

    def tearDown(self) -> None:
        """Clean registry after each test."""
        from zeo_core.modules import registry

        registry.clear()

    @patch("zeo_core.modules.discovery.entry_points")
    def test_explicit_load_loads_only_requested_plugins(
        self, mock_entry_points: MagicMock
    ) -> None:
        """
        Test B: Explicit load loads only requested modules.

        When we call load_enabled_entry_points with specific plugin IDs,
        only those modules should be loaded and registered.
        """
        from zeo_core.modules import load_enabled_entry_points, registry

        # Create mock entry points
        fs_plugin = MockTestPlugin(plugin_id="fs", name="FileSystem")
        paths_plugin = MockTestPlugin(plugin_id="paths", name="Paths")
        config_plugin = MockTestPlugin(plugin_id="config", name="Config")

        # Mock entry point objects
        fs_ep = Mock()
        fs_ep.name = "fs"
        fs_ep.value = "zeo_core.core.fs:create_plugin"
        fs_ep.load.return_value = lambda: fs_plugin

        paths_ep = Mock()
        paths_ep.name = "paths"
        paths_ep.value = "zeo_core.core.paths:create_plugin"
        paths_ep.load.return_value = lambda: paths_plugin

        config_ep = Mock()
        config_ep.name = "config"
        config_ep.value = "zeo_core.core.config:create_plugin"
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
        assert fs is not None  # narrow for mypy; assertIsNotNone doesn't
        self.assertEqual(fs.plugin_id, "fs")

    @patch("zeo_core.modules.discovery.entry_points")
    def test_strict_missing_plugin_fails_and_loads_nothing(
        self, mock_entry_points: MagicMock
    ) -> None:
        """
        Test C: Strict missing plugin fails and loads nothing.

        In strict mode, if a requested plugin doesn't exist, the entire
        operation should fail and NO modules should be registered.
        This now includes pre-validation, so nothing is attempted.
        """
        from zeo_core.modules import load_enabled_entry_points, registry

        # Create mock entry points (only fs exists)
        fs_plugin = MockTestPlugin(plugin_id="fs", name="FileSystem")

        fs_ep = Mock()
        fs_ep.name = "fs"
        fs_ep.value = "zeo_core.core.fs:create_plugin"
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

    @patch("zeo_core.modules.discovery.entry_points")
    def test_non_strict_missing_plugin_continues(
        self, mock_entry_points: MagicMock
    ) -> None:
        """
        Test D: Non-strict missing plugin continues.

        In non-strict mode, if a requested plugin doesn't exist, a warning
        should be generated but loading should continue with available modules.
        """
        from zeo_core.modules import load_enabled_entry_points, registry

        # Create mock entry points (only fs exists)
        fs_plugin = MockTestPlugin(plugin_id="fs", name="FileSystem")

        fs_ep = Mock()
        fs_ep.name = "fs"
        fs_ep.value = "zeo_core.core.fs:create_plugin"
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

    @patch("zeo_core.modules.discovery.entry_points")
    def test_load_preserves_order(self, mock_entry_points: MagicMock) -> None:
        """Verify that modules are loaded in the order specified."""
        from zeo_core.modules import load_enabled_entry_points

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
        result = load_enabled_entry_points(enabled=["gamma", "alpha", "beta"])

        # Verify order is preserved
        self.assertEqual(result.loaded, ["gamma", "alpha", "beta"])

    @patch("zeo_core.modules.discovery.entry_points")
    def test_auto_register_false_does_not_register(
        self, mock_entry_points: MagicMock
    ) -> None:
        """Test that auto_register=False prevents automatic registration."""
        from zeo_core.modules import load_enabled_entry_points, registry

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

    @patch("zeo_core.modules.discovery.entry_points")
    def test_plugin_id_must_match_entry_point_name(
        self, mock_entry_points: MagicMock
    ) -> None:
        """Test that plugin_id must match entry point name for deterministic
        behavior."""
        from zeo_core.modules import load_enabled_entry_points, registry

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

    def setUp(self) -> None:
        """Clean registry before each test."""
        from zeo_core.modules import registry

        registry.clear()

    def tearDown(self) -> None:
        """Clean registry after each test."""
        from zeo_core.modules import registry

        registry.clear()

    def test_registry_uses_plugin_id_not_name(self) -> None:
        """Verify that registry keys on plugin_id, not name."""
        from zeo_core.modules import registry

        # Create plugin where plugin_id differs from name
        plugin = MockTestPlugin(plugin_id="my_plugin_id", name="Different Display Name")

        # Register
        registry.register(plugin)

        # Verify we can retrieve by plugin_id
        retrieved = registry.get_plugin("my_plugin_id")
        self.assertIsNotNone(retrieved)
        assert retrieved is not None  # narrow for mypy; assertIsNotNone doesn't
        self.assertEqual(retrieved.plugin_id, "my_plugin_id")
        self.assertEqual(retrieved.name, "Different Display Name")

        # Verify we CANNOT retrieve by name
        by_name = registry.get_plugin("Different Display Name")
        self.assertIsNone(by_name)

    def test_registry_list_ids_returns_plugin_ids(self) -> None:
        """Verify that list_ids returns plugin_id values, not names."""
        from zeo_core.modules import registry

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

    def test_duplicate_plugin_id_raises_error(self) -> None:
        """Verify that registering duplicate plugin_id raises error."""
        from zeo_core.modules import registry

        # Register first plugin
        registry.register(MockTestPlugin(plugin_id="duplicate", name="First"))

        # Attempt to register second plugin with same ID
        with self.assertRaises(ZeoPluginError) as ctx:
            registry.register(MockTestPlugin(plugin_id="duplicate", name="Second"))

        self.assertIn("duplicate", str(ctx.exception).lower())
        self.assertIn("already registered", str(ctx.exception).lower())


class TestRegistryClear(unittest.TestCase):
    """Test the registry clear() method."""

    def setUp(self) -> None:
        """Clean registry before each test.

        registry is a module-level singleton shared across the whole test
        session (every test class in this file imports the same object) - this
        class was the only one missing the isolation every sibling class already
        has (TestExplicitLoading, TestPluginIdStability), so it silently counted
        whatever a preceding test happened to leave registered.
        """
        from zeo_core.modules import registry

        registry.clear()

    def tearDown(self) -> None:
        """Clean registry after each test."""
        from zeo_core.modules import registry

        registry.clear()

    def test_clear_removes_all_plugins(self) -> None:
        """Verify that clear() removes all modules from registry."""
        from zeo_core.modules import registry

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

    def test_clear_allows_re_registration(self) -> None:
        """Verify that clear() allows re-registering previously registered modules."""
        from zeo_core.modules import registry

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

    def setUp(self) -> None:
        """Clean registry before each test."""
        from zeo_core.modules import registry

        registry.clear()

    def tearDown(self) -> None:
        """Clean registry after each test."""
        from zeo_core.modules import registry

        registry.clear()

    @patch("zeo_core.modules.discovery.importlib.import_module")
    def test_load_enabled_modules_succeeds(self, mock_import: MagicMock) -> None:
        """Test successful loading of modules from module paths."""
        import types

        from zeo_core.modules import load_enabled_modules, registry

        # Create a real (not Mock) module-like object with a create_plugin
        # factory. Assigning directly to a Mock's __dict__ (the prior version of
        # this test did `mock_module.__dict__ = {...}`) wipes out Mock's own
        # internal bookkeeping attributes that live in that same __dict__
        # (_mock_methods, _mock_name, ...), corrupting the object so even a later,
        # unrelated attribute assignment on it raises AttributeError:
        # _mock_methods. types.ModuleType has no such internal state to corrupt -
        # same pattern already used correctly in
        # test_discovery.py::test_load_plugin.
        plugin = MockTestPlugin(plugin_id="test_module", name="Test Module")
        mock_module = types.ModuleType("test.module.plugin")
        mock_module.create_plugin = lambda: plugin  # type: ignore[attr-defined]

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

    @patch("zeo_core.modules.discovery.importlib.import_module")
    def test_load_enabled_modules_strict_failure(self, mock_import: MagicMock) -> None:
        """Test that strict mode fails on first error."""
        from zeo_core.modules import load_enabled_modules, registry

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

    @patch("zeo_core.modules.discovery.entry_points")
    def test_list_available_does_not_instantiate(
        self, mock_entry_points: MagicMock
    ) -> None:
        """Verify that listing entry points does not instantiate modules."""
        from zeo_core.modules import list_available_entry_points

        # Create mock entry points
        ep1 = Mock()
        ep1.name = "fs"
        ep1.value = "zeo_core.core.fs:create_plugin"

        ep2 = Mock()
        ep2.name = "paths"
        ep2.value = "zeo_core.core.paths:create_plugin"

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
