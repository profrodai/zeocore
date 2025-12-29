# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/base/integration_service_impl.py
# role: tests
# neighbors: __init__.py, auth_provider_impl.py, config_provider_impl.py, test_auth_provider.py, test_base.py, test_config_provider.py (+3 more)
# exports: MockIntegrationService
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===

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
