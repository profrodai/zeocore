# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/config.py
# module: quack_core.integrations.llms.config
# role: module
# neighbors: __init__.py, models.py, protocols.py, registry.py, fallback.py
# exports: OpenAIConfig, AnthropicConfig, OllamaConfig, LLMConfig, LLMConfigProvider
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
Configuration for LLM integration.

This module provides configuration models and a provider for LLM integration,
handling API keys, default models, and other settings.
"""

import logging
import os
from typing import Any

from pydantic import BaseModel, Field, field_validator
from quack_core.config.models import LoggingConfig
from quack_core.integrations.core import ConfigResult
from quack_core.integrations.core.base import BaseConfigProvider
from quack_core.integrations.llms.fallback import FallbackConfig


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI API."""

    api_key: str | None = Field(
        None, description="OpenAI API key (or set OPENAI_API_KEY environment variable)"
    )
    organization: str | None = Field(
        None,
        description="OpenAI organization ID (or set OPENAI_ORG_ID environment variable)",
    )
    api_base: str | None = Field(
        "https://api.openai.com/v1", description="OpenAI API base URL"
    )
    default_model: str = Field("gpt-4o", description="Default model to use")


class AnthropicConfig(BaseModel):
    """Configuration for Anthropic API."""

    api_key: str | None = Field(
        None,
        description="Anthropic API key (or set ANTHROPIC_API_KEY environment variable)",
    )
    api_base: str | None = Field(
        "https://api.anthropic.com", description="Anthropic API base URL"
    )
    default_model: str = Field(
        "claude-3-opus-20240229", description="Default model to use"
    )


class OllamaConfig(BaseModel):
    """Configuration for Ollama API."""

    api_base: str = Field("http://localhost:11434", description="Ollama API base URL")
    default_model: str = Field("llama3", description="Default model to use")


class LLMConfig(BaseModel):
    """Main configuration for LLM integration."""

    openai: OpenAIConfig = Field(
        default_factory=OpenAIConfig, description="OpenAI configuration"
    )
    anthropic: AnthropicConfig = Field(
        default_factory=AnthropicConfig, description="Anthropic configuration"
    )
    ollama: OllamaConfig = Field(
        default_factory=OllamaConfig, description="Ollama configuration"
    )
    default_provider: str = Field("openai", description="Default LLM provider to use")
    fallback: FallbackConfig | None = Field(
        None, description="Configuration for fallback behavior"
    )
    enable_fallback: bool = Field(
        True, description="Whether to enable fallback between providers"
    )
    timeout: int = Field(60, description="Request timeout in seconds")
    retry_count: int = Field(3, description="Number of retries for failed requests")
    initial_retry_delay: float = Field(
        1.0, description="Initial delay for exponential backoff"
    )
    max_retry_delay: float = Field(30.0, description="Maximum delay between retries")
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )

    @field_validator("retry_count")
    @classmethod
    def validate_retry_count(cls, v: int) -> int:
        """Validate retry_count to be non-negative."""
        if v < 0:
            raise ValueError("retry_count must be non-negative")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout to be positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v


class LLMConfigProvider(BaseConfigProvider):
    """Configuration provider for LLM integration."""

    # Class variables with proper typing
    DEFAULT_CONFIG_LOCATIONS = [
        "./config/llm_config.yaml",
        "./config/quack_config.yaml",
        "./quack_config.yaml",
        "~/.quack/llm_config.yaml",
    ]
    ENV_PREFIX = "QUACK_LLM_"

    def __init__(self, log_level: int = logging.INFO) -> None:
        """
        Initialize the LLM configuration provider.

        Args:
            log_level: Logging level
        """
        super().__init__(log_level)

    @property
    def name(self) -> str:
        """Get the name of the configuration provider."""
        return "LLMConfig"

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract LLM-specific configuration from the full config data.

        Args:
            config_data: Full configuration data

        Returns:
            dict[str, Any]: LLM-specific configuration
        """
        # Look for llm section in integrations section first
        if "integrations" in config_data and isinstance(
            config_data["integrations"], dict
        ):
            if "llm" in config_data["integrations"]:
                return config_data["integrations"]["llm"]

        # Then look for llm section directly
        if "llm" in config_data:
            return config_data["llm"]

        # Otherwise, return the original data for further processing
        return config_data

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration data against the LLM configuration schema.

        Args:
            config: Configuration data to validate

        Returns:
            bool: True if configuration is valid
        """
        try:
            LLMConfig(**config)
            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration values for LLM integration.

        Returns:
            dict[str, Any]: Default configuration values
        """
        default_config = LLMConfig().model_dump()

        # Check for environment variables for API keys
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            default_config["openai"]["api_key"] = openai_api_key

        openai_org_id = os.environ.get("OPENAI_ORG_ID")
        if openai_org_id:
            default_config["openai"]["organization"] = openai_org_id

        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            default_config["anthropic"]["api_key"] = anthropic_api_key

        return default_config

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        """
        Load configuration from a file.

        Args:
            config_path: Path to configuration file.

        Returns:
            ConfigResult: Result containing configuration data.
        """
        # Use the base implementation to load raw config
        result = super().load_config(config_path)

        if result.success and result.content:
            # Extract LLM-specific config
            llm_config = self._extract_config(result.content)

            # Set up environment variables from config
            self._setup_environment_variables(llm_config)

            return ConfigResult(
                success=True, content=llm_config, config_path=result.config_path
            )

        return result

    def _setup_environment_variables(self, config: dict[str, Any]) -> None:
        """
        Set up environment variables from configuration.

        This ensures that API keys from the configuration are available
        to the LLM providers' SDKs via environment variables.

        Args:
            config: LLM configuration dictionary
        """
        try:
            # Set OpenAI API key in environment if provided and not already set
            if "openai" in config and isinstance(config["openai"], dict):
                openai_config = config["openai"]

                if "api_key" in openai_config and openai_config["api_key"]:
                    api_key = openai_config["api_key"]
                    if not os.environ.get("OPENAI_API_KEY"):
                        os.environ["OPENAI_API_KEY"] = api_key
                        self.logger.debug(
                            "Set OPENAI_API_KEY in environment from config"
                        )

                if "organization" in openai_config and openai_config["organization"]:
                    org_id = openai_config["organization"]
                    if not os.environ.get("OPENAI_ORGANIZATION"):
                        os.environ["OPENAI_ORGANIZATION"] = org_id
                        self.logger.debug(
                            "Set OPENAI_ORGANIZATION in environment from config"
                        )

            # Set Anthropic API key in environment if provided and not already set
            if "anthropic" in config and isinstance(config["anthropic"], dict):
                anthropic_config = config["anthropic"]

                if "api_key" in anthropic_config and anthropic_config["api_key"]:
                    api_key = anthropic_config["api_key"]
                    if not os.environ.get("ANTHROPIC_API_KEY"):
                        os.environ["ANTHROPIC_API_KEY"] = api_key
                        self.logger.debug(
                            "Set ANTHROPIC_API_KEY in environment from config"
                        )

        except Exception as e:
            self.logger.warning(f"Error setting up environment variables: {e}")
            # Non-fatal error - continue without environment variables
