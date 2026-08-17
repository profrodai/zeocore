"""
Tests for LLM protocols.

This module tests the runtime protocol implementations for LLMs, ensuring
all required methods are present and correctly implemented.
"""

from collections.abc import Callable, Sequence
from unittest.mock import MagicMock

from tests.test_integrations.llms.mocks.clients import MockClient
from zeo_core.integrations.core import IntegrationResult
from zeo_core.integrations.llms.models import ChatMessage, LLMOptions
from zeo_core.integrations.llms.protocols import LLMProviderProtocol


class TestLLMProtocols:
    """Tests for LLM protocol implementations."""

    def test_llm_provider_protocol(self) -> None:
        """Test that LLMClient properly implements the LLMProviderProtocol."""
        # Create a mock client
        client = MockClient(model="test-model")

        # Check that it implements the protocol
        assert isinstance(client, LLMProviderProtocol)

        # Test the protocol methods
        messages = [ChatMessage.from_dict({"role": "user", "content": "Test message"})]
        options = LLMOptions(temperature=0.5)

        # Call chat method
        chat_result = client.chat(messages, options)
        assert chat_result.success is True

        # Call count_tokens method
        token_result = client.count_tokens(messages)
        assert token_result.success is True

        # Check model property
        assert client.model == "test-model"

    def test_incomplete_protocol_implementation(self) -> None:
        """Test that incomplete implementations don't satisfy the protocol."""
        # Create a very basic mock that won't match the protocol
        mock = MagicMock()
        assert not isinstance(mock, LLMProviderProtocol)

        # Test with a more specific implementation that has properties
        # but not all methods
        class PartialImpl:
            @property
            def model(self) -> str:
                return "test-model"

        partial = PartialImpl()
        assert not isinstance(partial, LLMProviderProtocol)

        # Test with a complete implementation
        class CompleteImpl:
            def chat(
                self,
                messages: Sequence[ChatMessage] | Sequence[dict],
                options: LLMOptions | None = None,
                callback: Callable[[str], None] | None = None,
            ) -> IntegrationResult[str]:
                return IntegrationResult.success_result("test")

            def count_tokens(
                self, messages: Sequence[ChatMessage] | Sequence[dict]
            ) -> IntegrationResult[int]:
                return IntegrationResult.success_result(42)

            @property
            def model(self) -> str:
                return "test-model"

        complete = CompleteImpl()
        assert isinstance(complete, LLMProviderProtocol)
