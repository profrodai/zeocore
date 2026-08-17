"""
Fallback mechanism for LLM clients.

This module provides a fallback mechanism for LLM clients, allowing graceful
degradation when primary providers are unavailable or fail.
"""

import time
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel, Field
from quack_core.core.errors import QuackApiError, QuackIntegrationError
from quack_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.clients.base import LLMClient
from quack_core.integrations.llms.models import ChatMessage, LLMOptions


class FallbackConfig(BaseModel):
    """Configuration for fallback behavior between LLM providers."""

    providers: list[str] = Field(
        default_factory=lambda: ["openai", "anthropic", "mock"],
        description="Ordered list of providers to try",
    )
    max_attempts_per_provider: int = Field(
        3, description="Maximum number of attempts per provider before falling back"
    )
    delay_between_providers: float = Field(
        1.0, description="Delay in seconds before trying the next provider"
    )
    fail_fast_on_auth_errors: bool = Field(
        True,
        description=(
            "Immediately try next provider on authentication errors without retrying"
        ),
    )
    stop_on_successful_provider: bool = Field(
        True,
        description=(
            "Whether to remember and use only the last successful provider "
            "for subsequent calls"
        ),
    )


class ProviderStatus(BaseModel):
    """Status information for a specific LLM provider."""

    provider: str = Field(..., description="Provider name")
    available: bool = Field(True, description="Whether the provider is available")
    last_error: str | None = Field(None, description="Last error message")
    last_attempt_time: float | None = Field(
        None, description="Timestamp of last attempt"
    )
    success_count: int = Field(0, description="Number of successful calls")
    fail_count: int = Field(0, description="Number of failed calls")


