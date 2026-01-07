# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/mocks/clients.py
# role: tests
# neighbors: __init__.py, anthropic.py, base.py, openai.py
# exports: MockClient, create_mock_client
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

"""
Mock client implementations for LLM testing.
"""

import logging
from collections.abc import Callable
from typing import Any

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.clients.base import LLMClient
from quack_core.integrations.llms.models import ChatMessage, LLMOptions


class MockClient(LLMClient):
    """Base mock client for testing."""

    def __init__(
        self,
        responses: list[str] = None,
        token_counts: list[int] = None,
        model: str = "mock-model",
        errors: list[Exception] = None,
        log_level: int = logging.INFO,
        **kwargs: Any,
    ):
        """
        Initialize a mock LLM client.

        Args:
            responses: List of responses to return for each call to chat
            token_counts: List of token counts to return for each call to count_tokens
            model: Mock model name
            errors: List of errors to raise for each call
            log_level: Logging level
            **kwargs: Additional keyword arguments
        """
        super().__init__(model=model, log_level=log_level, **kwargs)
        self.responses = responses or ["This is a mock response"]
        self.token_counts = token_counts or [30]
        self.errors = errors or []

        self.chat_call_count = 0
        self.count_tokens_call_count = 0

        self.last_messages = None
        self.last_options = None
        self.last_callback = None

    def _chat_with_provider(
        self,
        messages: list[ChatMessage],
        options: LLMOptions,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        """
        Mock implementation of chat method.

        Args:
            messages: List of messages for the conversation
            options: Additional options for the completion request
            callback: Optional callback function for streaming responses

        Returns:
            IntegrationResult[str]: Result containing the response
        """
        self.chat_call_count += 1
        self.last_messages = messages
        self.last_options = options
        self.last_callback = callback

        # Check if we should raise an error
        if self.errors and self.chat_call_count <= len(self.errors):
            error = self.errors[self.chat_call_count - 1]
            if error:
                return IntegrationResult.error_result(str(error))

        # Get the response for this call
        response_idx = min(self.chat_call_count - 1, len(self.responses) - 1)
        response = self.responses[response_idx]

        # Handle streaming callback if provided
        if callback and options.stream:
            self._handle_streaming(response, callback)

        return IntegrationResult.success_result(response)

    def _handle_streaming(self, response: str, callback: Callable[[str], None]) -> None:
        """
        Simulate streaming by calling the callback with chunks of the response.

        Args:
            response: The full response text
            callback: Callback function to call with each chunk
        """
        # Split the response into words for simplicity
        words = response.split()

        # Send each word with a space
        for word in words:
            callback(word + " ")

    def _count_tokens_with_provider(
        self, messages: list[ChatMessage]
    ) -> IntegrationResult[int]:
        """
        Mock implementation of count_tokens method.

        Args:
            messages: List of messages to count tokens for

        Returns:
            IntegrationResult[int]: Result containing the token count
        """
        self.count_tokens_call_count += 1

        # Check if we should raise an error
        if self.errors and self.count_tokens_call_count <= len(self.errors):
            error = self.errors[self.count_tokens_call_count - 1]
            if error:
                return IntegrationResult.error_result(str(error))

        # Get the token count for this call
        count_idx = min(self.count_tokens_call_count - 1, len(self.token_counts) - 1)
        count = self.token_counts[count_idx]

        return IntegrationResult.success_result(count)


def create_mock_client(
    client_type: type[LLMClient] = MockClient,
    responses: list[str] = None,
    token_counts: list[int] = None,
    model: str = "mock-model",
    errors: list[Exception] = None,
    **kwargs: Any,
) -> LLMClient:
    """
    Create a mock LLM client of the specified type.

    Args:
        client_type: Type of client to create
        responses: List of responses to return
        token_counts: List of token counts to return
        model: Model name
        errors: List of errors to raise
        **kwargs: Additional keyword arguments to pass to the client

    Returns:
        LLMClient: A mock LLM client
    """
    return client_type(
        responses=responses,
        token_counts=token_counts,
        model=model,
        errors=errors,
        **kwargs,
    )
