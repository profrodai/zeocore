# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/mocks/openai.py
# role: tests
# neighbors: __init__.py, anthropic.py, base.py, clients.py
# exports: MockOpenAIResponse, MockOpenAIStreamingResponse, MockOpenAIErrorResponse, MockOpenAIClient
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Mock OpenAI classes for LLM testing.
"""

from typing import Any
from unittest.mock import MagicMock

from tests.test_integrations.llms.mocks.base import (
    MockLLMResponse,
    MockStreamingGenerator,
)
from tests.test_integrations.llms.mocks.clients import MockClient


class MockOpenAIResponse(MockLLMResponse):
    """A mock response mimicking the OpenAI API format."""

    def __init__(
        self,
        content: str = "This is a mock OpenAI response",
        model: str = "gpt-4o",
        usage: dict[str, int] | None = None,
        finish_reason: str = "stop",
        error: Exception | None = None,
        object_type: str = "chat.completion",
        id: str = "chatcmpl-123",
        created: int = 1677858242,
    ):
        """
        Initialize a mock OpenAI response.

        Args:
            content: The text content of the response
            model: The model name that generated the response
            usage: Token usage statistics
            finish_reason: Reason the generation finished
            error: Optional error to raise instead of returning a response
            object_type: Type of OpenAI object
            id: The ID of the completion
            created: Unix timestamp for when the completion was created
        """
        super().__init__(
            content=content,
            model=model,
            usage=usage,
            finish_reason=finish_reason,
            error=error,
        )

        self.id = id
        self.object = object_type
        self.created = created

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI API format."""
        if self.error:
            raise self.error

        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self.content,
                    },
                    "finish_reason": self.finish_reason,
                }
            ],
            "usage": self.usage,
        }


class MockOpenAIStreamingResponse(MockStreamingGenerator):
    """A generator that yields chunks in OpenAI streaming format."""

    def __init__(
        self,
        content: str = "This is a mock response",
        chunk_size: int = 5,
        model: str = "mock-model",
        error: Exception | None = None,
        error_after: int | None = None,
    ):
        """Initialize with content to stream in chunks."""
        super().__init__(
            content=content,
            chunk_size=chunk_size,
            model=model,
            error=error,
            error_after=error_after,
        )
        # Pre-generate all chunks to avoid iteration issues
        self.chunks = list(self._generate_all_chunks())
        self.current_index = 0

    def _generate_all_chunks(self):
        """Generate all chunks at once."""
        # Split the response into chunks
        chunks = [
            self.content[i : i + self.chunk_size]
            for i in range(0, len(self.content), self.chunk_size)
        ]

        # Generate content chunks
        for i, chunk in enumerate(chunks):
            if self.error and self.error_after is not None and i >= self.error_after:
                raise self.error

            yield {
                "choices": [
                    {
                        "delta": {
                            "content": chunk,
                            "role": "assistant" if i == 0 else None,
                        },
                        "finish_reason": None,
                    }
                ],
                "model": self.model,
            }

        # Add final chunk with finish_reason
        yield {
            "choices": [{"delta": {"content": None}, "finish_reason": "stop"}],
            "model": self.model,
        }

    def __iter__(self):
        """Return self as iterator."""
        self.current_index = 0
        return self

    def __next__(self):
        """Get next chunk."""
        if self.current_index < len(self.chunks):
            chunk = self.chunks[self.current_index]
            self.current_index += 1
            return chunk
        raise StopIteration


class MockOpenAIErrorResponse:
    """A mock error response mimicking OpenAI API errors."""

    def __init__(
        self,
        message: str = "OpenAI API error",
        code: str = "rate_limit_exceeded",
        type: str = "server_error",
        param: str | None = None,
        status_code: int = 429,
    ):
        """
        Initialize a mock OpenAI error response.

        Args:
            message: Error message
            code: Error code
            type: Error type
            param: Parameter that caused the error
            status_code: HTTP status code
        """
        self.message = message
        self.code = code
        self.type = type
        self.param = param
        self.status_code = status_code

    def to_exception(self) -> Exception:
        """
        Convert to an exception that mimics OpenAI's error format.

        Returns:
            Exception: An exception with OpenAI error attributes
        """
        # Create a mock response with status_code
        response = MagicMock()
        response.status_code = self.status_code

        # Create an error object similar to what OpenAI would return
        error = {
            "message": self.message,
            "type": self.type,
            "code": self.code,
        }
        if self.param:
            error["param"] = self.param

        # Create an exception with OpenAI-like attributes
        exception = Exception(f"OpenAI API error: {self.message}")
        exception.response = response
        exception.error = error

        return exception


class MockOpenAIClient(MockClient):
    """A mock OpenAI client."""

    def __init__(
        self,
        responses: list[str] = None,
        token_counts: list[int] = None,
        model: str = "gpt-4o",
        errors: list[Exception] = None,
        **kwargs: Any,
    ):
        """
        Initialize a mock OpenAI client.

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

        # Track OpenAI-specific data
        self.openai_requests = []

    def chat_completions_create(self, *args, **kwargs):
        """
        Mock OpenAI's chat.completions.create method.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Union[MockOpenAIResponse, MockOpenAIStreamingResponse]: Response object

        Raises:
            Exception: If configured to raise an error
        """
        self.openai_requests.append(kwargs)

        # Get the response for this call
        response_idx = min(len(self.openai_requests) - 1, len(self.responses) - 1)
        response_text = self.responses[response_idx]

        # Check if we should raise an error
        if self.errors and len(self.openai_requests) <= len(self.errors):
            error = self.errors[len(self.openai_requests) - 1]
            if error:
                raise error

        # Handle streaming
        if kwargs.get("stream", False):
            return MockOpenAIStreamingResponse(content=response_text, model=self.model)

        # Return a normal response
        return MockOpenAIResponse(content=response_text, model=self.model)
