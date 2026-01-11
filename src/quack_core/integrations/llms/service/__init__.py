# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/service/__init__.py
# module: quack_core.integrations.llms.service.__init__
# role: service
# neighbors: dependencies.py, initialization.py, integration.py, operations.py
# exports: LLMIntegration, check_llm_dependencies
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

"""
LLM integration service for quack_core.

This module provides the main service class for LLM integration,
handling configuration, client initialization, and conversation management.
"""

import importlib.util
from collections.abc import Callable, Sequence

from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.clients import LLMClient, MockLLMClient
from quack_core.integrations.llms.config import LLMConfig, LLMConfigProvider
from quack_core.integrations.llms.fallback import FallbackConfig
from quack_core.integrations.llms.models import ChatMessage, LLMOptions
from quack_core.core.errors import QuackIntegrationError
from quack_core.core.logging import LOG_LEVELS, LogLevel


def check_llm_dependencies() -> tuple[bool, str, list[str]]:
    """
    Check if LLM dependencies are available.

    Returns:
        tuple[bool, str, list[str]]: Success status, message, and list of available providers
    """
    available_providers = []

    # Check for OpenAI
    if importlib.util.find_spec("openai") is not None:
        available_providers.append("openai")

    # Check for Anthropic
    if importlib.util.find_spec("anthropic") is not None:
        available_providers.append("anthropic")

    # Check for Ollama (requires requests package)
    if importlib.util.find_spec("requests") is not None:
        # Try to connect to local Ollama server to check availability
        try:
            import requests

            try:
                response = requests.get("http://localhost:11434/api/version", timeout=1)
                if response.status_code == 200:
                    available_providers.append("ollama")
            except requests.exceptions.RequestException:
                # Failed to connect to Ollama server
                pass
        except ImportError:
            # Requests not installed
            pass

    # Always add MockLLM as it has no external dependencies
    available_providers.append("mock")

    if not available_providers or (
        len(available_providers) == 1 and available_providers[0] == "mock"
    ):
        return (
            False,
            "No LLM providers available. Install OpenAI or Anthropic package, or run Ollama locally.",
            available_providers,
        )

    return (
        True,
        f"Available LLM providers: {', '.join(available_providers)}",
        available_providers,
    )


