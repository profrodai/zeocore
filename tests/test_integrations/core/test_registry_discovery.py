# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/test_registry_discovery.py
# role: tests
# neighbors: __init__.py, test_get_service.py, test_protocol_inheritance.py, test_protocols.py, test_registry.py, test_results.py
# exports: MockIntegration, MockPluginLoader, MockEntryPoint, TestIntegrationRegistryDiscovery
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
Tests for the integration registry discovery features.

This module tests the integration discovery functionality of the registry,
including entry point discovery and dynamic loading.
"""

import sys
from importlib.metadata import EntryPoint
from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackError
from quack_core.integrations.core.registry import (
    IntegrationRegistry,
    PluginLoaderProtocol,
)


class MockIntegration:
    """Mock integration for testing."""

    def __init__(self, name="MockIntegration", version="1.0.0"):
        self.name_value = name
        self.version_value = version
        self._initialized = False

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return self.name_value

    @property
    def version(self) -> str:
        """Get the version of the integration."""
        return self.version_value

    def initialize(self):
        """Initialize the integration."""
        self._initialized = True
        return {"success": True, "message": f"{self.name} initialized successfully"}

    def is_available(self) -> bool:
        """Check if the integration is available."""
        return self._initialized


class MockPluginLoader(PluginLoaderProtocol):
    """Mock plugin loader for testing."""

    def __init__(self, plugins=None):
        self.plugins = plugins or {}

    def load_plugin(self, identifier: str) -> object:
        """Load a plugin given its identifier."""
        if identifier in self.plugins:
            return self.plugins[identifier]
        raise ImportError(f"Plugin {identifier} not found")


class MockEntryPoint:
    """Mock entry point for testing."""

    def __init__(self, name, value, factory=None):
        self.name = name
        self.value = value
        self._factory = factory

    def load(self):
        """Load the entry point."""
        if self._factory:
            return self._factory
        raise ImportError(f"Could not load {self.name}")


class TestIntegrationRegistryDiscovery:
    """Tests for the integration registry discovery features."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing."""
        return IntegrationRegistry()

    def test_discover_integrations(self, registry):
        """Test discovering integrations from entry points."""
        # Mock entry points
        mock_entry_points = [
            MockEntryPoint(
                "integration1",
                "quack_core.integrations.integration1",
                lambda: MockIntegration("Integration1"),
            ),
            MockEntryPoint(
                "integration2",
                "quack_core.integrations.integration2",
                lambda: MockIntegration("Integration2"),
            ),
        ]

        # Mock entry_points function
        with patch(
            "quack_core.integrations.core.registry.IntegrationRegistry._get_entry_points"
        ) as mock_get_eps:
            mock_get_eps.return_value = mock_entry_points

            # Test discovery with no plugin loader
            with patch(
                "quack_core.integrations.core.registry.IntegrationRegistry._get_plugin_loader"
            ) as mock_get_loader:
                mock_get_loader.return_value = None

                discovered = registry.discover_integrations()
                assert len(discovered) == 2
                assert registry.is_registered("Integration1")
                assert registry.is_registered("Integration2")

        # Test discovery with plugin loader
        mock_plugin_loader = MockPluginLoader(
            {
                "quack_core.integrations.integration3": MockIntegration("Integration3"),
                "quack_core.integrations.integration4": MockIntegration("Integration4"),
            }
        )

        with patch(
            "quack_core.integrations.core.registry.IntegrationRegistry._get_entry_points"
        ) as mock_get_eps:
            mock_get_eps.return_value = [
                MockEntryPoint("integration3", "quack_core.integrations.integration3"),
                MockEntryPoint("integration4", "quack_core.integrations.integration4"),
            ]

            with patch(
                "quack_core.integrations.core.registry.IntegrationRegistry._get_plugin_loader"
            ) as mock_get_loader:
                mock_get_loader.return_value = mock_plugin_loader

                registry = IntegrationRegistry()  # Create fresh registry
                discovered = registry.discover_integrations()
                assert len(discovered) == 2
                assert registry.is_registered("Integration3")
                assert registry.is_registered("Integration4")

        # Test with entry point loading errors
        with patch(
            "quack_core.integrations.core.registry.IntegrationRegistry._get_entry_points"
        ) as mock_get_eps:
            mock_get_eps.return_value = [
                MockEntryPoint("bad_entry", "quack_core.integrations.bad_entry"),
                MockEntryPoint(
                    "integration1",
                    "quack_core.integrations.integration1",
                    lambda: MockIntegration("Integration1"),
                ),
            ]

            with patch(
                "quack_core.integrations.core.registry.IntegrationRegistry._get_plugin_loader"
            ) as mock_get_loader:
                mock_get_loader.return_value = None

                registry = IntegrationRegistry()  # Create fresh registry
                discovered = registry.discover_integrations()
                assert len(discovered) == 1
                assert registry.is_registered("Integration1")
                assert not registry.is_registered("bad_entry")

    def test_get_entry_points(self, registry):
        """Test retrieving entry points."""
        # Mock entry_points function
        mock_eps = [
            EntryPoint(
                name="integration1",
                value="quack_core.integrations.integration1",
                group="quack_core.integrations",
            ),
            EntryPoint(
                name="integration2",
                value="quack_core.integrations.integration2",
                group="quack_core.integrations",
            ),
        ]

        with patch("importlib.metadata.entry_points") as mock_entry_points:
            mock_entry_points.return_value = mock_eps

            entry_points = registry._get_entry_points("quack_core.integrations")
            assert len(entry_points) == 2
            assert entry_points[0].name == "integration1"
            assert entry_points[1].name == "integration2"

        # Test with exception
        with patch("importlib.metadata.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = Exception("Entry points error")

            entry_points = registry._get_entry_points("quack_core.integrations")
            assert entry_points == []

    def test_get_plugin_loader(self, registry):
        """Test retrieving the plugin loader."""
        # Test with available plugin loader
        mock_loader = MagicMock()

        # Create a mock module with a loader attribute
        mock_discovery = MagicMock()
        mock_discovery.loader = mock_loader

        # Patch sys.modules to include our mock
        with patch.dict(sys.modules, {"quack_core.plugins.discovery": mock_discovery}):
            loader = registry._get_plugin_loader()
            assert loader is mock_loader

        # Test with ImportError - completely patch sys and importlib to ensure isolation
        with patch.object(sys, "modules", {}):  # Empty modules dict
            with patch(
                "importlib.import_module", side_effect=ImportError("Module not found")
            ):
                loader = registry._get_plugin_loader()
                assert loader is None

    def test_load_integration_module(self, registry):
        """Test loading integrations from a module."""
        # Test with plugin loader
        mock_plugin_loader = MockPluginLoader(
            {
                "test.module": MockIntegration("PluginIntegration"),
            }
        )

        with patch(
            "quack_core.integrations.core.registry.IntegrationRegistry._get_plugin_loader"
        ) as mock_get_loader:
            mock_get_loader.return_value = mock_plugin_loader

            loaded = registry.load_integration_module("test.module")
            assert len(loaded) == 1
            assert loaded[0].name == "PluginIntegration"
            assert registry.is_registered("PluginIntegration")

        # Test with factory function - use a fresh registry and ensure _get_plugin_loader returns None
        registry = IntegrationRegistry()  # Create fresh registry

        class MockModule:
            def create_integration(self):
                return MockIntegration("FactoryIntegration")

        mock_module = MockModule()

        with patch(
            "quack_core.integrations.core.registry.IntegrationRegistry._get_plugin_loader",
            return_value=None,
        ):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = mock_module

                loaded = registry.load_integration_module("test.factory_module")
                assert len(loaded) == 1
                assert loaded[0].name == "FactoryIntegration"
                assert registry.is_registered("FactoryIntegration")

        # Test with integration classes in module
        registry = IntegrationRegistry()  # Create fresh registry

        # Define the test integration class that follows the protocol without inheritance
        class TestIntegrationClass:
            @property
            def name(self) -> str:
                return "ClassIntegration"

            @property
            def version(self) -> str:
                return "1.0.0"

            def initialize(self):
                return {"success": True}

            def is_available(self) -> bool:
                return True

        # Create mock module with the integration class - fixed to use the class defined above
        class MockClassModule:
            __name__ = "test.class_module"
            # Add the class as an attribute
            TestIntegration = TestIntegrationClass

        mock_module = MockClassModule()

        with patch(
            "quack_core.integrations.core.registry.IntegrationRegistry._get_plugin_loader",
            return_value=None,
        ):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = mock_module

                loaded = registry.load_integration_module("test.class_module")
                assert len(loaded) == 1
                assert loaded[0].name == "ClassIntegration"
                assert registry.is_registered("ClassIntegration")

        # Test with import error
        registry = IntegrationRegistry()  # Create fresh registry

        with patch(
            "quack_core.integrations.core.registry.IntegrationRegistry._get_plugin_loader",
            return_value=None,
        ):
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError("Module not found")

                with pytest.raises(QuackError) as excinfo:
                    registry.load_integration_module("nonexistent.module")

                assert "Failed to import module" in str(excinfo.value)

        # Test with no integrations found
        registry = IntegrationRegistry()  # Create fresh registry

        with patch(
            "quack_core.integrations.core.registry.IntegrationRegistry._get_plugin_loader",
            return_value=None,
        ):
            # Create a mock module that won't match our integration detection
            empty_mock = MagicMock(spec_set=[])  # Empty spec to prevent auto-attributes

            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = empty_mock

                loaded = registry.load_integration_module("empty.module")
                assert len(loaded) == 0
