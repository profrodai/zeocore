"""
Implementation classes for testing config providers.
"""

from typing import Any

from zeo_core.integrations.core.base import BaseConfigProvider


class MockConfigProvider(BaseConfigProvider):
    """Mock implementation of BaseConfigProvider for testing."""

    @property
    def name(self) -> str:
        return "test_config"

    def validate_config(self, config: dict[str, Any]) -> bool:
        return "test_key" in config

    def get_default_config(self) -> dict[str, Any]:
        return {"test_key": "default_value"}

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        section: dict[str, Any] = config_data.get("test_section", {})
        return section
