"""
Tests for plugin discovery functionality.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from zeo_core.core.errors import ZeoPluginError
from zeo_core.modules.discovery import LoadResult, PluginLoader
from zeo_core.modules.protocols import ZeoPluginMetadata, ZeoPluginProtocol


# Mock plugin implementation for testing
class MockPlugin(ZeoPluginProtocol):
    """Mock plugin implementation for testing."""

    @property
    def plugin_id(self) -> str:
        return "mock_plugin"

    @property
    def name(self) -> str:
        return "mock_plugin"

    def get_metadata(self) -> ZeoPluginMetadata:
        """Get plugin metadata."""
        return ZeoPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Mock plugin for testing",
            capabilities=[],
        )


class TestPluginLoader:
    """Tests for the PluginLoader class."""

    def test_init(self) -> None:
        """Test initializing the plugin loader."""
        loader = PluginLoader()
        assert loader.logger is not None

    def test_load_entry_points(self) -> None:
        """Test loading modules from entry points.

        discovery.py does `from importlib.metadata import entry_points`, binding
        its own local name in zeo_core.modules.discovery's namespace at import
        time. Patching "importlib.metadata.entry_points" (the origin) does not
        affect that already-bound local reference - the real entry_points() ran
        instead, picking up this package's genuinely-registered
        "zeo_core.modules" entry points (config/fs/paths/prompt, 4 total) for
        the default group, or nothing for a group like "test.modules" that has no
        real registrations - either way, not the mock. Patch where it is USED.
        """
        loader = PluginLoader()
        mock_plugin = MockPlugin()
        mock_factory = MagicMock(return_value=mock_plugin)
        mock_ep1 = MagicMock()
        mock_ep1.name = "plugin1"
        mock_ep1.value = "module:factory"
        mock_ep1.load.return_value = mock_factory

        with patch(
            "zeo_core.modules.discovery.entry_points", return_value=[mock_ep1]
        ) as mock_entry_points:
            plugins = loader.load_entry_points("test.modules")
            assert len(plugins) == 1
            assert plugins[0] is mock_plugin
            mock_entry_points.assert_called_once_with(group="test.modules")
            mock_ep1.load.assert_called_once()
            mock_factory.assert_called_once()

        with patch(
            "zeo_core.modules.discovery.entry_points", return_value=[mock_ep1]
        ):
            mock_ep1.load.side_effect = Exception("Test error")
            plugins = loader.load_entry_points("test.modules")
            assert len(plugins) == 0

        with patch(
            "zeo_core.modules.discovery.entry_points",
            side_effect=Exception("Test error"),
        ):
            plugins = loader.load_entry_points("test.modules")
            assert len(plugins) == 0

    def test_load_plugin(self) -> None:
        """Test loading a single plugin from a module path."""
        loader = PluginLoader()

        # Test loading from module with create_plugin function
        mock_module = MagicMock()
        mock_plugin = MockPlugin()
        mock_module.create_plugin = MagicMock(return_value=mock_plugin)
        with patch.dict(sys.modules, {"test.module": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                plugin = loader.load_plugin("test.module")
                assert plugin is mock_plugin
                mock_module.create_plugin.assert_called_once()

        # Test loading from module with plugin class.
        # Instead of using a MagicMock for the module, create a dummy module
        # using ModuleType.
        import types

        dummy_module = types.ModuleType("test.module")
        dummy_module.MockPlugin = MockPlugin  # type: ignore[attr-defined]
        dummy_module.MockPlugin.__module__ = "test.module"
        with patch.dict(sys.modules, {"test.module": dummy_module}):
            with patch("importlib.import_module", return_value=dummy_module):
                plugin = loader.load_plugin("test.module")
                assert isinstance(plugin, MockPlugin)

        # Test error when no plugin found.
        mock_module = MagicMock()
        mock_module.__name__ = "test.module"
        with patch.dict(sys.modules, {"test.module": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                with pytest.raises(ZeoPluginError):
                    loader.load_plugin("test.module")

        # Test import error.
        with patch("importlib.import_module", side_effect=ImportError("Test error")):
            with pytest.raises(ZeoPluginError):
                loader.load_plugin("test.module")

        # Test error creating plugin.
        mock_module = MagicMock()
        mock_module.create_plugin = MagicMock(side_effect=Exception("Test error"))
        with patch.dict(sys.modules, {"test.module": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                with pytest.raises(ZeoPluginError):
                    loader.load_plugin("test.module")

        # Test plugin without name attribute.
        # Use a dummy class that does not define a 'name' property.
        class PluginNoName:
            pass

        mock_module = MagicMock()
        mock_module.create_plugin = MagicMock(return_value=PluginNoName())
        with patch.dict(sys.modules, {"test.module": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                with pytest.raises(ZeoPluginError):
                    loader.load_plugin("test.module")

    def test_load_plugins(self) -> None:
        """Test loading multiple modules from module paths."""
        loader = PluginLoader()
        mock_module1 = MagicMock()
        mock_plugin1 = MockPlugin()
        mock_module1.create_plugin = MagicMock(return_value=mock_plugin1)
        mock_module2 = MagicMock()
        mock_plugin2 = MockPlugin()
        mock_module2.create_plugin = MagicMock(return_value=mock_plugin2)
        with patch.object(loader, "load_plugin") as mock_load:
            mock_load.side_effect = [mock_plugin1, mock_plugin2]
            plugins = loader.load_plugins(["test.module1", "test.module2"])
            assert len(plugins) == 2
            assert plugins[0] is mock_plugin1
            assert plugins[1] is mock_plugin2
            assert mock_load.call_count == 2

        with patch.object(loader, "load_plugin") as mock_load:
            mock_load.side_effect = [mock_plugin1, ZeoPluginError("Test error")]
            plugins = loader.load_plugins(["test.module1", "test.module2"])
            assert len(plugins) == 1
            assert plugins[0] is mock_plugin1
            assert mock_load.call_count == 2

    def test_discover_plugins(self) -> None:
        """Test discovering modules from entry points and modules."""
        loader = PluginLoader()
        mock_plugin1 = MockPlugin()
        mock_plugin2 = MockPlugin()
        with patch.object(loader, "load_entry_points") as mock_load_eps:
            with patch.object(loader, "load_plugins") as mock_load_plugins:
                mock_load_eps.return_value = [mock_plugin1]
                mock_load_plugins.return_value = [mock_plugin2]
                plugins = loader.discover_plugins("test.modules", ["test.module"])
                assert len(plugins) == 2
                assert plugins[0] is mock_plugin1
                assert plugins[1] is mock_plugin2
                mock_load_eps.assert_called_once_with("test.modules")
                mock_load_plugins.assert_called_once_with(["test.module"])

        with patch.object(loader, "load_entry_points") as mock_load_eps:
            mock_load_eps.return_value = [mock_plugin1]
            plugins = loader.discover_plugins("test.modules")
            assert len(plugins) == 1
            assert plugins[0] is mock_plugin1
            mock_load_eps.assert_called_once_with("test.modules")

    def test_validate_plugin_missing_plugin_id_with_get_metadata(self) -> None:
        """Covers discovery.py:161 -- a plugin that DOES implement a callable
        get_metadata() but has no plugin_id attribute at all must raise
        AttributeError (wrapped as ZeoPluginError), per the "new module"
        contract enforced by that branch.
        """
        loader = PluginLoader()

        class PluginNoPluginId:
            name = "no_id_plugin"

            def get_metadata(self) -> ZeoPluginMetadata:
                return ZeoPluginMetadata(
                    name="no_id_plugin",
                    version="1.0.0",
                    description="Missing plugin_id",
                    capabilities=[],
                )

        with pytest.raises(ZeoPluginError, match="valid plugin info"):
            loader._validate_plugin(PluginNoPluginId(), "test.module")  # type: ignore[arg-type]

    def test_validate_plugin_get_metadata_returns_dict(self) -> None:
        """Covers discovery.py:169-170 -- get_metadata() returning a plain
        dict (not a ZeoPluginMetadata instance) must be coerced via
        ZeoPluginMetadata(**metadata) rather than rejected.
        """
        loader = PluginLoader()

        class PluginDictMetadata:
            plugin_id = "dict_meta_plugin"
            name = "dict_meta_plugin"

            def get_metadata(self) -> dict[str, object]:
                return {
                    "plugin_id": "dict_meta_plugin",
                    "name": "dict_meta_plugin",
                    "version": "1.0.0",
                    "description": "Dict metadata",
                    "capabilities": [],
                }

        result = loader._validate_plugin(PluginDictMetadata(), "test.module")  # type: ignore[arg-type]
        assert result is not None
        assert result.plugin_id == "dict_meta_plugin"

    def test_validate_plugin_get_metadata_returns_invalid_type(self) -> None:
        """Covers discovery.py:171-172 -- get_metadata() returning something
        that is neither a ZeoPluginMetadata nor a dict must raise TypeError
        (wrapped as ZeoPluginError).
        """
        loader = PluginLoader()

        class PluginBadMetadataType:
            plugin_id = "bad_meta_plugin"
            name = "bad_meta_plugin"

            def get_metadata(self) -> str:
                return "not a metadata object"

        with pytest.raises(ZeoPluginError, match="must return a ZeoPluginMetadata"):
            loader._validate_plugin(PluginBadMetadataType(), "test.module")  # type: ignore[arg-type]

    def test_validate_plugin_fallback_plugin_id_from_module_path(self) -> None:
        """Covers discovery.py:183 -- when get_metadata() returns metadata
        whose plugin_id is falsy (None), validate_plugin must fall back to
        the module_path to populate PluginInfo's required plugin_id.
        """
        loader = PluginLoader()

        class PluginNoneMetadataId:
            plugin_id = "actual_id"
            name = "plugin_with_none_metadata_id"

            def get_metadata(self) -> ZeoPluginMetadata:
                # Deliberately omit plugin_id so metadata.model_dump()
                # yields plugin_id=None, forcing the fallback-to-module_path
                # branch at line 183.
                return ZeoPluginMetadata(
                    name="plugin_with_none_metadata_id",
                    version="1.0.0",
                    description="No plugin_id in metadata",
                    capabilities=[],
                )

        result = loader._validate_plugin(
            PluginNoneMetadataId(), "fallback.module.path"
        )
        assert result is not None

    def test_load_from_class_error_initializing(self) -> None:
        """Covers discovery.py:262-263 -- _load_from_class catches and logs
        exceptions raised while instantiating or validating a discovered
        MockPlugin class, returning None instead of propagating.
        """
        loader = PluginLoader()

        import types

        class BadMockPlugin:
            def __init__(self) -> None:
                raise RuntimeError("boom")

        mock_module = types.ModuleType("test.module.badclass")
        mock_module.MockPlugin = BadMockPlugin  # type: ignore[attr-defined]

        result = loader._load_from_class(mock_module, "test.module.badclass")
        assert result is None

    def test_load_from_dict_success(self) -> None:
        """Covers discovery.py:287-296 -- _load_from_dict's success path:
        a module whose __dict__ contains "MockPlugin" (found via getattr,
        not inspect.getmembers) is instantiated, validated, and returned.

        This path is only reached when _load_from_class does NOT find a
        class literally named "MockPlugin" via inspect.getmembers -- so we
        use a module-level dict entry named "MockPlugin" that inspect
        .getmembers still enumerates by the same name. To force the dict
        fallback specifically, we exercise _load_from_dict directly.
        """
        loader = PluginLoader()

        import types

        mock_plugin = MockPlugin()
        mock_module = types.ModuleType("test.module.dictplugin")
        mock_module.MockPlugin = lambda: mock_plugin  # type: ignore[attr-defined]

        result = loader._load_from_dict(mock_module, "test.module.dictplugin")
        assert result is mock_plugin

    def test_load_from_dict_error_initializing(self) -> None:
        """Covers discovery.py:296-297 -- _load_from_dict catches and logs
        exceptions raised while instantiating/validating the plugin found
        via module.__dict__, returning None instead of propagating.
        """
        loader = PluginLoader()

        import types

        def bad_factory() -> None:
            raise RuntimeError("boom")

        mock_module = types.ModuleType("test.module.baddict")
        mock_module.MockPlugin = bad_factory  # type: ignore[attr-defined]

        result = loader._load_from_dict(mock_module, "test.module.baddict")
        assert result is None

    def test_load_plugin_falls_through_to_dict_lookup(self) -> None:
        """Covers discovery.py:344-347 -- load_plugin's dict-lookup fallback
        branch is reached (and returns) when neither factory nor class
        lookup succeeds, but the module's __dict__ still has "MockPlugin".

        Achieved with a module.__dict__ entry that is not a class (so
        inspect.getmembers + isclass in _load_from_class does not match it),
        forcing control through to _load_from_dict inside load_plugin.
        """
        loader = PluginLoader()

        import types

        mock_plugin = MockPlugin()
        mock_module = types.ModuleType("test.module.dictfallback")
        # A callable (not a class) named MockPlugin: _load_from_class's
        # inspect.isclass(obj) check skips it, but _load_from_dict's
        # attr-in-__dict__ check finds and calls it.
        mock_module.MockPlugin = lambda: mock_plugin  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"test.module.dictfallback": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                plugin = loader.load_plugin("test.module.dictfallback")
                assert plugin is mock_plugin

    def test_load_entry_points_import_error_getting_entry_points(self) -> None:
        """Covers discovery.py:427-429 -- when entry_points(group=...) itself
        raises ImportError/AttributeError, load_entry_points logs and
        returns the (empty) plugins list built so far instead of propagating.
        """
        loader = PluginLoader()

        with patch(
            "zeo_core.modules.discovery.entry_points",
            side_effect=ImportError("no such group"),
        ):
            plugins = loader.load_entry_points("test.modules")
            assert plugins == []

    def test_list_available_entry_points_error(self) -> None:
        """Covers discovery.py:484-485 -- list_available_entry_points catches
        ImportError/AttributeError raised by entry_points(group=...) and
        returns an empty list rather than propagating.
        """
        loader = PluginLoader()

        with patch(
            "zeo_core.modules.discovery.entry_points",
            side_effect=AttributeError("bad group"),
        ):
            available = loader.list_available_entry_points("test.modules")
            assert available == []

    def test_rollback_registered_plugins_empty_is_noop(self) -> None:
        """Covers discovery.py:500-501 -- an empty registered_ids list makes
        _rollback_registered_plugins a no-op (early return), never touching
        the registry.
        """
        loader = PluginLoader()
        mock_registry = MagicMock()

        loader._rollback_registered_plugins(mock_registry, [])
        mock_registry.unregister.assert_not_called()

    def test_rollback_registered_plugins_unregister_error_logged(self) -> None:
        """Covers discovery.py:503-511 -- _rollback_registered_plugins logs
        (but does not raise) when registry.unregister() itself fails for one
        of the plugins being rolled back, and continues rolling back the rest.
        """
        loader = PluginLoader()
        mock_registry = MagicMock()
        mock_registry.unregister.side_effect = [RuntimeError("cannot unregister"), None]

        # Should not raise despite the first unregister failing.
        loader._rollback_registered_plugins(mock_registry, ["id_one", "id_two"])
        assert mock_registry.unregister.call_count == 2

    def test_load_one_entry_point_factory_not_callable(self) -> None:
        """Covers discovery.py:544-545 -- when ep.load() returns something
        that is not callable, _load_one_entry_point raises ValueError
        internally, which (in strict mode) is caught and reported as a
        result error rather than propagating.
        """
        loader = PluginLoader()
        mock_registry = MagicMock()
        result = LoadResult(success=True)

        ep = MagicMock()
        ep.name = "bad_ep"
        ep.value = "test:not_callable"
        ep.load.return_value = "not callable"

        keep_going = loader._load_one_entry_point(
            "bad_ep", ep, mock_registry, result, [], True, True
        )

        assert keep_going is False
        assert result.success is False
        assert any("not callable" in e for e in result.errors)

    def test_load_one_entry_point_non_strict_warns_and_continues(self) -> None:
        """Covers discovery.py:589-592 -- in non-strict mode, a failure while
        loading a single entry point is recorded as a warning (not an error)
        and the caller is told to keep iterating (return True).
        """
        loader = PluginLoader()
        mock_registry = MagicMock()
        result = LoadResult(success=True)

        ep = MagicMock()
        ep.name = "bad_ep"
        ep.value = "test:raises"
        ep.load.side_effect = RuntimeError("load failed")

        keep_going = loader._load_one_entry_point(
            "bad_ep", ep, mock_registry, result, [], False, True
        )

        assert keep_going is True
        assert result.success is True
        assert any("bad_ep" in w for w in result.warnings)
        assert result.errors == []

    def test_load_enabled_entry_points_error_getting_entry_points(self) -> None:
        """Covers discovery.py:639-643 -- load_enabled_entry_points catches
        ImportError/AttributeError raised when fetching entry_points(group=
        ...) up front and returns a failed LoadResult immediately.
        """
        with patch(
            "zeo_core.modules.discovery.entry_points",
            side_effect=ImportError("bad group"),
        ):
            from zeo_core.modules import load_enabled_entry_points

            result = load_enabled_entry_points(enabled=["fs"], group="bogus.group")
            assert result.success is False
            assert any("Failed to load entry points" in e for e in result.errors)

    @patch("zeo_core.modules.discovery.entry_points")
    def test_load_enabled_entry_points_non_strict_all_warnings_fails(
        self, mock_entry_points: MagicMock
    ) -> None:
        """Covers discovery.py:681-682 and 691-695 -- in non-strict mode, if
        NOTHING loaded and there ARE warnings (e.g. every requested plugin id
        was missing from the entry point map), overall success flips to
        False and the error-summary log branch executes.
        """
        from zeo_core.modules import load_enabled_entry_points, registry

        registry.clear()
        mock_entry_points.return_value = []

        result = load_enabled_entry_points(
            enabled=["totally_missing"], strict=False
        )

        assert result.success is False
        assert result.loaded == []
        assert any("totally_missing" in w for w in result.warnings)
        registry.clear()

    def test_load_one_module_path_auto_register_false_logs_debug(self) -> None:
        """Covers discovery.py:736-737 -- when auto_register=False,
        _load_one_module_path takes the "Loaded ... " debug-log branch
        instead of registering + the "Registered ..." branch.
        """
        loader = PluginLoader()
        mock_registry = MagicMock()
        result = LoadResult(success=True)
        mock_plugin = MockPlugin()

        with patch.object(loader, "load_plugin", return_value=mock_plugin):
            keep_going = loader._load_one_module_path(
                "test.module.path", mock_registry, result, [], True, False
            )

        assert keep_going is True
        mock_registry.register.assert_not_called()
        assert result.loaded == ["mock_plugin"]

    def test_load_one_module_path_non_strict_warns_and_continues(self) -> None:
        """Covers discovery.py:757-760 -- in non-strict mode, a failure while
        loading a single module path is recorded as a warning (not an
        error), and the caller is told to keep iterating (return True).
        """
        loader = PluginLoader()
        mock_registry = MagicMock()
        result = LoadResult(success=True)

        with patch.object(
            loader, "load_plugin", side_effect=ZeoPluginError("load failed")
        ):
            keep_going = loader._load_one_module_path(
                "bad.module.path", mock_registry, result, [], False, True
            )

        assert keep_going is True
        assert result.success is True
        assert any("bad.module.path" in w for w in result.warnings)
        assert result.errors == []

    def test_load_enabled_modules_non_strict_all_warnings_fails(self) -> None:
        """Covers discovery.py:802-803 and 812-818 -- in non-strict mode, if
        every module path fails to load (nothing loaded, only warnings),
        overall success flips to False and the error-summary log branch
        executes.
        """
        loader = PluginLoader()

        with patch.object(
            loader, "load_plugin", side_effect=ZeoPluginError("nope")
        ):
            result = loader.load_enabled_modules(
                modules=["bad.module.a", "bad.module.b"],
                strict=False,
                auto_register=True,
            )

        assert result.success is False
        assert result.loaded == []
        assert len(result.warnings) == 2

    def test_load_enabled_modules_success_with_warnings_logs_info(self) -> None:
        """Covers discovery.py:806-811 -- the success-path summary logging
        (including the "with N warning(s)" branch) when at least one module
        loads successfully in non-strict mode alongside a failing one.
        """
        loader = PluginLoader()
        mock_plugin = MockPlugin()

        def fake_load_plugin(module_path: str) -> ZeoPluginProtocol:
            if module_path == "good.module":
                return mock_plugin
            raise ZeoPluginError("bad module")

        with patch.object(loader, "load_plugin", side_effect=fake_load_plugin):
            result = loader.load_enabled_modules(
                modules=["good.module", "bad.module"],
                strict=False,
                auto_register=False,
            )

        assert result.success is True
        assert result.loaded == ["mock_plugin"]
        assert len(result.warnings) == 1
