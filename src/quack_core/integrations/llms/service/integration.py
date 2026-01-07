# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/service/integration.py
# module: quack_core.integrations.llms.service.integration
# role: service
# neighbors: __init__.py, operations.py, dependencies.py, initialization.py
# exports: LLMIntegration
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Core LLM integration class.

This module provides the main LLMIntegration class which serves as the entry point
for using different LLM providers.
"""
from collections.abc import Callable, Sequence

from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms import ChatMessage, LLMOptions
from quack_core.integrations.llms.clients import LLMClient
from quack_core.integrations.llms.config import LLMConfigProvider
from quack_core.integrations.llms.fallback import FallbackConfig
from quack_core.integrations.llms.service.dependencies import check_llm_dependencies
from quack_core.core.errors import QuackIntegrationError
from quack_core.core.logging import LOG_LEVELS, LogLevel


class LLMIntegration(BaseIntegrationService):
    """Integration service for LLMs."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        config_path: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        enable_fallback: bool = True,
    ) -> None:
        """
        Initialize the LLM integration service.

        Args:
            provider: LLM provider name
            model: Model name to use
            api_key: API key for authentication
            config_path: Path to configuration file
            log_level: Logging level
            enable_fallback: Whether to enable fallback between providers
        """
        # Retain the provided log level explicitly
        self.log_level = log_level

        # Initialize configuration provider and base service
        config_provider = LLMConfigProvider(log_level)
        super().__init__(config_provider, None, config_path, str(log_level))

        # Retain provided log level
        self.log_level = log_level

        # User-specified settings
        self.provider = provider
        self.model = model
        self.api_key = api_key

        # Internal state
        self.client: LLMClient | None = None
        self._using_mock = False
        self._enable_fallback = enable_fallback
        self._fallback_client = None  # Type hint removed to avoid circular imports

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "LLM"

    # src/quack-core/integrations/llms/service/integration.py (update for _extract_config method)
    def _extract_config(self) -> dict:
        """
        Extract and validate the LLM configuration.

        Returns:
            dict: LLM configuration

        Raises:
            QuackIntegrationError: If configuration is invalid
        """
        if not getattr(self, 'config', None):
            # Get default configuration
            if not self.config_provider:
                raise QuackIntegrationError("Configuration provider not initialized")

            try:
                config_result = self.config_provider.load_config(self.config_path)

                # Handle both ConfigResult and DataResult
                if config_result.success:
                    if hasattr(config_result, "content") and config_result.content:
                        self.config = config_result.content
                    elif hasattr(config_result, "data") and config_result.data:
                        self.config = config_result.data
                    else:
                        self.config = self.config_provider.get_default_config()
                else:
                    self.config = self.config_provider.get_default_config()

            except Exception as e:
                # If loading fails, use default config
                self.logger.warning(f"Failed to load config, using defaults: {e}")
                self.config = self.config_provider.get_default_config()

        # Validate configuration
        try:
            from quack_core.integrations.llms.config import LLMConfig

            LLMConfig(**self.config)
            return self.config
        except Exception as e:
            # Make sure we explicitly raise QuackIntegrationError for validation errors
            raise QuackIntegrationError(f"Invalid LLM configuration: {e}")

    def initialize(self) -> IntegrationResult:
        """
        Initialize the LLM integration.

        This method loads the configuration and initializes the LLM client.

        Returns:
            IntegrationResult: Result of initialization
        """
        from quack_core.integrations.llms.service.initialization import (
            initialize_single_provider,
            initialize_with_fallback,
        )

        try:
            init_result = super().initialize()
            if not init_result.success:
                return init_result

            # Check available LLM providers
            deps_available, deps_message, available_providers = check_llm_dependencies()
            self.logger.info(deps_message)

            # Extract and validate config
            llm_config = self._extract_config()

            # Get fallback configuration if available
            fallback_config = None
            if "fallback" in llm_config:
                try:
                    fallback_config = FallbackConfig(**llm_config["fallback"])
                    self.logger.info(
                        f"Loaded fallback configuration with providers: {fallback_config.providers}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Invalid fallback configuration, using defaults: {e}"
                    )

            # If fallback is disabled or not configured, use standard initialization
            if not self._enable_fallback or fallback_config is None:
                return initialize_single_provider(self, llm_config, available_providers)

            # Initialize with fallback support
            return initialize_with_fallback(
                self, llm_config, fallback_config, available_providers
            )

        except QuackIntegrationError as e:
            self.logger.error(f"Integration error during initialization: {e}")
            return IntegrationResult(success=False, error=str(e))
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM integration: {e}")
            return IntegrationResult(
                success=False, error=f"Failed to initialize LLM integration: {e}"
            )

    def get_client(self) -> LLMClient:
        """
        Get the LLM client instance.

        Returns:
            LLMClient: LLM client instance

        Raises:
            QuackIntegrationError: If the client is not initialized
        """
        if not getattr(self, '_initialized', False) or not self.client:
            raise QuackIntegrationError("LLM client not initialized")

        return self.client

    @property
    def is_using_mock(self) -> bool:
        """
        Check if the service is using a mock client.

        Returns:
            bool: True if using a mock client, False otherwise
        """
        return self._using_mock

    def chat(
        self,
        messages: Sequence[ChatMessage] | Sequence[dict],
        options: LLMOptions | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        """
        Send a chat completion request to the LLM.

        Args:
            messages: Sequence of messages for the conversation
            options: Additional options for the completion request
            callback: Optional callback function for streaming responses

        Returns:
            IntegrationResult[str]: Result of the chat completion request
        """
        from quack_core.integrations.llms.service.operations import chat

        return chat(self, messages, options, callback)

    def count_tokens(
        self, messages: Sequence[ChatMessage] | Sequence[dict]
    ) -> IntegrationResult[int]:
        """
        Count the number of tokens in the messages.

        Args:
            messages: Sequence of messages to count tokens for

        Returns:
            IntegrationResult[int]: Result containing the token count
        """
        from quack_core.integrations.llms.service.operations import count_tokens

        return count_tokens(self, messages)

    def get_provider_status(self) -> list[dict] | None:
        """
        Get the status of all providers when using fallback.

        Returns:
            list[dict] | None: Status information for all providers or None if not using fallback
        """
        from quack_core.integrations.llms.service.operations import get_provider_status

        return get_provider_status(self)

    def reset_provider_status(self) -> bool:
        """
        Reset the status of all providers, forcing re-evaluation.

        Returns:
            bool: True if successful, False if not using fallback
        """
        from quack_core.integrations.llms.service.operations import (
            reset_provider_status,
        )

        return reset_provider_status(self)
