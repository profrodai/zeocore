# quack-core/tests/test_integrations/core/base/integration_service_impl.py
"""
Implementation classes for testing integration services.
"""

from quack_core.integrations.core.base import BaseIntegrationService


class MockIntegrationService(BaseIntegrationService):
    """Mock implementation of BaseIntegrationService for testing."""

    @property
    def name(self) -> str:
        return "test_integration"

    @property
    def version(self) -> str:
        return "1.0.0"

    def custom_method(self) -> str:
        """Custom method for testing."""
        return "custom method"
