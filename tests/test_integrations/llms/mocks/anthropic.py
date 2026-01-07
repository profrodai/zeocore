# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/mocks/anthropic.py
# role: tests
# neighbors: __init__.py, base.py, clients.py, openai.py
# exports: MockAnthropicResponse, MockAnthropicStreamingResponse, MockAnthropicErrorResponse, MockAnthropicClient
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Mock Anthropic classes for LLM testing.
"""

from typing import Any
from unittest.mock import MagicMock

from tests.test_integrations.llms.mocks.base import (
    MockLLMResponse,
    MockStreamingGenerator,
)
from tests.test_integrations.llms.mocks.clients import MockClient


class MockAnthropicResponse(MockLLMResponse):
    """A mock response mimicking the Anthropic API format."""

    def __init__(
        self,
        content: str = "This is a mock Anthropic response",
        model: str = "claude-3-opus-20240229",
        usage: dict[str, int] | None = None,
        finish_reason: str = "end_turn",
        error: Exception | None = None,
        id: str = "msg_123",
        type: str = "message",
        stop_reason: str | None = None,
        stop_sequence: str | None = None,
    ):
        """
        Initialize a mock Anthropic response.

        Args:
            content: The text content of the response
            model: The model name that generated the response
            usage: Token usage statistics
            finish_reason: Reason the generation finished
            error: Optional error to raise instead of returning a response
            id: The ID of the message
            type: Type of Anthropic object
            stop_reason: Reason for stopping (mapped from finish_reason)
            stop_sequence: Stop sequence that triggered the stop
        """
        super().__init__(
            content=content,
            model=model,
            usage=usage,
            finish_reason=finish_reason,
            error=error,
        )

        self.id = id
        self.type = type
        self.stop_reason = stop_reason or finish_reason
        self.stop_sequence = stop_sequence

        # Create Anthropic-style structure
        self.content = [MagicMock(type="text", text=content)]

    def to_anthropic_format(self) -> dict[str, Any]:
        """Convert to Anthropic API format."""
        if self.error:
            raise self.error

        return {
            "id": self.id,
            "type": self.type,
            "role": "assistant",
            "content": [{"type": "text", "text": self.get_content()}],
            "model": self.model,
            "stop_reason": self.stop_reason,
            "stop_sequence": self.stop_sequence,
            "usage": {
                "input_tokens": self.usage["prompt_tokens"],
                "output_tokens": self.usage["completion_tokens"],
            },
        }


class MockAnthropicStreamingResponse(MockStreamingGenerator):
    """A generator that yields chunks in Anthropic streaming format."""

    def __init__(
        self,
        content: str = "This is a mock Anthropic response",
        chunk_size: int = 5,
        model: str = "claude-3-opus-20240229",
        error: Exception | None = None,
        error_after: int | None = None,
        id: str = "msg_123",
    ) -> None:
        """
        Initialize a mock Anthropic streaming generator.

        Args:
            content: The full content to stream
            chunk_size: Size of each chunk to yield in characters
            model: The model name
            error: Optional error to raise
            error_after: Number of chunks after which to raise the error
            id: The ID of the message
        """
        super().__init__(
            content=content,
            chunk_size=chunk_size,
            model=model,
            error=error,
            error_after=error_after,
        )
        self.id = id
        self.chunks_iter = None

    def __iter__(self) -> "MockAnthropicStreamingResponse":
        """Return self as iterator."""
        self.chunks_iter = self.generate_chunks()
        return self

    def __next__(self) -> Any:
        """
        Get the next chunk in Anthropic streaming format.

        Returns:
            Dict: A chunk of the response in Anthropic format

        Raises:
            StopIteration: When all chunks have been yielded
            Exception: If error is set and error_after chunks have been yielded
        """
        try:
            chunk_text = next(self.chunks_iter)

            # Create a mock chunk in Anthropic format
            mock_chunk = MagicMock()
            mock_chunk.type = "content_block_delta"
            mock_chunk.delta = MagicMock()
            mock_chunk.delta.type = "text"
            mock_chunk.delta.text = chunk_text
            mock_chunk.index = 0

            return mock_chunk
        except StopIteration:
            # For the last chunk, use a different type
            mock_chunk = MagicMock()
            mock_chunk.type = "message_stop"
            mock_chunk.message = MagicMock()
            mock_chunk.message.id = self.id
            mock_chunk.message.model = self.model
            mock_chunk.message.stop_reason = "end_turn"

            # Re-raise StopIteration to end the stream
            raise StopIteration

    def __enter__(self) -> "MockAnthropicStreamingResponse":
        """Context manager enter method."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit method."""
        pass

    def message_stream(self) -> "MockAnthropicStreamingResponse":
        """Context manager for Anthropic streaming."""
        return self


