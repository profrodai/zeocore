# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/clients/test_openai.py
# role: tests
# neighbors: __init__.py, test_anthropic.py, test_base.py, test_clients.py, test_mock.py, test_ollama.py
# exports: TestOpenAIClient
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===

"""
Tests for the OpenAI LLM client.

This module tests the OpenAI-specific client implementation, including
authentication, API interactions, and error handling.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.llms.clients.openai import OpenAIClient
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType
from quack_core.core.errors import QuackApiError, QuackIntegrationError

from tests.test_integrations.llms.mocks.openai import (
    MockOpenAIClient,
    MockOpenAIErrorResponse,
    MockOpenAIResponse,
    MockOpenAIStreamingResponse,
)


class TestOpenAIClient:
    """Tests for the OpenAI LLM client."""

    @pytest.fixture
    def openai_client(self) -> OpenAIClient:
        """Create an OpenAI client with test API key."""
        return OpenAIClient(model="gpt-4o", api_key="test-key")  # Add api_key here

    def test_init(self) -> None:
        """Test initializing the OpenAI client."""
        # Test with default parameters
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = OpenAIClient()
            assert client._model is None  # Will use default if not specified
            assert client._api_key is None  # Will get from env
            assert client._api_base is None
            assert client._organization is None
            assert client._timeout == 60
            assert client._client is None

        # Test with custom parameters
        client = OpenAIClient(
            model="gpt-4o",
            api_key="custom-key",
            api_base="https://custom-api.openai.com/v1",
            organization="org-123",
            timeout=30,
            retry_count=5,
            custom_param="value",
        )
        assert client._model == "gpt-4o"
        assert client._api_key == "custom-key"
        assert client._api_base == "https://custom-api.openai.com/v1"
        assert client._organization == "org-123"
        assert client._timeout == 30
        assert client._kwargs["custom_param"] == "value"

    def test_get_client(self) -> None:
        """Test getting the OpenAI client instance."""
        # Test with explicit API key
        with patch("openai.OpenAI") as mock_openai:
            mock_instance = MagicMock()
            mock_openai.return_value = mock_instance

            client = OpenAIClient(api_key="test-key")
            result = client._get_client()

            assert result == mock_instance
            mock_openai.assert_called_once_with(api_key="test-key", timeout=60)

            # Should cache the client
            assert client._client == mock_instance

            # Second call should use cached client
            client._get_client()
            assert mock_openai.call_count == 1

        # Test with API key from environment
        with patch("openai.OpenAI") as mock_openai:
            with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
                client = OpenAIClient()
                client._get_client()

                mock_openai.assert_called_once_with(api_key="env-key", timeout=60)

        # Test with additional parameters
        with patch("openai.OpenAI") as mock_openai:
            client = OpenAIClient(
                api_key="test-key",
                api_base="https://custom-api.openai.com/v1",
                organization="org-123",
            )
            client._get_client()

            mock_openai.assert_called_once_with(
                api_key="test-key",
                timeout=60,
                base_url="https://custom-api.openai.com/v1",
                organization="org-123",
            )

        # Test import error
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(QuackIntegrationError) as excinfo:
                client = OpenAIClient(api_key="test-key")
                client._get_client()

            assert "OpenAI package not installed" in str(excinfo.value)

    def test_get_api_key_from_env(self) -> None:
        """Test getting the API key from environment variables."""
        # Test with API key in environment
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            client = OpenAIClient()
            api_key = client._get_api_key_from_env()

            assert api_key == "env-key"

        # Test without API key in environment
        with patch.dict(os.environ, {}, clear=True):
            client = OpenAIClient()

            with pytest.raises(QuackIntegrationError) as excinfo:
                client._get_api_key_from_env()

            assert "OpenAI API key not provided" in str(excinfo.value)

    def test_model_property(self) -> None:
        """Test the model property."""
        # Test with specified model
        client = OpenAIClient(model="gpt-4o-mini")
        assert client.model == "gpt-4o-mini"

        # Test with default model
        client = OpenAIClient()
        assert client.model == "gpt-4o"

    def test_convert_message_to_openai(self) -> None:
        """Test converting ChatMessage to OpenAI format."""
        client = OpenAIClient()

        # Test with basic message
        message = ChatMessage(role=RoleType.USER, content="User message")
        openai_message = client._convert_message_to_openai(message)

        assert openai_message == {"role": "user", "content": "User message"}

        # Test with system message
        message = ChatMessage(role=RoleType.SYSTEM, content="System message")
        openai_message = client._convert_message_to_openai(message)

        assert openai_message == {"role": "system", "content": "System message"}

        # Test with empty content
        message = ChatMessage(role=RoleType.ASSISTANT, content=None)
        openai_message = client._convert_message_to_openai(message)

        assert openai_message == {"role": "assistant"}

        # Test with name
        message = ChatMessage(
            role=RoleType.FUNCTION, content="Function result", name="get_weather"
        )
        openai_message = client._convert_message_to_openai(message)

        assert openai_message == {
            "role": "function",
            "content": "Function result",
            "name": "get_weather",
        }

        # Test with function call
        message = ChatMessage(
            role=RoleType.ASSISTANT,
            content=None,
            function_call={
                "name": "get_weather",
                "arguments": '{"location": "San Francisco"}',
            },
        )
        openai_message = client._convert_message_to_openai(message)

        assert openai_message == {
            "role": "assistant",
            "function_call": {
                "name": "get_weather",
                "arguments": '{"location": "San Francisco"}',
            },
        }

        # Test with tool calls
        message = ChatMessage(
            role=RoleType.ASSISTANT,
            content=None,
            tool_calls=[
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "London"}',
                    },
                }
            ],
        )
        openai_message = client._convert_message_to_openai(message)

        assert openai_message == {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "London"}',
                    },
                }
            ],
        }

    def test_process_response(self) -> None:
        """Test processing OpenAI responses."""
        client = OpenAIClient()

        # Test with mock OpenAI response
        mock_response = MockOpenAIResponse(content="Response content", model="gpt-4o")
        openai_format = mock_response.to_openai_format()

        result = client._process_response(openai_format)
        assert result == "Response content"

        # Test with empty choices
        empty_response = MagicMock()
        empty_response.choices = []
        result = client._process_response(empty_response)
        assert result == ""

        # Test with missing message attribute
        invalid_response = MagicMock()
        invalid_response.choices = [MagicMock()]
        delattr(invalid_response.choices[0], "message")
        result = client._process_response(invalid_response)
        assert result == ""

        # Test with None content
        none_content_response = MagicMock()
        none_content_response.choices = [MagicMock(message=MagicMock(content=None))]
        result = client._process_response(none_content_response)
        assert result == ""

    def test_convert_error(self) -> None:
        """Test converting OpenAI errors to QuackApiError."""
        client = OpenAIClient()

        # Test with mock OpenAI error responses
        rate_limit_error = MockOpenAIErrorResponse(
            message="Rate limit exceeded", code="rate_limit_exceeded", status_code=429
        ).to_exception()

        api_error = client._convert_error(rate_limit_error)
        assert isinstance(api_error, QuackApiError)
        assert "OpenAI rate limit exceeded" in str(api_error)
        assert api_error.service == "OpenAI"
        assert api_error.api_method == "chat.completions.create"

        # Test invalid API key error
        auth_error = MockOpenAIErrorResponse(
            message="Invalid API key provided", code="invalid_api_key", status_code=401
        ).to_exception()

        api_error = client._convert_error(auth_error)
        assert "Invalid OpenAI API key" in str(api_error)

        # Test insufficient quota error
        quota_error = MockOpenAIErrorResponse(
            message="Insufficient quota", code="insufficient_quota", status_code=402
        ).to_exception()

        api_error = client._convert_error(quota_error)
        assert "Insufficient OpenAI quota" in str(api_error)

        # Test generic error
        generic_error = MockOpenAIErrorResponse(
            message="Some other error", code="server_error", status_code=500
        ).to_exception()

        api_error = client._convert_error(generic_error)
        assert "OpenAI API error" in str(api_error)

    def test_chat_with_provider_using_mock_client(self) -> None:
        """Test the OpenAI chat implementation using mock client."""
        # Create a mock client with predefined responses
        mock_client = MockOpenAIClient(
            responses=["Test response", "Second response"], model="gpt-4o"
        )

        # Set up messages and options
        messages = [ChatMessage(role=RoleType.USER, content="User message")]
        options = LLMOptions(temperature=0.5, max_tokens=100)

        # Create OpenAI client with the mock
        client = OpenAIClient(model="gpt-4o")

        # Replace the _get_client method to return our mock
        with patch.object(client, "_get_client", return_value=mock_client):
            # Test normal completion
            result = client._chat_with_provider(messages, options)

            assert result.success is True
            assert result.content == "Test response"

            # Verify our mock was called correctly
            assert len(mock_client.openai_requests) == 1
            assert mock_client.openai_requests[0]["model"] == "gpt-4o"
            assert mock_client.openai_requests[0]["temperature"] == 0.5
            assert mock_client.openai_requests[0]["max_tokens"] == 100

            # Test another chat call - should get second response
            result = client._chat_with_provider(messages, options)
            assert result.content == "Second response"

            # Test with error
            mock_error = MockOpenAIErrorResponse(
                message="API error", code="server_error", status_code=500
            ).to_exception()

            error_client = MockOpenAIClient(
                responses=["Shouldn't reach this"], errors=[mock_error]
            )

            with patch.object(client, "_get_client", return_value=error_client):
                with pytest.raises(QuackApiError) as excinfo:
                    client._chat_with_provider(messages, options)

                assert "OpenAI API error" in str(excinfo.value)

    @patch("openai.OpenAI")
    def test_chat_with_provider(
        self, mock_openai: MagicMock, openai_client: OpenAIClient
    ) -> None:
        """Test the OpenAI-specific chat implementation with standard mocks."""
        # Set up mock OpenAI client
        mock_instance = MagicMock()
        mock_openai.return_value = mock_instance

        # Use our MockOpenAIResponse for a better structured response
        mock_response = MockOpenAIResponse(
            content="Response content",
            model="gpt-4o",
            usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        )

        mock_instance.chat.completions.create.return_value = (
            mock_response.to_openai_format()
        )

        # Set up messages and options
        messages = [ChatMessage(role=RoleType.USER, content="User message")]
        options = LLMOptions(temperature=0.5, max_tokens=100)

        # Test normal completion
        result = openai_client._chat_with_provider(messages, options)

        assert result.success is True
        assert result.content == "Response content"

        # Verify OpenAI was called correctly
        mock_instance.chat.completions.create.assert_called_once_with(
            model="gpt-4o",
            messages=[{"role": "user", "content": "User message"}],
            temperature=0.5,
            max_tokens=100,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )

        # Test with streaming
        mock_instance.chat.completions.create.reset_mock()
        callback = MagicMock()
        options.stream = True

        # Set up streaming response
        mock_stream = MockOpenAIStreamingResponse(
            content="Streaming response", model="gpt-4o"
        )
        mock_instance.chat.completions.create.return_value = mock_stream

        result = openai_client._chat_with_provider(messages, options, callback)

        assert result.success is True
        assert "Streaming response" in result.content

        # Verify OpenAI was called with stream=True
        mock_instance.chat.completions.create.assert_called_once()
        assert mock_instance.chat.completions.create.call_args[1]["stream"] is True

        # Test with API error using our mock error response
        mock_instance.chat.completions.create.reset_mock()
        mock_error = MockOpenAIErrorResponse(
            message="API error", code="server_error", status_code=500
        ).to_exception()

        mock_instance.chat.completions.create.side_effect = mock_error

        with pytest.raises(QuackApiError) as excinfo:
            openai_client._chat_with_provider(messages, options)

        assert "OpenAI API error" in str(excinfo.value)

        # Test with import error
        with patch.object(openai_client, "_get_client") as mock_get_client:
            mock_get_client.side_effect = QuackIntegrationError(
                "Failed to import OpenAI package: No module named 'openai'"
            )

            with pytest.raises(QuackIntegrationError) as excinfo:
                openai_client._chat_with_provider(messages, options)

            assert "Failed to import OpenAI package" in str(excinfo.value)

    @patch("tiktoken.encoding_for_model")
    def test_count_tokens_with_provider(
        self, mock_tiktoken: MagicMock, openai_client: OpenAIClient
    ) -> None:
        """Test the OpenAI-specific token counting implementation."""
        # Set up mock encoding
        mock_encoding = MagicMock()
        mock_tiktoken.return_value = mock_encoding

        # Configure encode method to return a token array of specific length
        def mock_encode(text):
            # Return an array with one "token" per character for simplicity
            return [i for i in range(len(text))]

        mock_encoding.encode.side_effect = mock_encode

        # Set up messages
        messages = [
            ChatMessage(role=RoleType.SYSTEM, content="System message"),
            ChatMessage(role=RoleType.USER, content="User message"),
        ]

        # Test token counting with tiktoken
        result = openai_client._count_tokens_with_provider(messages)

        assert result.success is True
        # 3 tokens per message + content length + 3 for assistant reply
        expected_tokens = (3 * 2) + len("System message") + len("User message") + 3
        assert result.content == expected_tokens

        # Verify tiktoken was used correctly
        mock_tiktoken.assert_called_once_with("gpt-4o")

        # Test with model-specific encoding error
        mock_tiktoken.reset_mock()
        mock_tiktoken.side_effect = KeyError("Model not found")

        with patch("tiktoken.get_encoding") as mock_get_encoding:
            mock_get_encoding.return_value = mock_encoding
            result = openai_client._count_tokens_with_provider(messages)

            assert result.success is True
            assert result.content == expected_tokens

            # Should fall back to cl100k_base encoding
            mock_get_encoding.assert_called_once_with("cl100k_base")

        # Test with tiktoken import error
        with patch.dict("sys.modules", {"tiktoken": None}):
            with patch("logging.Logger.warning") as mock_warning:
                result = openai_client._count_tokens_with_provider(messages)

                assert result.success is True
                # Should use simple estimation
                assert result.content > 0
                assert "using simple token estimation" in result.message.lower()

                # Should log a warning
                mock_warning.assert_called_once()
                assert "tiktoken not installed" in mock_warning.call_args[0][0]

        # Test with general error
        with patch(
            "tiktoken.encoding_for_model", side_effect=Exception("Counting error")
        ):
            result = openai_client._count_tokens_with_provider(messages)

            assert result.success is False
            assert "Error counting tokens" in result.error

    def test_handle_streaming(self) -> None:
        """Test handling streaming responses."""
        client = OpenAIClient()

        # Set up test parameters
        callback = MagicMock()
        messages = [{"role": "user", "content": "Test message"}]
        params = {"temperature": 0.7}

        # Use MockOpenAIStreamingResponse for better testing
        streaming_content = "Hello world!"
        mock_stream = MockOpenAIStreamingResponse(
            content=streaming_content,
            model="gpt-4o",
            chunk_size=2,  # Split into smaller chunks for testing
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_stream

        # Test streaming
        result = client._handle_streaming(
            mock_client, "gpt-4o", messages, params, callback
        )

        assert result == streaming_content
        # Should have multiple callback calls based on chunk size
        assert callback.call_count > 0

        # Verify create was called with stream=True
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o", messages=messages, stream=True, **params
        )

        # Test with error during streaming
        mock_error = MockOpenAIErrorResponse(
            message="Streaming error", code="server_error", status_code=500
        ).to_exception()

        mock_client.chat.completions.create.side_effect = mock_error

        with pytest.raises(QuackApiError) as excinfo:
            client._handle_streaming(mock_client, "gpt-4o", messages, params, callback)

        assert "OpenAI API error: Streaming error" in str(excinfo.value)

        # Test with empty choices
        mock_client.chat.completions.create.side_effect = None
        mock_client.chat.completions.create.return_value = [MagicMock(choices=[])]

        result = client._handle_streaming(
            mock_client, "gpt-4o", messages, params, callback
        )
        assert result == ""
