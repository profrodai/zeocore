# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/test_registry.py
# === QV-LLM:END ===

"""
Tests for the integration registry module.
"""

import pytest
from quack_core.core.errors import QuackError
from quack_core.integrations.core.registry import IntegrationRegistry
from quack_core.integrations.core.results import IntegrationResult


# Create a mock integration for testing
class MockIntegration:
    """Mock integration for testing."""

    def __init__(self, name="MockIntegration", version="1.0.0") -> None:
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

    def initialize(self) -> IntegrationResult:
        """Initialize the integration."""
        self._initialized = True
        return IntegrationResult.success_result(
            message=f"{self.name} initialized successfully"
        )

    def is_available(self) -> bool:
        """Check if the integration is available."""
        return self._initialized


@pytest.fixture
def registry():
    """Create a fresh registry for testing."""
    return IntegrationRegistry()


@pytest.fixture
def mock_integration():
    """Create a mock integration for testing."""
    return MockIntegration()


def test_registry_creation(registry):
    """Test that the registry can be created."""
    assert registry is not None
    assert isinstance(registry, IntegrationRegistry)
    assert registry.list_ids() == []


def test_register_integration(registry, mock_integration):
    """Test registering an integration."""
    # Register the integration
    registry.register(mock_integration)

    # Verify it's registered
    assert registry.is_registered(mock_integration.name)
    assert registry.list_ids() == [mock_integration.name]
    assert registry.get_integration(mock_integration.name) is mock_integration


def test_register_duplicate_integration(registry, mock_integration):
    """Test that registering a duplicate integration raises an error."""
    # Register the integration
    registry.register(mock_integration)

    # Try to register the same integration again
    with pytest.raises(QuackError) as excinfo:
        registry.register(mock_integration)

    # Verify the error message
    assert "already registered" in str(excinfo.value)


def test_unregister_integration(registry, mock_integration):
    """Test unregistering an integration."""
    # Register then unregister the integration
    registry.register(mock_integration)
    result = registry.unregister(mock_integration.name)

    # Verify it's unregistered
    assert result is True
    assert not registry.is_registered(mock_integration.name)
    assert registry.list_ids() == []
    assert registry.get_integration(mock_integration.name) is None


def test_unregister_nonexistent_integration(registry):
    """Test unregistering a non-existent integration."""
    # Try to unregister a non-existent integration
    result = registry.unregister("NonExistentIntegration")

    # Verify the result
    assert result is False


def test_get_integration_by_type(registry):
    """Test getting integrations by type."""
    # Create mock integrations of different types
    integration1 = MockIntegration("Integration1")
    integration2 = MockIntegration("Integration2")

    # Register the integrations
    registry.register(integration1)
    registry.register(integration2)

    # Get integrations by type
    integrations = list(registry.get_integration_by_type(MockIntegration))

    # Verify the result
    assert len(integrations) == 2
    assert integration1 in integrations
    assert integration2 in integrations


def test_registry_is_pure_container_no_discovery(registry):
    """The registry is a pure container: it registers whatever is handed to
    it explicitly and performs no module discovery or import side effects
    (per registry.py's own docstring: "avoids any auto-discovery logic or
    side effects" -- the module-loading API this test used to exercise,
    `load_integration_module`, was deliberately removed).
    """
    module_integration = MockIntegration("ModuleIntegration")

    # The only supported path is explicit registration by the caller.
    registry.register(module_integration)

    assert registry.is_registered("ModuleIntegration")
    assert registry.list_ids() == ["ModuleIntegration"]
    assert registry.get_integration("ModuleIntegration") is module_integration

    # No dynamic-loading surface remains on the registry.
    assert not hasattr(registry, "load_integration_module")
