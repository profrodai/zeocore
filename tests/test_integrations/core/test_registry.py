"""
Tests for the integration registry module.
"""

import pytest

from zeo_core.core.errors import ZeoError
from zeo_core.integrations.core.registry import IntegrationRegistry
from zeo_core.integrations.core.results import IntegrationResult


# Create a mock integration for testing
class MockIntegration:
    """Mock integration for testing."""

    def __init__(self, name: str = "MockIntegration", version: str = "1.0.0") -> None:
        self.name_value = name
        self.version_value = version
        self._initialized = False

    # Deliberately does NOT implement integration_id: this mock exercises
    # IntegrationRegistry's documented legacy fallback path ("Prefer
    # integration_id, fallback to name if missing", registry.py's own
    # register()), which every assertion below is keyed on (is_registered,
    # list_ids, get_integration all use mock_integration.name). Adding
    # integration_id here would silently switch these tests onto the
    # integration_id-keyed path instead and desync the assertions from what
    # they actually verify -- confirmed live: doing so broke
    # test_register_integration/test_unregister_integration/
    # test_registry_is_pure_container_no_discovery. The resulting
    # IntegrationProtocol mismatch is real (register()'s param type is
    # IntegrationProtocol, which now requires integration_id) but is a
    # narrowing of the runtime-supported legacy contract, not a defect in
    # this mock -- scoped ignores are applied at each register() call instead.

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
def registry() -> IntegrationRegistry:
    """Create a fresh registry for testing."""
    return IntegrationRegistry()


@pytest.fixture
def mock_integration() -> MockIntegration:
    """Create a mock integration for testing."""
    return MockIntegration()


def test_registry_creation(registry: IntegrationRegistry) -> None:
    """Test that the registry can be created."""
    assert registry is not None
    assert isinstance(registry, IntegrationRegistry)
    assert registry.list_ids() == []


def test_register_integration(
    registry: IntegrationRegistry, mock_integration: MockIntegration
) -> None:
    """Test registering an integration."""
    # Register the integration
    registry.register(mock_integration)  # type: ignore[arg-type]  # deliberately no integration_id, see MockIntegration's own comment

    # Verify it's registered
    assert registry.is_registered(mock_integration.name)
    assert registry.list_ids() == [mock_integration.name]
    assert registry.get_integration(mock_integration.name) is mock_integration


def test_register_duplicate_integration(
    registry: IntegrationRegistry, mock_integration: MockIntegration
) -> None:
    """Test that registering a duplicate integration raises an error."""
    # Register the integration
    registry.register(mock_integration)  # type: ignore[arg-type]  # deliberately no integration_id, see MockIntegration's own comment

    # Try to register the same integration again
    with pytest.raises(ZeoError) as excinfo:
        registry.register(mock_integration)  # type: ignore[arg-type]  # deliberately no integration_id, see MockIntegration's own comment

    # Verify the error message
    assert "already registered" in str(excinfo.value)


def test_unregister_integration(
    registry: IntegrationRegistry, mock_integration: MockIntegration
) -> None:
    """Test unregistering an integration."""
    # Register then unregister the integration
    registry.register(mock_integration)  # type: ignore[arg-type]  # deliberately no integration_id, see MockIntegration's own comment
    result = registry.unregister(mock_integration.name)

    # Verify it's unregistered
    assert result is True
    assert not registry.is_registered(mock_integration.name)
    assert registry.list_ids() == []
    assert registry.get_integration(mock_integration.name) is None


def test_unregister_nonexistent_integration(registry: IntegrationRegistry) -> None:
    """Test unregistering a non-existent integration."""
    # Try to unregister a non-existent integration
    result = registry.unregister("NonExistentIntegration")

    # Verify the result
    assert result is False


def test_get_integration_by_type(registry: IntegrationRegistry) -> None:
    """Test getting integrations by type."""
    # Create mock integrations of different types
    integration1 = MockIntegration("Integration1")
    integration2 = MockIntegration("Integration2")

    # Register the integrations
    registry.register(integration1)  # type: ignore[arg-type]  # deliberately no integration_id, see MockIntegration's own comment
    registry.register(integration2)  # type: ignore[arg-type]  # deliberately no integration_id, see MockIntegration's own comment

    # Get integrations by type
    integrations = list(
        registry.get_integration_by_type(MockIntegration)  # type: ignore[type-var]  # deliberately no integration_id, see MockIntegration's own comment
    )

    # Verify the result
    assert len(integrations) == 2
    assert integration1 in integrations
    assert integration2 in integrations


def test_registry_is_pure_container_no_discovery(registry: IntegrationRegistry) -> None:
    """The registry is a pure container: it registers whatever is handed to
    it explicitly and performs no module discovery or import side effects
    (per registry.py's own docstring: "avoids any auto-discovery logic or
    side effects" -- the module-loading API this test used to exercise,
    `load_integration_module`, was deliberately removed).
    """
    module_integration = MockIntegration("ModuleIntegration")

    # The only supported path is explicit registration by the caller.
    registry.register(module_integration)  # type: ignore[arg-type]  # deliberately no integration_id, see MockIntegration's own comment

    assert registry.is_registered("ModuleIntegration")
    assert registry.list_ids() == ["ModuleIntegration"]
    assert registry.get_integration("ModuleIntegration") is module_integration

    # No dynamic-loading surface remains on the registry.
    assert not hasattr(registry, "load_integration_module")
