# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_plugins/test_discovery.py
# role: tests
# neighbors: __init__.py, test_explicit_loading.py, test_protocols.py, test_registry.py
# exports: MockPlugin, TestPluginLoader
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Tests for plugin discovery functionality.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackPluginError
from quack_core.plugins.discovery import PluginLoader
from quack_core.plugins.protocols import QuackPluginMetadata, QuackPluginProtocol


# Mock plugin implementation for testing
class MockPlugin(QuackPluginProtocol):
    """Mock plugin implementation for testing."""

    @property
    def name(self) -> str:
        return "mock_plugin"

    def get_metadata(self) -> QuackPluginMetadata:
        """Get plugin metadata."""
        return QuackPluginMetadata(
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
        """Test loading plugins from entry points."""
        loader = PluginLoader()
        mock_plugin = MockPlugin()
        mock_factory = MagicMock(return_value=mock_plugin)
        mock_ep1 = MagicMock()
        mock_ep1.name = "plugin1"
        mock_ep1.value = "module:factory"
        mock_ep1.load.return_value = mock_factory

        with patch(
            "importlib.metadata.entry_points", return_value=[mock_ep1]
        ) as mock_entry_points:
            plugins = loader.load_entry_points("test.plugins")
            assert len(plugins) == 1
            assert plugins[0] is mock_plugin
            mock_entry_points.assert_called_once_with(group="test.plugins")
            mock_ep1.load.assert_called_once()
            mock_factory.assert_called_once()

        with patch("importlib.metadata.entry_points", return_value=[mock_ep1]):
            mock_ep1.load.side_effect = Exception("Test error")
            plugins = loader.load_entry_points("test.plugins")
            assert len(plugins) == 0

        with patch(
            "importlib.metadata.entry_points", side_effect=Exception("Test error")
        ):
            plugins = loader.load_entry_points("test.plugins")
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
        # Instead of using a MagicMock for the module, create a dummy module using ModuleType.
        import types

        mock_module = types.ModuleType("test.module")
        mock_module.MockPlugin = MockPlugin
        mock_module.MockPlugin.__module__ = "test.module"
        with patch.dict(sys.modules, {"test.module": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                plugin = loader.load_plugin("test.module")
                assert isinstance(plugin, MockPlugin)

        # Test error when no plugin found.
        mock_module = MagicMock()
        mock_module.__name__ = "test.module"
        with patch.dict(sys.modules, {"test.module": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                with pytest.raises(QuackPluginError):
                    loader.load_plugin("test.module")

        # Test import error.
        with patch("importlib.import_module", side_effect=ImportError("Test error")):
            with pytest.raises(QuackPluginError):
                loader.load_plugin("test.module")

        # Test error creating plugin.
        mock_module = MagicMock()
        mock_module.create_plugin = MagicMock(side_effect=Exception("Test error"))
        with patch.dict(sys.modules, {"test.module": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                with pytest.raises(QuackPluginError):
                    loader.load_plugin("test.module")

        # Test plugin without name attribute.
        # Use a dummy class that does not define a 'name' property.
        class PluginNoName:
            pass

        mock_module = MagicMock()
        mock_module.create_plugin = MagicMock(return_value=PluginNoName())
        with patch.dict(sys.modules, {"test.module": mock_module}):
            with patch("importlib.import_module", return_value=mock_module):
                with pytest.raises(QuackPluginError):
                    loader.load_plugin("test.module")

    def test_load_plugins(self) -> None:
        """Test loading multiple plugins from module paths."""
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
            mock_load.side_effect = [mock_plugin1, QuackPluginError("Test error")]
            plugins = loader.load_plugins(["test.module1", "test.module2"])
            assert len(plugins) == 1
            assert plugins[0] is mock_plugin1
            assert mock_load.call_count == 2

    def test_discover_plugins(self) -> None:
        """Test discovering plugins from entry points and modules."""
        loader = PluginLoader()
        mock_plugin1 = MockPlugin()
        mock_plugin2 = MockPlugin()
        with patch.object(loader, "load_entry_points") as mock_load_eps:
            with patch.object(loader, "load_plugins") as mock_load_plugins:
                mock_load_eps.return_value = [mock_plugin1]
                mock_load_plugins.return_value = [mock_plugin2]
                plugins = loader.discover_plugins("test.plugins", ["test.module"])
                assert len(plugins) == 2
                assert plugins[0] is mock_plugin1
                assert plugins[1] is mock_plugin2
                mock_load_eps.assert_called_once_with("test.plugins")
                mock_load_plugins.assert_called_once_with(["test.module"])

        with patch.object(loader, "load_entry_points") as mock_load_eps:
            mock_load_eps.return_value = [mock_plugin1]
            plugins = loader.discover_plugins("test.plugins")
            assert len(plugins) == 1
            assert plugins[0] is mock_plugin1
            mock_load_eps.assert_called_once_with("test.plugins")
