# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/base/config_provider_impl.py
# role: tests
# neighbors: __init__.py, auth_provider_impl.py, integration_service_impl.py, test_auth_provider.py, test_base.py, test_config_provider.py (+3 more)
# exports: MockConfigProvider
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Implementation classes for testing config providers.
"""

from quack_core.integrations.core.base import BaseConfigProvider


class MockConfigProvider(BaseConfigProvider):
    """Mock implementation of BaseConfigProvider for testing."""

    @property
    def name(self) -> str:
        return "test_config"

    def validate_config(self, config: dict) -> bool:
        return "test_key" in config

    def get_default_config(self) -> dict:
        return {"test_key": "default_value"}

    def _extract_config(self, config_data: dict) -> dict:
        return config_data.get("test_section", {})
