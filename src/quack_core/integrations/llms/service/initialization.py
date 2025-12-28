# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/service/initialization.py
# module: quack_core.integrations.llms.service.initialization
# role: service
# neighbors: __init__.py, operations.py, dependencies.py, integration.py
# exports: initialize_single_provider, initialize_with_fallback
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Provider initialization logic for LLM integration.

This module provides functions for initializing single providers and fallback configurations.
"""

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.fallback import FallbackConfig


def initialize_single_provider(
    self, llm_config: dict, available_providers: list[str]
) -> IntegrationResult:
    """
    Initialize with a single provider.

    Args:
        self: LLMIntegration instance
        llm_config: LLM configuration
        available_providers: List of available providers

    Returns:
        IntegrationResult: Result of initialization
    """
    # Determine provider
    requested_provider = self.provider or llm_config.get("default_provider", "openai")

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
    except Exception as e:
        # If we can't initialize the requested client, fall back to MockLLMClient
        self.logger.warning(f"Failed to initialize {provider} client: {e}")
        self.logger.warning("Falling back to MockLLMClient")

        # Create a mock client with default responses
        from quack_core.integrations.llms.clients.mock import MockLLMClient

        self.client = MockLLMClient(log_level=self.log_level)
        self._using_mock = True

    self._initialized = True

    return IntegrationResult(
        success=True,
        message=f"LLM integration initialized successfully with provider: {provider}"
        f"{' (using mock client)' if self._using_mock else ''}",
    )


def initialize_with_fallback(
    self,
    llm_config: dict,
    fallback_config: FallbackConfig,
    available_providers: list[str],
) -> IntegrationResult:
    """
    Initialize with fallback support.

    Args:
        self: LLMIntegration instance
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
    self._using_mock = len(fallback_providers) == 1 and fallback_providers[0] == "mock"

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

        return IntegrationResult(
            success=True,
            message=(
                f"LLM integration initialized successfully with fallback support. "
                f"Providers: {', '.join(fallback_providers)}"
                f"{' (may use mock client as fallback)' if not self._using_mock else ' (using mock client only)'}"
            ),
        )
    except Exception as e:
        self.logger.error(f"Failed to initialize fallback LLM client: {e}")

        # Try to fall back to single provider mode
        self.logger.warning("Falling back to single provider mode")
        return initialize_single_provider(self, llm_config, available_providers)
