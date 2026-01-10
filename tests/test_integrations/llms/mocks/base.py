# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/mocks/base.py
# role: tests
# neighbors: __init__.py, anthropic.py, clients.py, openai.py
# exports: MockLLMResponse, MockTokenResponse, MockStreamingGenerator
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

"""
Base mock classes for LLM testing.
"""

from collections.abc import Generator, Iterator
from typing import Any
from unittest.mock import MagicMock


class MockLLMResponse:
    """A mock LLM response for testing client implementations."""

    def __init__(
        self,
        content: str = "This is a mock response",
        model: str = "mock-model",
        usage: dict[str, int] | None = None,
        finish_reason: str = "stop",
        error: Exception | None = None,
    ):
        """
        Initialize a mock LLM response.

        Args:
            content: The text content of the response
            model: The model name that generated the response
            usage: Token usage statistics
            finish_reason: Reason the generation finished
            error: Optional error to raise instead of returning a response
        """
        self.content = content
        self.model = model
        self.usage = usage or {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        self.finish_reason = finish_reason
        self.error = error

        # Create OpenAI-style structure
        self.choices = [
            MagicMock(
                index=0,
                message=MagicMock(content=content, role="assistant"),
                finish_reason=finish_reason,
            )
        ]

        # Add token usage
        self.usage_info = MagicMock(
            prompt_tokens=self.usage["prompt_tokens"],
            completion_tokens=self.usage["completion_tokens"],
            total_tokens=self.usage["total_tokens"],
        )

    def get_content(self) -> str:
        """Get the response content."""
        if self.error:
            raise self.error
        return self.content

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary representation."""
        if self.error:
            raise self.error
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
        }


class MockTokenResponse:
    """A mock token count response."""

    def __init__(self, count: int = 30, error: Exception | None = None):
        """
        Initialize a mock token count response.

        Args:
            count: Token count to return
            error: Optional error to raise
        """
        self.count = count
        self.error = error

        # OpenAI-style structure
        self.token_count = count

        # Anthropic-style structure
        self.input_tokens = count

    def get_count(self) -> int:
        """Get the token count."""
        if self.error:
            raise self.error
        return self.count


class MockStreamingGenerator:
    """A generator that yields mock streaming chunks."""

    def __init__(
        self,
        content: str = "This is a mock response",
        chunk_size: int = 5,
        model: str = "mock-model",
        error: Exception | None = None,
        error_after: int | None = None,
    ):
        """
        Initialize a mock streaming generator.

        Args:
            content: The full content to stream
            chunk_size: Size of each chunk to yield in characters
            model: The model name
            error: Optional error to raise
            error_after: Number of chunks after which to raise the error
        """
        self.content = content
        self.chunk_size = chunk_size
        self.model = model
        self.error = error
        self.error_after = error_after

    def __iter__(self) -> Iterator[Any]:
        """Return self as iterator."""
        return self

    def __next__(self) -> Any:
        """Not implemented directly, use the provider-specific generators."""
        raise NotImplementedError("Use a provider-specific streaming generator")

    def generate_chunks(self) -> Generator[str]:
        """
        Generate chunks of content for streaming.

        Yields:
            Chunks of the content string.

        Raises:
            Exception: If error is set and error_after chunks have been yielded.
        """
        chunks = [
            self.content[i : i + self.chunk_size]
            for i in range(0, len(self.content), self.chunk_size)
        ]

        for i, chunk in enumerate(chunks):
            if self.error and self.error_after is not None and i >= self.error_after:
                raise self.error
            yield chunk
