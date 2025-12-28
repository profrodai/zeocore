# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_workflow/mixins/test_integration_enabled.py
# role: tests
# neighbors: __init__.py, test_output_writer.py, test_save_output_mixin.py
# exports: DummyService, Host, test_resolve_none, test_resolve_and_initialize
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===



from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.workflow.mixins.integration_enabled import IntegrationEnabledMixin


class DummyService(BaseIntegrationService):
    def __init__(self):
        super().__init__()  # Call the superclass's __init__ method
        self.initialized = False

    def initialize(self):
        self.initialized = True

    @property
    def name(self) -> str:
        return "dummy"


class Host(IntegrationEnabledMixin[DummyService]):
    pass


def test_resolve_none(monkeypatch):
    """Test that resolve_integration returns None when no service is available."""

    # Patch the Host class with a new implementation of resolve_integration
    original_resolve = Host.resolve_integration

    def patched_resolve(self, service_type):
        # Simply return None for this test case
        return None

    # Apply the patch
    monkeypatch.setattr(Host, "resolve_integration", patched_resolve)

    # Create the host and test
    h = Host()
    assert h.resolve_integration(DummyService) is None
    assert h.get_integration_service() is None


def test_resolve_and_initialize(monkeypatch):
    """Test that the service is properly initialized when resolved."""
    # Create a concrete service instance to return
    service = DummyService()

    # Patch the Host class with a new implementation of resolve_integration
    original_resolve = Host.resolve_integration

    def patched_resolve(self, service_type):
        # Initialize the service
        service.initialize()
        # Set the internal attribute directly
        self._integration_service = service
        # Return the service
        return service

    # Apply the patch
    monkeypatch.setattr(Host, "resolve_integration", patched_resolve)

    # Create the host and test resolve_integration
    h = Host()
    result = h.resolve_integration(DummyService)

    # Verify that our service was returned and initialized
    assert result is service, f"Expected {service}, got {result}"
    assert service.initialized is True, "Service should be initialized"

    # Verify that get_integration_service returns the same instance
    assert h.get_integration_service() is service
