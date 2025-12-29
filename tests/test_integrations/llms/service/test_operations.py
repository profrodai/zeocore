# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/service/test_operations.py
# role: service
# neighbors: __init__.py, test_dependencies.py, test_initialization.py, test_integration.py
# exports: TestLLMOperationsComplete
# git_branch: refactor/toolkitWorkflow
# git_commit: e4fa88d
# === QV-LLM:END ===

"""
Comprehensive tests for LLM service _operations.

This module provides complete test coverage for the service/_operations.py file,
which contains the chat and token counting _operations.
"""

from unittest.mock import MagicMock

import pytest

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType
from quack_core.integrations.llms.service.operations import (
    chat,
    count_tokens,
    get_provider_status,
    reset_provider_status,
)


class TestLLMOperationsComplete:
    """Comprehensive tests for LLM _operations."""

    @pytest.fixture
    def mock_integration(self) -> MagicMock:
        """Create a mock LLM integration."""
        integration = MagicMock()
        integration._initialized = True
        integration.client = MagicMock()
        integration._using_mock = False
        integration._ensure_initialized.return_value = None  # No error
        return integration

    @pytest.fixture
    def mock_uninitialized_integration(self) -> MagicMock:
        """Create a mock uninitialized LLM integration."""
        integration = MagicMock()
        integration._initialized = False
        integration.client = None
        integration._using_mock = False
        integration._ensure_initialized.return_value = IntegrationResult(
            success=False, error="Not initialized"
        )
        return integration

    def test_chat_success(self, mock_integration: MagicMock) -> None:
        """Test successful chat operation."""
        # Set up mock client's chat method
        mock_integration.client.chat.return_value = IntegrationResult(
            success=True, content="Response"
        )

        # Call chat operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]
        options = LLMOptions(temperature=0.5)
        callback = MagicMock()

        result = chat(mock_integration, messages, options, callback)

        assert result.success is True
        assert result.content == "Response"

        # Verify client method was called
        mock_integration.client.chat.assert_called_once_with(
            messages, options, callback
        )

    def test_chat_not_initialized(
        self, mock_uninitialized_integration: MagicMock
    ) -> None:
        """Test chat operation when not initialized."""
        # Call chat operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = chat(mock_uninitialized_integration, messages)

        assert result.success is False
        assert result.error == "Not initialized"

        # Verify ensure_initialized was called
        mock_uninitialized_integration._ensure_initialized.assert_called_once()
        # Don't try to use assert_not_called on a property path that doesn't exist
        assert mock_uninitialized_integration.client is None

    def test_chat_no_client(self, mock_integration: MagicMock) -> None:
        """Test chat operation with no client."""
        # Set client to None
        mock_integration.client = None

        # Call chat operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = chat(mock_integration, messages)

        assert result.success is False
        assert "LLM client not initialized" in result.error

    def test_chat_with_mock(self, mock_integration: MagicMock) -> None:
        """Test chat operation with mock client."""
        # Set using mock flag
        mock_integration._using_mock = True
        mock_integration.client.chat.return_value = IntegrationResult(
            success=True, content="Mock response"
        )

        # Call chat operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = chat(mock_integration, messages)

        assert result.success is True
        assert result.content == "Mock response"
        assert "using mock LLM" in result.message

    def test_chat_failure(self, mock_integration: MagicMock) -> None:
        """Test chat operation handling errors from client."""
        # Set up mock client's chat method to return an error
        mock_integration.client.chat.return_value = IntegrationResult(
            success=False, error="API error"
        )

        # Call chat operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = chat(mock_integration, messages)

        assert result.success is False
        assert result.error == "API error"

        # Verify client method was called
        mock_integration.client.chat.assert_called_once()

    def test_count_tokens_success(self, mock_integration: MagicMock) -> None:
        """Test successful token counting operation."""
        # Set up mock client's count_tokens method
        mock_integration.client.count_tokens.return_value = IntegrationResult(
            success=True, content=42
        )

        # Call count_tokens operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = count_tokens(mock_integration, messages)

        assert result.success is True
        assert result.content == 42

        # Verify client method was called
        mock_integration.client.count_tokens.assert_called_once_with(messages)

    def test_count_tokens_not_initialized(
        self, mock_uninitialized_integration: MagicMock
    ) -> None:
        """Test count_tokens operation when not initialized."""
        # Reset the mock so it's only called once in this test
        mock_uninitialized_integration._ensure_initialized.reset_mock()

        # Call count_tokens operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = count_tokens(mock_uninitialized_integration, messages)

        assert result.success is False
        assert result.error == "Not initialized"

        # Verify ensure_initialized was called
        mock_uninitialized_integration._ensure_initialized.assert_called_once()
        assert mock_uninitialized_integration.client is None

    def test_count_tokens_no_client(self, mock_integration: MagicMock) -> None:
        """Test count_tokens operation with no client."""
        # Set client to None
        mock_integration.client = None

        # Call count_tokens operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = count_tokens(mock_integration, messages)

        assert result.success is False
        assert "LLM client not initialized" in result.error

    def test_count_tokens_with_mock(self, mock_integration: MagicMock) -> None:
        """Test count_tokens operation with mock client."""
        # Set using mock flag
        mock_integration._using_mock = True
        mock_integration.client.count_tokens.return_value = IntegrationResult(
            success=True, content=42
        )

        # Call count_tokens operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = count_tokens(mock_integration, messages)

        assert result.success is True
        assert result.content == 42
        assert "using mock estimation" in result.message

    def test_count_tokens_failure(self, mock_integration: MagicMock) -> None:
        """Test count_tokens operation handling errors from client."""
        # Set up mock client's count_tokens method to return an error
        mock_integration.client.count_tokens.return_value = IntegrationResult(
            success=False, error="Token counting error"
        )

        # Call count_tokens operation
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]

        result = count_tokens(mock_integration, messages)

        assert result.success is False
        assert result.error == "Token counting error"

        # Verify client method was called
        mock_integration.client.count_tokens.assert_called_once()

    def test_get_provider_status_with_fallback(
        self, mock_integration: MagicMock
    ) -> None:
        """Test get_provider_status operation with fallback client."""
        # Set up fallback client with provider status
        mock_fallback = MagicMock()
        provider_statuses = [
            MagicMock(model_dump=MagicMock(return_value={"provider": "openai"})),
            MagicMock(model_dump=MagicMock(return_value={"provider": "anthropic"})),
        ]
        mock_fallback.get_provider_status.return_value = provider_statuses
        mock_integration._fallback_client = mock_fallback

        # Call get_provider_status operation
        result = get_provider_status(mock_integration)

        assert result is not None
        assert len(result) == 2
        assert result[0]["provider"] == "openai"
        assert result[1]["provider"] == "anthropic"

        # Verify fallback client method was called
        mock_fallback.get_provider_status.assert_called_once()

    def test_get_provider_status_no_fallback(self, mock_integration: MagicMock) -> None:
        """Test get_provider_status operation with no fallback client."""
        # Set fallback client to None
        mock_integration._fallback_client = None

        # Call get_provider_status operation
        result = get_provider_status(mock_integration)

        assert result is None

    def test_reset_provider_status_with_fallback(
        self, mock_integration: MagicMock
    ) -> None:
        """Test reset_provider_status operation with fallback client."""
        # Set up fallback client
        mock_fallback = MagicMock()
        mock_integration._fallback_client = mock_fallback

        # Call reset_provider_status operation
        result = reset_provider_status(mock_integration)

        assert result is True

        # Verify fallback client method was called
        mock_fallback.reset_provider_status.assert_called_once()

    def test_reset_provider_status_no_fallback(
        self, mock_integration: MagicMock
    ) -> None:
        """Test reset_provider_status operation with no fallback client."""
        # Set fallback client to None
        mock_integration._fallback_client = None

        # Call reset_provider_status operation
        result = reset_provider_status(mock_integration)

        assert result is False

    def test_chat_with_dict_messages(self, mock_integration: MagicMock) -> None:
        """Test chat operation with dictionary messages."""
        # Set up mock client's chat method
        mock_integration.client.chat.return_value = IntegrationResult(
            success=True, content="Response"
        )

        # Call chat operation with dict messages
        dict_messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Test message"},
        ]
        options = LLMOptions(temperature=0.5)

        result = chat(mock_integration, dict_messages, options)

        assert result.success is True
        assert result.content == "Response"

        # Verify client method was called (with any arguments since we can't easily check the conversion)
        mock_integration.client.chat.assert_called_once()

    def test_count_tokens_with_dict_messages(self, mock_integration: MagicMock) -> None:
        """Test count_tokens operation with dictionary messages."""
        # Set up mock client's count_tokens method
        mock_integration.client.count_tokens.return_value = IntegrationResult(
            success=True, content=42
        )

        # Call count_tokens operation with dict messages
        dict_messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Test message"},
        ]

        result = count_tokens(mock_integration, dict_messages)

        assert result.success is True
        assert result.content == 42

        # Verify client method was called (with any arguments)
        mock_integration.client.count_tokens.assert_called_once()
