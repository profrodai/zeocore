# quack-core/tests/test_integrations/llms/test_config.py
"""
Tests for LLM configuration models.

This module tests the configuration model classes for the LLM integration,
ensuring proper validation and default values.
"""

import pytest
from pydantic import ValidationError

from quackcore.config.models import LoggingConfig
from quackcore.integrations.llms.config import (
    AnthropicConfig,
    LLMConfig,
    OpenAIConfig,
)


class TestLLMConfig:
    """Tests for LLM configuration models."""

    def test_openai_config(self) -> None:
        """Test the OpenAI configuration model."""
        # Test with default values
        config = OpenAIConfig()
        assert config.api_key is None
        assert config.organization is None
        assert config.api_base == "https://api.openai.com/v1"
        assert config.default_model == "gpt-4o"

        # Test with custom values
        config = OpenAIConfig(
            api_key="test-key",
            organization="test-org",
            api_base="https://custom-api.openai.com",
            default_model="gpt-4o-mini",
        )
        assert config.api_key == "test-key"
        assert config.organization == "test-org"
        assert config.api_base == "https://custom-api.openai.com"
        assert config.default_model == "gpt-4o-mini"

    def test_anthropic_config(self) -> None:
        """Test the Anthropic configuration model."""
        # Test with default values
        config = AnthropicConfig()
        assert config.api_key is None
        assert config.api_base == "https://api.anthropic.com"
        assert config.default_model == "claude-3-opus-20240229"

        # Test with custom values
        config = AnthropicConfig(
            api_key="test-key",
            api_base="https://custom-api.anthropic.com",
            default_model="claude-3-sonnet-20240229",
        )
        assert config.api_key == "test-key"
        assert config.api_base == "https://custom-api.anthropic.com"
        assert config.default_model == "claude-3-sonnet-20240229"

    def test_llm_config(self) -> None:
        """Test the main LLM configuration model."""
        # Test with default values
        config = LLMConfig()
        assert isinstance(config.openai, OpenAIConfig)
        assert isinstance(config.anthropic, AnthropicConfig)
        assert config.default_provider == "openai"
        assert config.timeout == 60
        assert config.retry_count == 3
        assert config.initial_retry_delay == 1.0
        assert config.max_retry_delay == 30.0
        assert isinstance(config.logging, LoggingConfig)

        # Test with custom values
        config = LLMConfig(
            openai=OpenAIConfig(api_key="openai-key"),
            anthropic=AnthropicConfig(api_key="anthropic-key"),
            default_provider="anthropic",
            timeout=30,
            retry_count=5,
            initial_retry_delay=0.5,
            max_retry_delay=10.0,
            logging=LoggingConfig(level="DEBUG"),
        )
        assert config.openai.api_key == "openai-key"
        assert config.anthropic.api_key == "anthropic-key"
        assert config.default_provider == "anthropic"
        assert config.timeout == 30
        assert config.retry_count == 5
        assert config.initial_retry_delay == 0.5
        assert config.max_retry_delay == 10.0
        assert config.logging.level == "DEBUG"

        # Test validation - retry_count must be non-negative
        with pytest.raises(ValidationError):
            LLMConfig(retry_count=-1)

        # Test validation - timeout must be positive
        with pytest.raises(ValidationError):
            LLMConfig(timeout=0)

        with pytest.raises(ValidationError):
            LLMConfig(timeout=-1)

    def test_config_from_dict(self) -> None:
        """Test creating config models from dictionaries."""
        # Test OpenAI config from dict
        openai_dict = {
            "api_key": "test-key",
            "organization": "test-org",
            "api_base": "https://custom-api.openai.com",
            "default_model": "gpt-4o-mini",
        }
        config = OpenAIConfig(**openai_dict)
        assert config.api_key == "test-key"
        assert config.organization == "test-org"
        assert config.api_base == "https://custom-api.openai.com"
        assert config.default_model == "gpt-4o-mini"

        # Test Anthropic config from dict
        anthropic_dict = {
            "api_key": "test-key",
            "api_base": "https://custom-api.anthropic.com",
            "default_model": "claude-3-sonnet-20240229",
        }
        config = AnthropicConfig(**anthropic_dict)
        assert config.api_key == "test-key"
        assert config.api_base == "https://custom-api.anthropic.com"
        assert config.default_model == "claude-3-sonnet-20240229"

        # Test main config from dict
        config_dict = {
            "openai": openai_dict,
            "anthropic": anthropic_dict,
            "default_provider": "anthropic",
            "timeout": 30,
            "retry_count": 5,
            "initial_retry_delay": 0.5,
            "max_retry_delay": 10.0,
            "logging": {"level": "DEBUG"},
        }
        config = LLMConfig(**config_dict)
        assert config.openai.api_key == "test-key"
        assert config.anthropic.api_key == "test-key"
        assert config.default_provider == "anthropic"
        assert config.timeout == 30
        assert config.retry_count == 5
        assert config.initial_retry_delay == 0.5
        assert config.max_retry_delay == 10.0
        assert config.logging.level == "DEBUG"

    def test_config_model_dump(self) -> None:
        """Test dumping config models to dictionaries."""
        # Create a config with custom values
        config = LLMConfig(
            openai=OpenAIConfig(api_key="openai-key"),
            anthropic=AnthropicConfig(api_key="anthropic-key"),
            default_provider="anthropic",
            timeout=30,
            retry_count=5,
        )

        # Dump to dict
        config_dict = config.model_dump()

        # Check the structure of the dumped dict
        assert "openai" in config_dict
        assert "anthropic" in config_dict
        assert "default_provider" in config_dict
        assert "timeout" in config_dict
        assert "retry_count" in config_dict

        # Check values
        assert config_dict["default_provider"] == "anthropic"
        assert config_dict["timeout"] == 30
        assert config_dict["retry_count"] == 5
        assert config_dict["openai"]["api_key"] == "openai-key"
        assert config_dict["anthropic"]["api_key"] == "anthropic-key"
