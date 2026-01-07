# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/clients/test_mock.py
# role: tests
# neighbors: __init__.py, test_anthropic.py, test_base.py, test_clients.py, test_ollama.py, test_openai.py
# exports: TestMockLLMClient
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Tests for the Mock LLM client.

This module tests the mock client implementation used for testing and educational purposes.
"""

from unittest.mock import MagicMock, patch

from quack_core.integrations.llms.clients.mock import MockLLMClient
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType


class TestMockLLMClient:
    """Tests for the Mock LLM client."""

    def test_init(self) -> None:
        """Test initializing the mock client."""
        # Test with default parameters
        client = MockLLMClient()
        assert client._model == "mock-model"
        assert client._script == ["This is a mock response from the LLM."]
        assert client._current_index == 0

        # Test with custom parameters
        custom_responses = ["Response 1", "Response 2"]
        client = MockLLMClient(
            script=custom_responses,
            model="custom-model",
            log_level=20,
            custom_param="value",
        )
        assert client._model == "custom-model"
        assert client._script == custom_responses
        assert client._kwargs["custom_param"] == "value"
        assert client.logger.level == 20

    def test_chat_with_provider(self) -> None:
        """Test the mock chat implementation."""
        # Test with default script
        client = MockLLMClient()
        messages = [
            ChatMessage(role=RoleType.USER, content="User message"),
        ]
        options = LLMOptions()

        result = client._chat_with_provider(messages, options)
        assert result.success is True
        assert result.content == "This is a mock response from the LLM."

        # Test with custom script
        client = MockLLMClient(script=["Response 1", "Response 2", "Response 3"])

        # First call
        result = client._chat_with_provider(messages, options)
        assert result.content == "Response 1"
        assert client._current_index == 1

        # Second call
        result = client._chat_with_provider(messages, options)
        assert result.content == "Response 2"
        assert client._current_index == 2

        # Third call
        result = client._chat_with_provider(messages, options)
        assert result.content == "Response 3"
        assert client._current_index == 3

        # Fourth call - should cycle back to the first response
        result = client._chat_with_provider(messages, options)
        assert result.content == "Response 1"
        assert client._current_index == 4

        # Test with empty script
        client = MockLLMClient(script=[])
        result = client._chat_with_provider(messages, options)
        assert result.success is False
        assert "No mock responses available" in result.error

    def test_chat_with_streaming(self) -> None:
        """Test the mock chat implementation with streaming."""
        client = MockLLMClient(script=["Hello world"])
        messages = [
            ChatMessage(role=RoleType.USER, content="User message"),
        ]
        options = LLMOptions(stream=True)
        callback = MagicMock()

        with patch.object(client, "_mock_streaming") as mock_streaming:
            result = client._chat_with_provider(messages, options, callback)
            assert result.success is True
            assert result.content == "Hello world"
            mock_streaming.assert_called_once_with("Hello world", callback)

    def test_mock_streaming(self) -> None:
        """Test the mock streaming implementation."""
        client = MockLLMClient()
        callback = MagicMock()

        # Test streaming a simple message
        with patch("time.sleep") as mock_sleep:
            client._mock_streaming("Hello world", callback)

            # Should call callback once per word
            assert callback.call_count == 2
            callback.assert_any_call("Hello ")
            callback.assert_any_call("world ")

            # Should sleep between chunks
            assert mock_sleep.call_count == 2

    def test_count_tokens_with_provider(self) -> None:
        """Test the mock token counting implementation."""
        client = MockLLMClient()

        # Test with small message
        messages = [
            ChatMessage(role=RoleType.USER, content="Short message"),
        ]

        result = client._count_tokens_with_provider(messages)
        assert result.success is True
        assert result.content > 0

        # Test with longer message
        messages = [
            ChatMessage(
                role=RoleType.SYSTEM,
                content="This is a longer system message with more tokens",
            ),
            ChatMessage(
                role=RoleType.USER,
                content="And this is a user message that also has quite a few tokens",
            ),
        ]

        result = client._count_tokens_with_provider(messages)
        assert result.success is True
        assert result.content > 0
        # Should have more tokens than the short message
        assert (
            result.content > client._count_tokens_with_provider([messages[0]]).content
        )

    def test_set_responses(self) -> None:
        """Test setting custom responses."""
        client = MockLLMClient(script=["Initial response"])

        # Initial state
        assert client._script == ["Initial response"]
        assert client._current_index == 0

        # First call
        result = client.chat([ChatMessage(role=RoleType.USER, content="User message")])
        assert result.content == "Initial response"
        assert client._current_index == 1

        # Set new responses
        new_responses = ["New response 1", "New response 2"]
        client.set_responses(new_responses)

        # Should reset the index and set new responses
        assert client._script == new_responses
        assert client._current_index == 0

        # Next call should use the first new response
        result = client.chat([ChatMessage(role=RoleType.USER, content="User message")])
        assert result.content == "New response 1"