class LLMIntegration(BaseIntegrationService):
    """Integration service for LLMs."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        config_path: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        enable_fallback: bool = True,  # New parameter
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
        config_provider = LLMConfigProvider(log_level)
        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level)

        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.client: LLMClient | None = None
        self._using_mock = False
        self._enable_fallback = enable_fallback
        self._fallback_client = None  # Type hint removed to avoid circular imports

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "LLM"

    def _extract_config(self) -> dict:
        """
        Extract and validate the LLM configuration.

        Returns:
            dict: LLM configuration

        Raises:
            QuackIntegrationError: If configuration is invalid
        """
        if not self.config:
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
            LLMConfig(**self.config)
            return self.config
        except Exception as e:
            raise QuackIntegrationError(f"Invalid LLM configuration: {e}")

    def initialize(self) -> IntegrationResult:
        """
        Initialize the LLM integration.

        This method loads the configuration and initializes the LLM client.

        Returns:
            IntegrationResult: Result of initialization
        """
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
                return self._initialize_single_provider(llm_config, available_providers)

            # Initialize with fallback support
            return self._initialize_with_fallback(
                llm_config, fallback_config, available_providers
            )

        except QuackIntegrationError as e:
            self.logger.error(f"Integration error during initialization: {e}")
            return IntegrationResult.error_result(str(e))
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM integration: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize LLM integration: {e}"
            )

    def _initialize_single_provider(
        self, llm_config: dict, available_providers: list[str]
    ) -> IntegrationResult:
        """
        Initialize with a single provider (original implementation).

        Args:
            llm_config: LLM configuration
            available_providers: List of available providers

        Returns:
            IntegrationResult: Result of initialization
        """
        # Determine provider
        requested_provider = self.provider or llm_config.get(
            "default_provider", "openai"
        )

        # Fall back to an available provider if the requested one is not available
        provider = requested_provider
        if provider not in available_providers:
            # If we have any real providers, use the first one
            for p in ["openai", "anthropic", "ollama"]:
                if p in available_providers:
                    provider = p
                    self.logger.warning(
                        f"Requested provider '{requested_provider}' not available. "
                        f"Using '{provider}' instead."
                    )
                    break
            else:
                # Fall back to mock if no real providers are available
                provider = "mock"
                self._using_mock = True
                self.logger.warning(
                    f"Requested provider '{requested_provider}' not available and no "
                    f"other LLM providers found. Using MockLLMClient instead."
                )

        # Get provider-specific config
        provider_config = llm_config.get(provider, {})

        # Initialize client with appropriate arguments
        client_args = {
            "provider": provider,
            "model": self.model or provider_config.get("default_model"),
            "api_key": self.api_key or provider_config.get("api_key"),
            "timeout": llm_config.get("timeout", 60),
            "retry_count": llm_config.get("retry_count", 3),
            "initial_retry_delay": llm_config.get("initial_retry_delay", 1.0),
            "max_retry_delay": llm_config.get("max_retry_delay", 30.0),
            "log_level": self.log_level,
        }

        # Add provider-specific config
        if provider == "openai":
            client_args["api_base"] = provider_config.get("api_base")
            client_args["organization"] = provider_config.get("organization")
        elif provider == "anthropic":
            client_args["api_base"] = provider_config.get("api_base")
        elif provider == "ollama":
            client_args["api_base"] = provider_config.get("api_base")

        try:
            # Import the registry functions for getting an LLM client
            from quack_core.integrations.llms.registry import get_llm_client

            self.client = get_llm_client(**client_args)
        except QuackIntegrationError as e:
            # If we can't initialize the requested client, fall back to MockLLMClient
            self.logger.warning(f"Failed to initialize {provider} client: {e}")
            self.logger.warning("Falling back to MockLLMClient")

            # Create a mock client with default responses
            self.client = MockLLMClient(log_level=self.log_level)
            self._using_mock = True

        self._initialized = True

        return IntegrationResult.success_result(
            message=(
                f"LLM integration initialized successfully with provider: {provider}"
                f"{' (using mock client)' if self._using_mock else ''}"
            )
        )

    def _initialize_with_fallback(
        self,
        llm_config: dict,
        fallback_config: FallbackConfig,
        available_providers: list[str],
    ) -> IntegrationResult:
        """
        Initialize with fallback support.

        Args:
            llm_config: LLM configuration
            fallback_config: Fallback configuration
            available_providers: List of available providers

        Returns:
            IntegrationResult: Result of initialization
        """
        # Filter fallback_config.providers to only include available providers
        fallback_providers = [
            p for p in fallback_config.providers if p in available_providers
        ]

        # Always include mock as the last resort
        if "mock" not in fallback_providers:
            fallback_providers.append("mock")

        # Update fallback config with filtered providers
        fallback_config.providers = fallback_providers

        # Check if we have any real providers
        self._using_mock = (
            len(fallback_providers) == 1 and fallback_providers[0] == "mock"
        )

        # Prepare model and API key maps
        model_map = {}
        api_key_map = {}
        provider_args = {}

        for provider in fallback_providers:
            provider_config = llm_config.get(provider, {})

            # Set model for this provider
            if provider == self.provider and self.model:
                # If this is the requested provider and a model was specified, use it
                model_map[provider] = self.model
            else:
                # Otherwise, use the default model from the config
                model_map[provider] = provider_config.get("default_model")

            # Set API key for this provider
            if provider == self.provider and self.api_key:
                # If this is the requested provider and an API key was specified, use it
                api_key_map[provider] = self.api_key
            else:
                # Otherwise, use the API key from the config
                api_key_map[provider] = provider_config.get("api_key")

            # Set provider-specific config
            provider_args[provider] = {}

            if provider == "openai":
                provider_args[provider] = {
                    "api_base": provider_config.get("api_base"),
                    "organization": provider_config.get("organization"),
                }
            elif provider in ["anthropic", "ollama"]:
                provider_args[provider] = {
                    "api_base": provider_config.get("api_base"),
                }

        # Common args for all providers
        common_args = {
            "timeout": llm_config.get("timeout", 60),
            "retry_count": llm_config.get("retry_count", 3),
            "initial_retry_delay": llm_config.get("initial_retry_delay", 1.0),
            "max_retry_delay": llm_config.get("max_retry_delay", 30.0),
        }

        # Initialize the fallback client
        try:
            # Import here to avoid circular imports
            from quack_core.integrations.llms.fallback import FallbackLLMClient

            self._fallback_client = FallbackLLMClient(
                fallback_config=fallback_config,
                model_map=model_map,
                api_key_map=api_key_map,
                log_level=self.log_level,
                **common_args,
            )

            # Set provider-specific args
            self._fallback_client._provider_args = provider_args

            # Set the fallback client as the main client
            self.client = self._fallback_client

            self._initialized = True

            return IntegrationResult.success_result(
                message=(
                    f"LLM integration initialized successfully with fallback support. "
                    f"Providers: {', '.join(fallback_providers)}"
                    f"{' (may use mock client as fallback)' if not self._using_mock else ' (using mock client only)'}"
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback LLM client: {e}")

            # Try to fall back to single provider mode
            self.logger.warning("Falling back to single provider mode")
            return self._initialize_single_provider(llm_config, available_providers)

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
        if init_error := self._ensure_initialized():
            return init_error

        if not self.client:
            return IntegrationResult.error_result("LLM client not initialized")

        result = self.client.chat(messages, options, callback)

        # Add a note if we're using the mock client
        if self._using_mock and result.success:
            result.message = f"{result.message or 'Success'} (using mock LLM)"

        return result

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
        if init_error := self._ensure_initialized():
            return init_error

        if not self.client:
            return IntegrationResult.error_result("LLM client not initialized")

        result = self.client.count_tokens(messages)

        # Add a note if we're using the mock client
        if self._using_mock and result.success:
            result.message = f"{result.message or 'Success'} (using mock estimation)"

        return result

    def get_provider_status(self) -> list[dict] | None:
        """
        Get the status of all providers when using fallback.

        Returns:
            list[dict] | None: Status information for all providers or None if not using fallback
        """
        if self._fallback_client is not None:
            return [
                status.model_dump()
                for status in self._fallback_client.get_provider_status()
            ]
        return None

    def reset_provider_status(self) -> bool:
        """
        Reset the status of all providers, forcing re-evaluation.

        Returns:
            bool: True if successful, False if not using fallback
        """
        if self._fallback_client is not None:
            self._fallback_client.reset_provider_status()
            return True
        return False

    def get_client(self) -> LLMClient:
        """
        Get the LLM client instance.

        Returns:
            LLMClient: LLM client instance

        Raises:
            QuackIntegrationError: If the client is not initialized
        """
        if not self._initialized or not self.client:
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
