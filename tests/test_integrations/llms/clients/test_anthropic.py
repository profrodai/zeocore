# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/clients/test_anthropic.py
# role: tests
# neighbors: __init__.py, test_base.py, test_clients.py, test_mock.py, test_ollama.py, test_openai.py
# exports: TestAnthropicClient
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""
Tests for the Anthropic LLM client.

This module tests the Anthropic-specific client implementation, including
authentication, API interactions, and error handling.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackApiError, QuackIntegrationError
from quack_core.integrations.llms.clients.anthropic import AnthropicClient
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType
from tests.test_integrations.llms.mocks.anthropic import (
    MockAnthropicClient,
    MockAnthropicErrorResponse,
    MockAnthropicResponse,
    MockAnthropicStreamingResponse,
)


class TestAnthropicClient:
    """Tests for the Anthropic LLM client."""

    @pytest.fixture
    def anthropic_client(self) -> AnthropicClient:
        """Create an Anthropic client with test API key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            return AnthropicClient(model="claude-3-opus-20240229")

    def test_init(self) -> None:
        """Test initializing the Anthropic client."""
        # Test with default parameters
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = AnthropicClient()
            assert client._model is None  # Will use default if not specified
            assert client._api_key is None  # Will get from env
            assert client._api_base is None
            assert client._timeout == 60
            assert client._client is None

        # Test with custom parameters
        client = AnthropicClient(
            model="claude-3-opus-20240229",
            api_key="custom-key",
            api_base="https://custom-api.anthropic.com",
            timeout=30,
            retry_count=5,
            custom_param="value",
        )
        assert client._model == "claude-3-opus-20240229"
        assert client._api_key == "custom-key"
        assert client._api_base == "https://custom-api.anthropic.com"
        assert client._timeout == 30
        assert client._kwargs["custom_param"] == "value"

    def test_get_client(self) -> None:
        """Test getting the Anthropic client instance."""
        # Test with explicit API key
        mock_instance = MagicMock()
        mock_anthropic_class = MagicMock()
        mock_anthropic_class.return_value = mock_instance
        mock_anthropic_module = MagicMock(Anthropic=mock_anthropic_class)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            client = AnthropicClient(api_key="test-key")
            result = client._get_client()

            # Verify that the returned client is our mock_instance
            assert result == mock_instance
            mock_anthropic_class.assert_called_once_with(api_key="test-key")

            # Should cache the client
            assert client._client == mock_instance

            # Second call should use cached client
            client._get_client()
            assert mock_anthropic_class.call_count == 1

        # Test with API key from environment
        mock_instance = MagicMock()
        mock_anthropic_class = MagicMock()
        mock_anthropic_class.return_value = mock_instance
        mock_anthropic_module = MagicMock(Anthropic=mock_anthropic_class)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
                client = AnthropicClient()
                client._get_client()
                mock_anthropic_class.assert_called_once_with(api_key="env-key")

        # Test with additional parameters
        mock_instance = MagicMock()
        mock_anthropic_class = MagicMock()
        mock_anthropic_class.return_value = mock_instance
        mock_anthropic_module = MagicMock(Anthropic=mock_anthropic_class)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            client = AnthropicClient(
                api_key="test-key",
                api_base="https://custom-api.anthropic.com",
            )
            client._get_client()
            mock_anthropic_class.assert_called_once_with(
                api_key="test-key",
                base_url="https://custom-api.anthropic.com",
            )

        # Test import error by removing anthropic from sys.modules
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(QuackIntegrationError) as excinfo:
                client = AnthropicClient(api_key="test-key")
                client._get_client()
            assert "Anthropic package not installed" in str(excinfo.value)

    def test_get_api_key_from_env(self) -> None:
        """Test getting the API key from environment variables."""
        # Test with API key in environment
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            client = AnthropicClient()
            api_key = client._get_api_key_from_env()

            assert api_key == "env-key"

        # Test without API key in environment
        with patch.dict(os.environ, {}, clear=True):
            client = AnthropicClient()

            with pytest.raises(QuackIntegrationError) as excinfo:
                client._get_api_key_from_env()

            assert "Anthropic API key not provided" in str(excinfo.value)

    def test_model_property(self) -> None:
        """Test the model property."""
        # Test with specified model
        client = AnthropicClient(model="claude-3-sonnet-20240229")
        assert client.model == "claude-3-sonnet-20240229"

        # Test with default model
        client = AnthropicClient()
        assert client.model == "claude-3-opus-20240229"

    def test_convert_message_to_anthropic(self) -> None:
        """Test converting ChatMessage to Anthropic format."""
        client = AnthropicClient()

        # Test with user message
        message = ChatMessage(role=RoleType.USER, content="User message")
        anthropic_message = client._convert_message_to_anthropic(message)

        assert anthropic_message == {"role": "user", "content": "User message"}

        # Test with assistant message
        message = ChatMessage(role=RoleType.ASSISTANT, content="Assistant message")
        anthropic_message = client._convert_message_to_anthropic(message)

        assert anthropic_message == {
            "role": "assistant",
            "content": "Assistant message",
        }

        # Test with empty content
        message = ChatMessage(role=RoleType.USER, content=None)
        anthropic_message = client._convert_message_to_anthropic(message)

        assert anthropic_message == {"role": "user", "content": ""}

    def test_convert_error(self) -> None:
        """Test converting Anthropic errors to QuackApiError."""
        client = AnthropicClient()

        # Use MockAnthropicErrorResponse to create test errors
        rate_limit_error = MockAnthropicErrorResponse(
            message="Rate limit exceeded", type="rate_limit_error", status_code=429
        ).to_exception()

        api_error = client._convert_error(rate_limit_error)
        assert isinstance(api_error, QuackApiError)
        assert "Anthropic rate limit exceeded" in str(api_error)
        assert api_error.service == "Anthropic"
        assert api_error.api_method == "messages.create"

        # Test invalid API key error
        invalid_key_error = MockAnthropicErrorResponse(
            message="Invalid API key provided",
            type="authentication_error",
            status_code=401,
        ).to_exception()

        api_error = client._convert_error(invalid_key_error)
        assert "Invalid Anthropic API key" in str(api_error)

        # Test insufficient quota error
        quota_error = MockAnthropicErrorResponse(
            message="Insufficient quota", type="quota_error", status_code=402
        ).to_exception()

        api_error = client._convert_error(quota_error)
        assert "Insufficient Anthropic quota" in str(api_error)

        # Test generic error
        generic_error = MockAnthropicErrorResponse(
            message="Some other error", type="api_error", status_code=500
        ).to_exception()

        api_error = client._convert_error(generic_error)
        assert "Anthropic API error" in str(api_error)

    def test_chat_with_provider(self, anthropic_client: AnthropicClient) -> None:
        """Test the Anthropic-specific chat implementation."""
        # Set up messages and options
        messages = [
            ChatMessage(role=RoleType.SYSTEM, content="System message"),
            ChatMessage(role=RoleType.USER, content="User message"),
        ]
        options = LLMOptions(temperature=0.5, max_tokens=100, top_p=0.8)

        # Use MockAnthropicResponse for non-streaming response
        mock_response = MockAnthropicResponse(
            content="Response content", model="claude-3-opus-20240229"
        )

        # Test normal completion
        with patch.object(anthropic_client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = anthropic_client._chat_with_provider(messages, options)

            assert result.success is True
            assert result.content == "Response content"

            # Verify Anthropic was called correctly
            mock_client.messages.create.assert_called_once_with(
                model="claude-3-opus-20240229",
                messages=[{"role": "user", "content": "User message"}],
                system="System message",
                max_tokens=100,
                temperature=0.5,
                top_p=0.8,
            )

        # Test with streaming
        callback = MagicMock()
        streaming_options = LLMOptions(temperature=0.5, max_tokens=100, stream=True)

        # Use MockAnthropicStreamingResponse for streaming
        mock_stream = MockAnthropicStreamingResponse(
            content="Hello world!", model="claude-3-opus-20240229"
        )

        with patch.object(anthropic_client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.stream.return_value = mock_stream
            mock_get_client.return_value = mock_client

            result = anthropic_client._chat_with_provider(
                messages, streaming_options, callback
            )

            assert result.success is True
            assert result.content == "Hello world!"

            # Verify Anthropic streaming was called correctly
            mock_client.messages.stream.assert_called_once()
            assert (
                mock_client.messages.stream.call_args[1]["model"]
                == "claude-3-opus-20240229"
            )
            assert mock_client.messages.stream.call_args[1]["stream"] is True

        # Test with API error
        with patch.object(anthropic_client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            error_response = MockAnthropicErrorResponse(
                message="API error", type="server_error", status_code=500
            ).to_exception()
            mock_client.messages.create.side_effect = error_response
            mock_get_client.return_value = mock_client

            with pytest.raises(QuackApiError) as excinfo:
                anthropic_client._chat_with_provider(messages, options)

            assert "Anthropic API error" in str(excinfo.value)

        # Test with import error
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(QuackIntegrationError) as excinfo:
                anthropic_client._chat_with_provider(messages, options)

            assert "Failed to import Anthropic package" in str(excinfo.value)

    def test_count_tokens_with_provider(
        self, anthropic_client: AnthropicClient
    ) -> None:
        """Test the Anthropic-specific token counting implementation."""
        # Set up messages
        messages = [
            ChatMessage(role=RoleType.SYSTEM, content="System message"),
            ChatMessage(role=RoleType.USER, content="User message"),
        ]

        # Use MockAnthropicClient's count_tokens method
        mock_client = MockAnthropicClient(token_counts=[40])

        with patch.object(anthropic_client, "_get_client", return_value=mock_client):
            # Test token counting with Anthropic API
            result = anthropic_client._count_tokens_with_provider(messages)

            assert result.success is True
            assert result.content == 40

            # Verify the mock client was called with the right parameters
            assert mock_client.count_tokens_call_count == 1

        # Test when token counting API is not available
        with patch.object(anthropic_client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.count_tokens.side_effect = AttributeError("No such method")
            mock_get_client.return_value = mock_client

            with patch("logging.Logger.warning") as mock_warning:
                result = anthropic_client._count_tokens_with_provider(messages)

                assert result.success is True
                # Should use simple estimation
                assert result.content > 0
                assert "Token count is an estimation" in result.message

                # Should log a warning
                mock_warning.assert_called_once()
                assert (
                    "Anthropic token counting API not available"
                    in mock_warning.call_args[0][0]
                )

        # Test with general error
        with patch.object(anthropic_client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.count_tokens.side_effect = Exception("Counting error")
            mock_get_client.return_value = mock_client

            result = anthropic_client._count_tokens_with_provider(messages)

            assert result.success is False
            assert "Error counting tokens" in result.error

    def test_handle_streaming(self) -> None:
        """Test handling streaming responses."""
        client = AnthropicClient()

        # Set up test parameters
        system = "System prompt"
        messages = [{"role": "user", "content": "Test message"}]
        params = {"temperature": 0.7}
        callback = MagicMock()

        # Use MockAnthropicStreamingResponse
        mock_stream = MockAnthropicStreamingResponse(
            content="Hello world!",
            model="claude-3-opus-20240229",
            chunk_size=2,  # Split into smaller chunks for testing
        )

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream

        # Test streaming
        result = client._handle_streaming(
            mock_client, "claude-3-opus-20240229", system, messages, params, callback
        )

        assert result == "Hello world!"
        assert callback.call_count > 0

        # Verify stream was called with correct parameters
        mock_client.messages.stream.assert_called_once_with(
            model="claude-3-opus-20240229",
            messages=messages,
            system=system,
            stream=True,
            **params,
        )

        # Test with error during streaming
        error = MockAnthropicErrorResponse(
            message="Streaming error", type="server_error", status_code=500
        ).to_exception()

        mock_client.messages.stream.side_effect = error

        with pytest.raises(QuackApiError) as excinfo:
            client._handle_streaming(
                mock_client,
                "claude-3-opus-20240229",
                system,
                messages,
                params,
                callback,
            )

        assert "Anthropic API error: Streaming error" in str(excinfo.value)
