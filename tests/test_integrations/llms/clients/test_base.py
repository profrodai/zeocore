# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/clients/test_base.py
# role: tests
# neighbors: __init__.py, test_anthropic.py, test_clients.py, test_mock.py, test_ollama.py, test_openai.py
# exports: TestLLMClient
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Tests for the base LLM client.

This module tests the abstract base class for LLM clients, including
retry logic, error handling, and message normalization.
"""

import logging
import time
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.core.results import (  # Import IntegrationResult for testing
    IntegrationResult,
)
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType
from quack_core.core.errors import QuackApiError, QuackIntegrationError

from tests.test_integrations.llms.mocks.clients import MockClient


class TestLLMClient:
    """Tests for the base LLM client."""

    @pytest.fixture
    def mock_client(self) -> MockClient:
        """Create a mock LLM client for testing."""
        return MockClient(model="test-model")

    def test_init(self) -> None:
        """Test initializing the LLM client."""
        # Test with default parameters
        client = MockClient()
        assert client._model == "mock-model"
        assert client._api_key is None
        assert client._timeout == 60
        assert client._retry_count == 3
        assert client._initial_retry_delay == 1.0
        assert client._max_retry_delay == 30.0
        assert client.logger.level == logging.INFO

        # Test with custom parameters
        client = MockClient(
            model="custom-model",
            api_key="test-key",
            timeout=30,
            retry_count=5,
            initial_retry_delay=0.5,
            max_retry_delay=10.0,
            log_level=logging.DEBUG,
            custom_param="value",
        )
        assert client._model == "custom-model"
        assert client._api_key == "test-key"
        assert client._timeout == 30
        assert client._retry_count == 5
        assert client._initial_retry_delay == 0.5
        assert client._max_retry_delay == 10.0
        assert client.logger.level == logging.DEBUG
        assert client._kwargs["custom_param"] == "value"

    def test_model_property(self, mock_client: MockClient) -> None:
        """Test the model property."""
        assert mock_client.model == "test-model"

        # Test with no model specified
        client = MockClient()
        client._model = None
        with pytest.raises(ValueError):
            _ = client.model

    def test_chat_normalize_messages(self, mock_client: MockClient) -> None:
        """Test normalizing messages in the chat method."""
        # Test with ChatMessage objects
        messages = [
            ChatMessage(role=RoleType.SYSTEM, content="System message"),
            ChatMessage(role=RoleType.USER, content="User message"),
        ]

        result = mock_client.chat(messages)
        assert result.success is True
        assert mock_client.last_messages == messages

        # Test with dictionaries
        dict_messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "User message"},
        ]

        result = mock_client.chat(dict_messages)
        assert result.success is True
        assert len(mock_client.last_messages) == 2
        assert mock_client.last_messages[0].role == RoleType.SYSTEM
        assert mock_client.last_messages[0].content == "System message"
        assert mock_client.last_messages[1].role == RoleType.USER
        assert mock_client.last_messages[1].content == "User message"

        # Test with invalid message type (update: check error result instead of exception)
        invalid_messages = cast(list[dict], ["invalid message"])
        result = mock_client.chat(invalid_messages)
        assert result.success is False
        assert "Unsupported message type" in result.error

    def test_chat_default_options(self, mock_client: MockClient) -> None:
        """Test using default options in the chat method."""
        messages = [
            ChatMessage(role=RoleType.USER, content="User message"),
        ]

        result = mock_client.chat(messages)
        assert result.success is True
        assert isinstance(mock_client.last_options, LLMOptions)
        assert mock_client.last_options.temperature == 0.7  # Default value
        assert (
            mock_client.last_options.model == "test-model"
        )  # Should use client's model

    def test_chat_custom_options(self, mock_client: MockClient) -> None:
        """Test using custom options in the chat method."""
        messages = [
            ChatMessage(role=RoleType.USER, content="User message"),
        ]
        options = LLMOptions(
            temperature=0.5,
            max_tokens=100,
            model="custom-model",
            stream=True,
        )

        result = mock_client.chat(messages, options)
        assert result.success is True
        assert mock_client.last_options == options
        assert (
            mock_client.last_options.model == "custom-model"
        )  # Should use provided model

    def test_chat_with_callback(self, mock_client: MockClient) -> None:
        """Test the chat method with a callback function."""
        messages = [
            ChatMessage(role=RoleType.USER, content="User message"),
        ]
        callback = MagicMock()
        options = LLMOptions(stream=True)

        result = mock_client.chat(messages, options, callback)
        assert result.success is True
        assert mock_client.last_callback == callback

    def test_chat_empty_messages(self, mock_client: MockClient) -> None:
        """Test the chat method with empty messages."""
        result = mock_client.chat([])
        assert result.success is False
        assert "No messages provided for chat request" in result.error

    def test_chat_error_handling(self, mock_client: MockClient) -> None:
        """Test error handling in the chat method."""
        messages = [
            ChatMessage(role=RoleType.USER, content="User message"),
        ]

        # Test with API error
        with patch.object(mock_client, "_chat_with_provider") as mock_chat:
            mock_chat.side_effect = QuackApiError("API error", "TestService")
            result = mock_client.chat(messages)
            assert result.success is False
            assert "API error" in result.error

        # Test with integration error
        with patch.object(mock_client, "_chat_with_provider") as mock_chat:
            mock_chat.side_effect = QuackIntegrationError("Integration error")
            result = mock_client.chat(messages)
            assert result.success is False
            assert "Integration error" in result.error

        # Test with generic error
        with patch.object(mock_client, "_chat_with_provider") as mock_chat:
            mock_chat.side_effect = Exception("Unexpected error")
            result = mock_client.chat(messages)
            assert result.success is False
            assert "Unexpected error" in result.error

    def test_chat_retry_logic(self) -> None:
        """Test retry logic in the chat method."""
        messages = [
            ChatMessage(role=RoleType.USER, content="User message"),
        ]

        # Create a client with retries
        client = MockClient(
            model="test-model",
            retry_count=2,
            initial_retry_delay=0.1,
            max_retry_delay=0.2,
        )

        # Mock _chat_with_provider to fail twice, then succeed.
        # For the successful case, use the class method to create a proper IntegrationResult.
        mock_provider = MagicMock()
        error = QuackApiError("Rate limit exceeded", "TestService")
        mock_provider.side_effect = [
            error,
            error,
            IntegrationResult.success_result("Success"),
        ]

        with patch.object(client, "_chat_with_provider", mock_provider):
            with patch.object(time, "sleep") as mock_sleep:
                result = client.chat(messages)

                # Should have called the provider 3 times (initial + 2 retries)
                assert mock_provider.call_count == 3

                # Should have slept twice (after first and second failure)
                assert mock_sleep.call_count == 2

                # Check sleep durations - should be exponential backoff
                assert mock_sleep.call_args_list[0][0][0] == 0.1  # Initial delay
                assert (
                    mock_sleep.call_args_list[1][0][0] == 0.2
                )  # Doubled but capped at max

                # Verify the result was successful after retries
                assert result.success is True
                assert result.content == "Success"

        # Test reaching max retries
        client = MockClient(
            model="test-model",
            retry_count=1,
            initial_retry_delay=0.1,
        )

        mock_provider = MagicMock()
        mock_provider.side_effect = QuackApiError("Rate limit exceeded", "TestService")

        with patch.object(client, "_chat_with_provider", mock_provider):
            with patch.object(time, "sleep") as mock_sleep:
                result = client.chat(messages)

                # Should have called the provider 2 times (initial + 1 retry)
                assert mock_provider.call_count == 2

                # Should have slept once
                assert mock_sleep.call_count == 1

                # Result should be an error
                assert result.success is False
                assert "Rate limit exceeded" in result.error

    def test_count_tokens(self, mock_client: MockClient) -> None:
        """Test the count_tokens method."""
        messages = [
            ChatMessage(role=RoleType.SYSTEM, content="System message"),
            ChatMessage(role=RoleType.USER, content="User message"),
        ]

        result = mock_client.count_tokens(messages)
        assert result.success is True
        assert result.content == 30  # Default value from mock

        # Test with dictionaries
        dict_messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "User message"},
        ]

        result = mock_client.count_tokens(dict_messages)
        assert result.success is True
        assert result.content == 30

        # Test with empty messages
        result = mock_client.count_tokens([])
        assert result.success is False
        assert "No messages provided for token counting" in result.error

        # Test with error
        with patch.object(mock_client, "_count_tokens_with_provider") as mock_count:
            mock_count.side_effect = Exception("Counting error")
            result = mock_client.count_tokens(messages)
            assert result.success is False
            assert "Error counting tokens: Counting error" in result.error

    def test_normalize_messages(self, mock_client: MockClient) -> None:
        """Test the _normalize_messages method."""
        # Test with ChatMessage objects
        messages = [
            ChatMessage(role=RoleType.SYSTEM, content="System message"),
            ChatMessage(role=RoleType.USER, content="User message"),
        ]

        normalized = mock_client._normalize_messages(messages)
        assert normalized == messages

        # Test with dictionaries
        dict_messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "User message"},
        ]

        normalized = mock_client._normalize_messages(dict_messages)
        assert len(normalized) == 2
        assert normalized[0].role == RoleType.SYSTEM
        assert normalized[0].content == "System message"
        assert normalized[1].role == RoleType.USER
        assert normalized[1].content == "User message"

        # Test with invalid message
        # Using cast to tell type checker we're deliberately testing with invalid type
        invalid_message = cast(list[dict], ["invalid"])
        with pytest.raises(ValueError):
            mock_client._normalize_messages(invalid_message)

        # Test with dictionary missing required fields
        with pytest.raises(QuackIntegrationError):
            mock_client._normalize_messages([{}])
