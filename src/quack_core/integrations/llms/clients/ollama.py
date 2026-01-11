# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/clients/ollama.py
# module: quack_core.integrations.llms.clients.ollama
# role: module
# neighbors: __init__.py, anthropic.py, base.py, mock.py, openai.py
# exports: OllamaClient
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

"""
Ollama LLM client implementation.

This module provides a client for the Ollama API, supporting local LLM inference
with proper error handling and retry logic.
"""

from collections.abc import Callable
from typing import Any

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.clients.base import LLMClient
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType
from quack_core.core.errors import QuackApiError, QuackIntegrationError
from quack_core.core.logging import LOG_LEVELS, LogLevel


class OllamaClient(LLMClient):
    """Ollama LLM client implementation."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,  # Not used but kept for API consistency
        api_base: str | None = None,
        timeout: int = 60,
        retry_count: int = 3,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 30.0,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Ollama client.

        Args:
            model: Model name to use
            api_key: Not used by Ollama but kept for API consistency
            api_base: Ollama API base URL
            timeout: Request timeout in seconds
            retry_count: Number of retries for failed requests
            initial_retry_delay: Initial delay for exponential backoff
            max_retry_delay: Maximum delay between retries
            log_level: Logging level
            **kwargs: Additional arguments
        """
        super().__init__(
            model=model,
            api_key=api_key,
            timeout=timeout,
            retry_count=retry_count,
            initial_retry_delay=initial_retry_delay,
            max_retry_delay=max_retry_delay,
            log_level=log_level,
            **kwargs,
        )
        self._api_base = api_base or "http://localhost:11434"
        self._client = None

    @property
    def model(self) -> str:
        """
        Get the model name.

        Returns:
            str: Model name
        """
        if not self._model:
            # Default model if not specified
            self._model = "llama3"
        return self._model

    def _check_requests_installed(self) -> bool:
        """
        Check if the requests package is installed.

        Returns:
            bool: True if installed, raises exception otherwise
        """
        try:
            import requests

            return True
        except ImportError as e:
            raise QuackIntegrationError(
                f"Failed to import required package: {e}. Please install requests: pip install requests",
                original_error=e,
            )

    def _chat_with_provider(
        self,
        messages: list[ChatMessage],
        options: LLMOptions,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        """
        Send a chat completion request to the Ollama API.

        Args:
            messages: List of messages for the conversation.
            options: Additional options for the completion request.
            callback: Optional callback function for streaming responses.

        Returns:
            IntegrationResult[str]: Result of the chat completion request.
        """
        # First check if requests is installed
        self._check_requests_installed()

        try:
            import requests

            # Convert messages to Ollama format
            ollama_messages = self._convert_messages_to_ollama(messages)

            # Prepare request data
            request_data = {
                "model": options.model or self.model,
                "messages": ollama_messages,
                "stream": options.stream or callback is not None,
                "options": {
                    "temperature": options.temperature,
                },
            }

            # Add max_tokens if provided
            if options.max_tokens is not None:
                request_data["options"]["num_predict"] = options.max_tokens

            # Add stop if provided
            if options.stop:
                request_data["options"]["stop"] = options.stop

            # Prepare endpoint URL
            api_url = f"{self._api_base}/api/chat"

            # Handle streaming
            if request_data["stream"]:
                return self._handle_streaming(api_url, request_data, callback)

            # Non-streaming request
            try:
                response = requests.post(
                    api_url, json=request_data, timeout=self._timeout
                )

                # Check for HTTP errors
                response.raise_for_status()

                # Parse response
                result = response.json()

                if "message" in result and "content" in result["message"]:
                    return IntegrationResult.success_result(
                        result["message"]["content"]
                    )
                else:
                    return IntegrationResult.error_result(
                        f"Unexpected response format from Ollama: {result}"
                    )

            except requests.exceptions.RequestException as e:
                raise QuackApiError(
                    f"Ollama API request failed: {e}",
                    service="Ollama",
                    api_method="chat",
                    original_error=e,
                )

        except ImportError as e:
            raise QuackIntegrationError(
                f"Failed to import required package: {e}. Please install requests: pip install requests",
                original_error=e,
            )
        except Exception as e:
            raise QuackApiError(
                f"Ollama API error: {e}",
                service="Ollama",
                api_method="chat",
                original_error=e,
            )

    def _handle_streaming(
        self,
        api_url: str,
        request_data: dict,
        callback: Callable[[str], None] | None,
    ) -> IntegrationResult[str]:
        """
        Handle streaming responses from the Ollama API.

        Args:
            api_url: API endpoint URL
            request_data: Request data
            callback: Callback function for streaming

        Returns:
            IntegrationResult[str]: Complete response
        """
        # Import at the beginning to avoid reference issues
        try:
            import json

            import requests
        except ImportError as e:
            return IntegrationResult.error_result(
                f"Failed to import required package: {e}. Please install requests: pip install requests"
            )

        try:
            collected_content = []

            with requests.post(
                api_url, json=request_data, timeout=self._timeout, stream=True
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)

                        if "message" in chunk and "content" in chunk["message"]:
                            content = chunk["message"]["content"]
                            collected_content.append(content)

                            if callback:
                                callback(content)
                    except json.JSONDecodeError:
                        self.logger.warning(
                            f"Failed to parse Ollama stream chunk: {line}"
                        )

            return IntegrationResult.success_result("".join(collected_content))

        except requests.exceptions.RequestException as e:
            raise QuackApiError(
                f"Ollama streaming API request failed: {e}",
                service="Ollama",
                api_method="chat",
                original_error=e,
            )

    def _convert_messages_to_ollama(self, messages: list[ChatMessage]) -> list[dict]:
        """
        Convert ChatMessage objects to Ollama format.

        Args:
            messages: List of ChatMessage objects

        Returns:
            list[dict]: Messages in Ollama format
        """
        ollama_messages = []

        for message in messages:
            role = self._convert_role_to_ollama(message.role)

            if message.content is not None:
                ollama_messages.append(
                    {
                        "role": role,
                        "content": message.content,
                    }
                )

        return ollama_messages

    def _convert_role_to_ollama(self, role: RoleType) -> str:
        """
        Convert a RoleType to Ollama role string.

        Args:
            role: Role type

        Returns:
            str: Ollama role
        """
        role_map = {
            RoleType.USER: "user",
            RoleType.ASSISTANT: "assistant",
            RoleType.SYSTEM: "system",
        }

        return role_map.get(role, "user")

    def _count_tokens_with_provider(
        self, messages: list[ChatMessage]
    ) -> IntegrationResult[int]:
        """
        Count tokens using Ollama API.

        Args:
            messages: List of messages to count tokens for

        Returns:
            IntegrationResult[int]: Token count
        """
        # Check requests package first
        try:
            import requests
        except ImportError as e:
            return IntegrationResult.error_result(
                f"Failed to import required package: {e}. Please install requests: pip install requests"
            )

        try:
            # Combine all message content for token counting
            combined_text = ""
            for message in messages:
                if message.content:
                    combined_text += message.content + "\n"

            # Prepare request data for token counting
            request_data = {
                "model": self.model,
                "prompt": combined_text,
            }

            # Call Ollama API for token counting
            try:
                response = requests.post(
                    f"{self._api_base}/api/tokenize",
                    json=request_data,
                    timeout=self._timeout,
                )

                response.raise_for_status()
                result = response.json()

                if "tokens" in result and isinstance(result["tokens"], list):
                    token_count = len(result["tokens"])
                    return IntegrationResult.success_result(token_count)
                else:
                    # Fallback to a simple estimation
                    estimated_tokens = len(combined_text) // 4
                    return IntegrationResult.success_result(
                        estimated_tokens,
                        message="Token count is an estimation based on text length.",
                    )

            except requests.exceptions.RequestException as e:
                # If token counting endpoint fails, fall back to estimation
                self.logger.warning(
                    f"Ollama token counting failed: {e}. Using estimation."
                )
                estimated_tokens = len(combined_text) // 4
                return IntegrationResult.success_result(
                    estimated_tokens,
                    message="Token count is an estimation. Ollama token counting API failed.",
                )

        except Exception as e:
            self.logger.error(f"Error counting tokens: {e}")
            return IntegrationResult.error_result(f"Error counting tokens: {e}")
