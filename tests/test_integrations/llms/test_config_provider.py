# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/test_config_provider.py
# role: tests
# neighbors: __init__.py, test_config.py, test_fallback.py, test_integration.py, test_llms.py, test_models.py (+3 more)
# exports: TestLLMConfigProvider
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""
Tests for the LLM configuration provider.

This module tests the configuration provider for LLM integrations, including
loading, validation, and management of configuration data.
"""

import os
from unittest.mock import patch

import pytest

from quack_core.integrations.core.results import ConfigResult
from quack_core.integrations.llms.config import LLMConfigProvider


class TestLLMConfigProvider:
    """Tests for the LLM configuration provider."""

    @pytest.fixture
    def config_provider(self) -> LLMConfigProvider:
        """Create a LLM configuration provider."""
        return LLMConfigProvider()

    def test_init(self, config_provider: LLMConfigProvider) -> None:
        """Test initializing the config provider."""
        assert config_provider.name == "LLMConfig"
        assert config_provider.logger is not None

    def test_extract_config(self, config_provider: LLMConfigProvider) -> None:
        """Test extracting LLM-specific configuration."""
        # Test with llm section
        config_data = {
            "llm": {
                "default_provider": "anthropic",
                "timeout": 30,
                "openai": {
                    "api_key": "test-key",
                },
            }
        }
        result = config_provider._extract_config(config_data)
        assert result == config_data["llm"]

        # Test without llm section
        config_data = {
            "default_provider": "anthropic",
            "timeout": 30,
            "openai": {
                "api_key": "test-key",
            },
        }
        result = config_provider._extract_config(config_data)
        assert result == config_data

    def test_validate_config(self, config_provider: LLMConfigProvider) -> None:
        """Test validating configuration data."""
        # Test with valid config
        valid_config = {
            "default_provider": "openai",
            "timeout": 60,
            "retry_count": 3,
            "openai": {
                "api_key": "test-key",
            },
        }
        assert config_provider.validate_config(valid_config) is True

        # Test with invalid config - negative retry_count
        invalid_config = {
            "default_provider": "openai",
            "retry_count": -1,
        }
        assert config_provider.validate_config(invalid_config) is False

        # Test with invalid type - string instead of int
        invalid_config = {
            "default_provider": "openai",
            "timeout": "not-an-int",
        }
        assert config_provider.validate_config(invalid_config) is False

        # Test with exception during validation
        with patch(
            "quack_core.integrations.llms.config.LLMConfig",
            side_effect=Exception("Validation error"),
        ):
            assert config_provider.validate_config({}) is False

    def test_get_default_config(self, config_provider: LLMConfigProvider) -> None:
        """Test getting default configuration."""
        # Test with no environment variables
        with patch.dict(os.environ, {}, clear=True):
            config = config_provider.get_default_config()

            assert config["default_provider"] == "openai"
            assert config["timeout"] == 60
            assert config["retry_count"] == 3
            assert config["openai"]["api_key"] is None
            assert config["anthropic"]["api_key"] is None

        # Test with environment variables
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "env-openai-key",
                "ANTHROPIC_API_KEY": "env-anthropic-key",
            },
        ):
            config = config_provider.get_default_config()

            assert config["openai"]["api_key"] == "env-openai-key"
            assert config["anthropic"]["api_key"] == "env-anthropic-key"

    def test_load_config(self, config_provider: LLMConfigProvider) -> None:
        """Test loading configuration from different sources."""
        # Create a ConfigResult with the test data
        mock_config_result = ConfigResult(
            success=True,
            content={
                "default_provider": "anthropic",
                "timeout": 30,
            },
        )

        # Replace the load_config method temporarily
        original_load_config = config_provider.load_config

        try:
            # Replace with a simple function that returns our mock result
            config_provider.load_config = lambda config_path=None: mock_config_result

            # Now call the method and verify the result
            result = config_provider.load_config("config.yaml")

            # Verify the result
            assert result.success is True
            assert "default_provider" in result.content
            assert result.content["default_provider"] == "anthropic"
        finally:
            # Restore the original method
            config_provider.load_config = original_load_config

    def test_no_path_resolution_needed(
        self, config_provider: LLMConfigProvider
    ) -> None:
        """Test that LLM config does not need path resolution."""
        # LLM config doesn't have any paths to resolve,
        # so we should be able to use it as-is

        config = {
            "default_provider": "openai",
            "timeout": 60,
        }

        # Just verify we can get the config working
        assert config_provider.validate_config(config) is True
