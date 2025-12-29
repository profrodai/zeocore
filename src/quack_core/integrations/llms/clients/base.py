# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/clients/base.py
# module: quack_core.integrations.llms.clients.base
# role: module
# neighbors: __init__.py, anthropic.py, mock.py, ollama.py, openai.py
# exports: LLMClient
# git_branch: refactor/toolkitWorkflow
# git_commit: 7e3e554
# === QV-LLM:END ===

"""
Base LLM client implementation.

This module provides the abstract base class for all LLM clients with common
functionality for handling requests, retries, and error handling.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.models import ChatMessage, LLMOptions
from quack_core.integrations.llms.protocols import LLMProviderProtocol
from quack_core.lib.errors import QuackApiError, QuackIntegrationError


class LLMClient(ABC, LLMProviderProtocol):
    """Base class for LLM clients."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
        retry_count: int = 3,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 30.0,
        log_level: int = logging.INFO,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the LLM client.

        Args:
            model: Model name to use
            api_key: API key for authentication
            timeout: Request timeout in seconds
            retry_count: Number of retries for failed requests
            initial_retry_delay: Initial delay for exponential backoff
            max_retry_delay: Maximum delay between retries
            log_level: Logging level
            **kwargs: Additional provider-specific arguments
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(log_level)

        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        self._retry_count = retry_count
        self._initial_retry_delay = initial_retry_delay
        self._max_retry_delay = max_retry_delay
        self._kwargs = kwargs

    @property
    def model(self) -> str:
        """
        Get the model name.

        Returns:
            str: The model name to use for requests

        Raises:
            ValueError: If model name is not specified
        """
        if not self._model:
            raise ValueError("Model name not specified")
        return self._model

    def chat(
        self,
        messages: Sequence[ChatMessage] | Sequence[dict],
        options: LLMOptions | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        """
        Send a chat completion request to the LLM.

        This method normalizes the messages, calls the provider-specific
        implementation, and applies retry logic for failed requests.

        Args:
            messages: Sequence of messages for the conversation
            options: Additional options for the completion request
            callback: Optional callback function for streaming responses

        Returns:
            IntegrationResult[str]: Result of the chat completion request
        """
        try:
            # Validate inputs
            if not messages:
                raise QuackIntegrationError("No messages provided for chat request")

            # Normalize messages
            normalized_messages = self._normalize_messages(messages)

            # Use default options if not provided
            request_options = options or LLMOptions()
            if request_options.model is None:
                # Override with instance model if not specified in options
                try:
                    request_options.model = self.model
                except ValueError:
                    pass  # If model is not specified, let the concrete implementation handle it

            # Apply retry logic
            retry_count = 0
            delay = self._initial_retry_delay

            while True:
                try:
                    return self._chat_with_provider(
                        normalized_messages, request_options, callback
                    )
                except QuackApiError as e:
                    retry_count += 1
                    if retry_count > self._retry_count:
                        raise

                    # Log retry information
                    self.logger.warning(
                        f"Retrying chat request ({retry_count}/{self._retry_count}) after error: {e}"
                    )

                    # Sleep with exponential backoff
                    time.sleep(delay)
                    delay = min(delay * 2, self._max_retry_delay)

        except QuackApiError as e:
            # Handle API-specific errors (rate limits, authentication, etc.)
            self.logger.error(f"API error during chat request: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackIntegrationError as e:
            # Handle other integration-specific errors (configuration, setup, etc.)
            self.logger.error(f"Integration error during chat request: {e}")
            return IntegrationResult.error_result(f"Integration error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during chat request: {e}")
            return IntegrationResult.error_result(f"Unexpected error: {e}")

    @abstractmethod
    def _chat_with_provider(
        self,
        messages: list[ChatMessage],
        options: LLMOptions,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        """
        Provider-specific implementation of chat completion request.

        Args:
            messages: Normalized list of messages for the conversation
            options: Additional options for the completion request
            callback: Optional callback function for streaming responses

        Returns:
            IntegrationResult[str]: Result of the chat completion request
        """
        ...

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
        try:
            # Validate inputs
            if not messages:
                raise QuackIntegrationError("No messages provided for token counting")

            # Normalize messages
            normalized_messages = self._normalize_messages(messages)

            # Call provider-specific implementation
            return self._count_tokens_with_provider(normalized_messages)

        except QuackApiError as e:
            self.logger.error(f"API error during token counting: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackIntegrationError as e:
            self.logger.error(f"Integration error during token counting: {e}")
            return IntegrationResult.error_result(f"Integration error: {e}")
        except Exception as e:
            self.logger.error(f"Error counting tokens: {e}")
            return IntegrationResult.error_result(f"Error counting tokens: {e}")

    @abstractmethod
    def _count_tokens_with_provider(
        self, messages: list[ChatMessage]
    ) -> IntegrationResult[int]:
        """
        Provider-specific implementation of token counting.

        Args:
            messages: Normalized list of messages to count tokens for

        Returns:
            IntegrationResult[int]: Result containing the token count
        """
        ...

    def _normalize_messages(
        self, messages: Sequence[ChatMessage] | Sequence[dict]
    ) -> list[ChatMessage]:
        """
        Normalize messages to a list of ChatMessage objects.

        Args:
            messages: Messages to normalize

        Returns:
            list[ChatMessage]: Normalized list of messages

        Raises:
            ValueError: If messages are of an unsupported type
            QuackIntegrationError: If message conversion fails or required fields are missing
        """
        normalized_messages: list[ChatMessage] = []

        for message in messages:
            if isinstance(message, dict):
                # Ensure required keys are present
                if "role" not in message or "content" not in message:
                    raise QuackIntegrationError(
                        "Failed to normalize message: missing required fields 'role' and/or 'content'",
                        context={"message_type": type(message).__name__},
                    )
                try:
                    normalized_messages.append(ChatMessage.from_dict(message))
                except Exception as e:
                    raise QuackIntegrationError(
                        f"Failed to normalize message: {e}",
                        context={"message_type": type(message).__name__},
                        original_error=e,
                    )
            elif isinstance(message, ChatMessage):
                normalized_messages.append(message)
            else:
                raise ValueError(f"Unsupported message type: {type(message)}")

        return normalized_messages