class FallbackLLMClient(LLMClient):
    """
    LLM client with fallback capabilities.

    This client tries multiple LLM providers in sequence, falling back to the next
    provider if the current one fails.
    """

    def __init__(
        self,
        fallback_config: FallbackConfig | None = None,
        model_map: dict[str, str] | None = None,
        api_key_map: Mapping[str, str | None] | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        **kwargs: Any,  # noqa: ANN401 -- provider-specific kwargs forwarded to each underlying provider client's constructor
    ) -> None:
        """
        Initialize the fallback LLM client.

        Args:
            fallback_config: Configuration for fallback behavior
            model_map: Mapping from provider to model name
            api_key_map: Mapping from provider to API key
            log_level: Logging level
            **kwargs: Additional arguments passed to all underlying clients
        """
        # Initialize with a placeholder model name - it will be overridden
        super().__init__(
            model="fallback-client",
            api_key=None,  # No API key for the parent, we'll use provider-specific keys
            log_level=log_level,
            **kwargs,
        )

        self.logger = get_logger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.logger.setLevel(log_level)

        # Use default config if none is provided
        self._fallback_config = fallback_config or FallbackConfig()

        # Initialize provider-specific parameters
        self._model_map = model_map or {}
        self._api_key_map = api_key_map or {}
        self._common_kwargs = kwargs
        self._provider_args: dict[str, dict[str, str | None]] = {}

        # Initialize client cache and provider status tracking
        self._client_cache: dict[str, LLMClient] = {}
        self._provider_status: dict[str, ProviderStatus] = {
            provider: ProviderStatus(provider=provider)
            for provider in self._fallback_config.providers
        }

        # Track the last successful provider
        self._last_successful_provider: str | None = None

        providers_str = ", ".join(self._fallback_config.providers)
        self.logger.info(
            f"Initialized fallback LLM client with providers: {providers_str}"
        )

    @property
    def log_level(self) -> int:
        """
        Get the current logging level.

        Returns:
            int: Current logging level
        """
        return self.logger.level  # Access the logger's level directly

    @property
    def model(self) -> str:
        """
        Get the effective model name based on the current active provider.

        Returns:
            str: Current model name
        """
        # If we have a successful provider, return its model
        if (
            self._last_successful_provider
            and self._fallback_config.stop_on_successful_provider
        ):
            provider = self._last_successful_provider
            client = self._get_client_for_provider(provider)
            return client.model

        # Otherwise, return the model name for the first provider
        provider = self._fallback_config.providers[0]
        return self._model_map.get(provider, f"{provider}-default-model")

    def get_provider_status(self) -> list[ProviderStatus]:
        """
        Get the status of all providers.

        Returns:
            list[ProviderStatus]: Status information for all providers
        """
        return list(self._provider_status.values())

    def reset_provider_status(self) -> None:
        """Reset the status of all providers, forcing re-evaluation."""
        self._provider_status = {
            provider: ProviderStatus(provider=provider)
            for provider in self._fallback_config.providers
        }
        self._last_successful_provider = None
        self.logger.info("Reset provider status and cleared successful provider cache")

    def _get_client_for_provider(self, provider: str) -> LLMClient:
        """
        Get or create a client for the specified provider.

        Args:
            provider: Provider name

        Returns:
            LLMClient: Client instance for the provider

        Raises:
            QuackIntegrationError: If the client cannot be initialized
        """
        # Return cached client if available
        if provider in self._client_cache:
            return self._client_cache[provider]

        try:
            # Import registry function inside method to avoid circular imports
            from quack_core.integrations.llms.registry import get_llm_client

            # Initialize client arguments
            client_args: dict[str, Any] = {
                "model": self._model_map.get(provider),
                "api_key": self._api_key_map.get(provider),
                "log_level": self.logger.level,  # Use the logger's level directly
            }

            # Add common arguments
            client_args.update(self._common_kwargs)

            # Add provider-specific arguments
            if provider in self._provider_args:
                client_args.update(self._provider_args[provider])

            # Create client
            client = get_llm_client(provider=provider, **client_args)

            # Cache client
            self._client_cache[provider] = client

            return client
        except Exception as e:
            # Update provider status
            status = self._provider_status[provider]
            status.available = False
            status.last_error = str(e)
            status.last_attempt_time = time.time()
            status.fail_count += 1

            raise QuackIntegrationError(
                f"Failed to initialize {provider} client: {e}",
                context={"provider": provider},
                original_error=e,
            ) from e

    def _is_auth_error(self, error: Exception) -> bool:
        """
        Check if an error is related to authentication.

        Args:
            error: The error to check

        Returns:
            bool: True if it's an authentication error
        """
        error_str = str(error).lower()
        return any(
            term in error_str
            for term in [
                "api key",
                "authentication",
                "auth",
                "credential",
                "permission",
                "unauthorized",
                "invalid key",
            ]
        )

    def _resolve_providers_to_try(self) -> list[str]:
        """
        Determine the provider order to attempt, preferring the last success.

        Returns:
            list[str]: Providers in the order they should be tried.
        """
        # If we have a successful provider and config says to use it, try it first
        if (
            self._last_successful_provider
            and self._fallback_config.stop_on_successful_provider
        ):
            return [
                self._last_successful_provider,
                *[
                    p
                    for p in self._fallback_config.providers
                    if p != self._last_successful_provider
                ],
            ]
        return self._fallback_config.providers

    def _try_chat_attempt(
        self,
        provider: str,
        provider_status: ProviderStatus,
        client: LLMClient,
        messages: list[ChatMessage],
        options: LLMOptions,
        callback: Callable[[str], None] | None,
        attempt: int,
        max_attempts: int,
    ) -> tuple[IntegrationResult[str] | None, Exception | None, bool]:
        """
        Perform a single chat attempt against a provider.

        Args:
            provider: Provider name being attempted.
            provider_status: Mutable status record for the provider.
            client: LLM client for the provider.
            messages: List of messages for the conversation.
            options: Options for the completion request, may be replaced
                with a copy carrying a provider-specific model.
            callback: Optional streaming callback.
            attempt: Current attempt number, 1-indexed.
            max_attempts: Maximum attempts configured for this provider.

        Returns:
            Tuple of (result, error, stop_retrying). If result is not None,
            the request succeeded and the caller should return it
            immediately. Otherwise error holds the last error to record and
            stop_retrying indicates whether the caller should break out of
            the attempt loop (True) or continue to the next attempt
            (False).
        """
        try:
            # Start the request
            self.logger.debug(
                f"Sending request to {provider} (attempt {attempt}/{max_attempts})"
            )

            # Set the model in options if not already set
            if options.model is None:
                provider_model = self._model_map.get(provider)
                if provider_model:
                    # Create a copy to avoid modifying the original
                    options = LLMOptions(**options.model_dump())
                    options.model = provider_model

            # Send the request
            start_time = time.time()
            result = client.chat(messages, options, callback)
            elapsed_time = time.time() - start_time

            # If successful, update status and return
            if result.success:
                self.logger.info(
                    f"Request to {provider} succeeded in {elapsed_time:.2f}s"
                )
                provider_status.success_count += 1
                provider_status.last_attempt_time = time.time()
                self._last_successful_provider = provider

                # Add provider info to result
                if result.message:
                    result.message = f"{result.message} (via {provider})"
                else:
                    result.message = f"Success (via {provider})"

                return result, None, True

            return None, None, False

        except QuackApiError as e:
            # Handle API errors
            error_time = time.time()
            provider_status.last_attempt_time = error_time
            provider_status.last_error = str(e)
            provider_status.fail_count += 1

            # Check if it's an auth error and we should fail fast
            if self._fallback_config.fail_fast_on_auth_errors and self._is_auth_error(
                e
            ):
                self.logger.warning(
                    f"Authentication error with {provider}, "
                    f"skipping remaining attempts: {e}"
                )
                return None, e, True

            # If it's the last attempt for this provider, log and
            # continue to next
            if attempt == max_attempts:
                self.logger.warning(f"All attempts failed for provider {provider}: {e}")
                return None, e, True

            # Otherwise retry
            retry_delay = min(2 ** (attempt - 1), 30)  # Exponential backoff
            self.logger.warning(
                f"Attempt {attempt}/{max_attempts} failed for {provider}, "
                f"retrying in {retry_delay}s: {e}"
            )
            time.sleep(retry_delay)
            return None, None, False

        except Exception as e:
            # Handle other exceptions
            provider_status.last_attempt_time = time.time()
            provider_status.last_error = str(e)
            provider_status.fail_count += 1

            self.logger.error(f"Unexpected error with provider {provider}: {e}")
            return None, e, True  # Don't retry on unexpected errors

    def _chat_with_provider(
        self,
        messages: list[ChatMessage],
        options: LLMOptions,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        """
        Send a chat completion request with fallback support.

        This method tries multiple providers in sequence according to the fallback
        configuration, with appropriate retries and delays.

        Args:
            messages: List of messages for the conversation
            options: Additional options for the completion request
            callback: Optional callback function for streaming responses

        Returns:
            IntegrationResult[str]: Result of the chat completion request
        """
        providers_to_try = self._resolve_providers_to_try()

        last_error: Exception | None = None

        # Try each provider in sequence
        for provider_idx, provider in enumerate(providers_to_try):
            # Check if provider is marked as unavailable
            provider_status = self._provider_status[provider]
            if not provider_status.available:
                self.logger.info(
                    f"Skipping provider {provider} "
                    f"(marked unavailable: {provider_status.last_error})"
                )
                continue

            # Add delay before trying next provider (except for the first one)
            if provider_idx > 0 and self._fallback_config.delay_between_providers > 0:
                time.sleep(self._fallback_config.delay_between_providers)

            # Try to get client for this provider
            try:
                client = self._get_client_for_provider(provider)
                self.logger.info(
                    f"Trying provider: {provider} with model: {client.model}"
                )
            except QuackIntegrationError as e:
                self.logger.warning(f"Could not initialize provider {provider}: {e}")
                last_error = e
                continue

            # Try the provider with appropriate retry logic
            max_attempts = self._fallback_config.max_attempts_per_provider

            for attempt in range(1, max_attempts + 1):
                result, error, stop_retrying = self._try_chat_attempt(
                    provider,
                    provider_status,
                    client,
                    messages,
                    options,
                    callback,
                    attempt,
                    max_attempts,
                )
                if result is not None:
                    return result
                if error is not None:
                    last_error = error
                if stop_retrying:
                    break

        # If we get here, all providers failed
        error_message = f"All LLM providers failed. Last error: {last_error}"
        self.logger.error(error_message)
        return IntegrationResult.error_result(error_message)

    def _count_tokens_with_provider(
        self, messages: list[ChatMessage]
    ) -> IntegrationResult[int]:
        """
        Count tokens with fallback support.

        This method tries multiple providers for token counting, similar to chat.

        Args:
            messages: List of messages to count tokens for

        Returns:
            IntegrationResult[int]: Result containing the token count
        """
        # Similar fallback logic as _chat_with_provider, but for token counting
        providers_to_try = self._resolve_providers_to_try()

        last_error: str | Exception | None = None

        for provider_idx, provider in enumerate(providers_to_try):
            # Check if provider is marked as unavailable
            provider_status = self._provider_status[provider]
            if not provider_status.available:
                continue

            # Add delay before trying next provider (except for the first one)
            if provider_idx > 0 and self._fallback_config.delay_between_providers > 0:
                time.sleep(self._fallback_config.delay_between_providers)

            # Try to get client for this provider
            try:
                client = self._get_client_for_provider(provider)
                self.logger.debug(f"Trying to count tokens with provider: {provider}")
            except QuackIntegrationError as e:
                last_error = e
                continue

            # Try token counting
            try:
                result = client.count_tokens(messages)

                if result.success:
                    # Update provider status
                    provider_status.success_count += 1
                    provider_status.last_attempt_time = time.time()

                    # Add provider info to result
                    if result.message:
                        result.message = f"{result.message} (via {provider})"
                    else:
                        result.message = f"Success (via {provider})"

                    return result

                # If unsuccessful, try next provider
                last_error = result.error or Exception("Unknown token counting error")

            except Exception as e:
                # Update provider status
                provider_status.last_attempt_time = time.time()
                provider_status.last_error = str(e)
                provider_status.fail_count += 1

                last_error = e

        # If we get here, all providers failed
        error_message = (
            f"All providers failed to count tokens. Last error: {last_error}"
        )
        self.logger.error(error_message)
        return IntegrationResult.error_result(error_message)