class MockAnthropicErrorResponse:
    """A mock error response mimicking Anthropic API errors."""

    def __init__(
        self,
        message: str = "Anthropic API error",
        type: str = "api_error",
        status_code: int = 429,
    ):
        """
        Initialize a mock Anthropic error response.

        Args:
            message: Error message
            type: Error type
            status_code: HTTP status code
        """
        self.message = message
        self.type = type
        self.status_code = status_code

    def to_exception(self) -> Exception:
        """
        Convert to an exception that mimics Anthropic's error format.

        Returns:
            Exception: An exception with Anthropic error attributes
        """
        # Create a mock response with status_code
        response = MagicMock()
        response.status_code = self.status_code

        # Create an error object similar to what Anthropic would return
        error = {
            "error": {
                "message": self.message,
                "type": self.type,
            }
        }

        # Create an exception with Anthropic-like attributes
        exception = Exception(f"Anthropic API error: {self.message}")
        exception.response = response
        exception.error = error

        return exception


class MockAnthropicClient(MockClient):
    """A mock Anthropic client."""

    def __init__(
        self,
        responses: list[str] = None,
        token_counts: list[int] = None,
        model: str = "claude-3-opus-20240229",
        errors: list[Exception] = None,
        **kwargs: Any,
    ):
        """
        Initialize a mock Anthropic client.

        Args:
            responses: List of responses to return
            token_counts: List of token counts to return
            model: Model name
            errors: List of errors to raise
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            responses=responses,
            token_counts=token_counts,
            model=model,
            errors=errors,
            **kwargs,
        )

        # Track Anthropic-specific data
        self.anthropic_requests = []

    def messages_create(self, *args, **kwargs):
        """
        Mock Anthropic's messages.create method.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Union[MockAnthropicResponse, MockAnthropicStreamingResponse]: Response object

        Raises:
            Exception: If configured to raise an error
        """
        self.anthropic_requests.append(kwargs)

        # Get the response for this call
        response_idx = min(len(self.anthropic_requests) - 1, len(self.responses) - 1)
        response_text = self.responses[response_idx]

        # Check if we should raise an error
        if self.errors and len(self.anthropic_requests) <= len(self.errors):
            error = self.errors[len(self.anthropic_requests) - 1]
            if error:
                raise error

        # Handle streaming
        if kwargs.get("stream", False):
            return MockAnthropicStreamingResponse(
                content=response_text, model=self.model
            )

        # Return a normal response
        return MockAnthropicResponse(content=response_text, model=self.model)

    def count_tokens(self, *args, **kwargs):
        """
        Mock Anthropic's count_tokens method.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            MagicMock: A mock token count response

        Raises:
            Exception: If configured to raise an error
        """
        count_idx = min(self.count_tokens_call_count, len(self.token_counts) - 1)
        token_count = self.token_counts[count_idx]

        # Check if we should raise an error
        if self.errors and self.count_tokens_call_count < len(self.errors):
            error = self.errors[self.count_tokens_call_count]
            if error:
                raise error

        self.count_tokens_call_count += 1

        # Create a mock token count response in Anthropic format
        response = MagicMock()
        response.input_tokens = token_count
        return response
