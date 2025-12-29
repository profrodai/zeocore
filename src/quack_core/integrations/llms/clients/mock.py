# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/clients/mock.py
# module: quack_core.integrations.llms.clients.mock
# role: module
# neighbors: __init__.py, anthropic.py, base.py, ollama.py, openai.py
# exports: MockLLMClient
# git_branch: refactor/toolkitWorkflow
# git_commit: 0f9247b
# === QV-LLM:END ===

"""
Mock LLM client implementation.

This module provides a mock implementation of the LLM client for testing
and educational purposes, allowing scripted responses without API calls.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.clients.base import LLMClient
from quack_core.integrations.llms.models import ChatMessage, LLMOptions


class MockLLMClient(LLMClient):
    """Mock LLM client for testing and educational purposes."""

    def __init__(
        self,
        script: list[str] | None = None,
        model: str = "mock-model",
        log_level: int = logging.INFO,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the mock LLM client.

        Args:
            script: List of responses to return in sequence.
                    If None, a default response will be used.
            model: Mock model name.
            log_level: Logging level.
            **kwargs: Additional arguments.
        """
        super().__init__(model=model, log_level=log_level, **kwargs)
        # Check explicitly for None instead of falsy check
        self._script = (
            ["This is a mock response from the LLM."] if script is None else script
        )
        self._current_index = 0

    def _chat_with_provider(
        self,
        messages: list[ChatMessage],
        options: LLMOptions,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        """
        Return a mock response from the script.

        Args:
            messages: List of messages for the conversation.
            options: Additional options for the completion request.
            callback: Optional callback function for streaming responses.

        Returns:
            IntegrationResult[str]: Result of the chat completion request.
        """
        # Get the next response from the script
        if not self._script:
            return IntegrationResult.error_result("No mock responses available")

        response = self._script[self._current_index % len(self._script)]
        self._current_index += 1

        # Handle streaming if callback is provided
        if callback and options.stream:
            self._mock_streaming(response, callback)

        return IntegrationResult.success_result(response)

    def _mock_streaming(self, response: str, callback: Callable[[str], None]) -> None:
        """
        Simulate streaming by sending chunks of the response to the callback.

        Args:
            response: Full response text.
            callback: Callback function for streaming responses.
        """
        # Split the response into chunks (words for simplicity)
        chunks = response.split(" ")

        for chunk in chunks:
            # Add the space back except for the last chunk
            chunk_with_space = chunk + " "
            callback(chunk_with_space)
            time.sleep(0.1)  # Simulate delay between chunks

    def _count_tokens_with_provider(
        self, messages: list[ChatMessage]
    ) -> IntegrationResult[int]:
        """
        Provide a mock token count.

        Args:
            messages: List of messages to count tokens for.

        Returns:
            IntegrationResult[int]: Result containing the token count.
        """
        # Simple mock implementation: count characters and divide by 4
        total_chars = 0
        for message in messages:
            if message.content:
                total_chars += len(message.content)

        # Rough approximation: 1 token ≈ 4 characters
        mock_token_count = total_chars // 4

        return IntegrationResult.success_result(mock_token_count)

    def set_responses(self, responses: list[str]) -> None:
        """
        Set the list of responses to return.

        Args:
            responses: List of responses to return in sequence.
        """
        self._script = responses
        self._current_index = 0
