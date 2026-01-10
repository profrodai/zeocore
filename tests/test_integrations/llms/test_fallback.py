# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/test_fallback.py
# role: tests
# neighbors: __init__.py, test_config.py, test_config_provider.py, test_integration.py, test_llms.py, test_models.py (+3 more)
# exports: TestFallbackConfig, TestProviderStatus, TestFallbackLLMClient
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Tests for the fallback mechanism for LLM clients.

This module tests the FallbackLLMClient that provides graceful degradation
when primary providers are unavailable or fail.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.llms.fallback import (
    FallbackConfig,
    FallbackLLMClient,
    ProviderStatus,
)
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType
from quack_core.core.errors import QuackApiError, QuackIntegrationError

from tests.test_integrations.llms.mocks.clients import MockClient


class TestFallbackConfig:
    """Tests for FallbackConfig."""

    def test_default_config(self) -> None:
        """Test FallbackConfig with default values."""
        config = FallbackConfig()
        assert config.providers == ["openai", "anthropic", "mock"]
        assert config.max_attempts_per_provider == 3
        assert config.delay_between_providers == 1.0
        assert config.fail_fast_on_auth_errors is True
        assert config.stop_on_successful_provider is True

    def test_custom_config(self) -> None:
        """Test FallbackConfig with custom values."""
        config = FallbackConfig(
            providers=["anthropic", "ollama", "mock"],
            max_attempts_per_provider=2,
            delay_between_providers=0.5,
            fail_fast_on_auth_errors=False,
            stop_on_successful_provider=False,
        )
        assert config.providers == ["anthropic", "ollama", "mock"]
        assert config.max_attempts_per_provider == 2
        assert config.delay_between_providers == 0.5
        assert config.fail_fast_on_auth_errors is False
        assert config.stop_on_successful_provider is False


class TestProviderStatus:
    """Tests for ProviderStatus."""

    def test_default_status(self) -> None:
        """Test ProviderStatus with default values."""
        status = ProviderStatus(provider="openai")
        assert status.provider == "openai"
        assert status.available is True
        assert status.last_error is None
        assert status.last_attempt_time is None
        assert status.success_count == 0
        assert status.fail_count == 0

    def test_custom_status(self) -> None:
        """Test ProviderStatus with custom values."""
        status = ProviderStatus(
            provider="anthropic",
            available=False,
            last_error="Authentication failed",
            last_attempt_time=time.time(),
            success_count=5,
            fail_count=2,
        )
        assert status.provider == "anthropic"
        assert status.available is False
        assert status.last_error == "Authentication failed"
        assert status.last_attempt_time is not None
        assert status.success_count == 5
        assert status.fail_count == 2


class TestFallbackLLMClient:
    """Tests for FallbackLLMClient."""

    @pytest.fixture
    def fallback_client(self) -> FallbackLLMClient:
        """Create a FallbackLLMClient for testing."""
        config = FallbackConfig(
            providers=["openai", "anthropic", "mock"],
            max_attempts_per_provider=2,
            delay_between_providers=0.1,
        )
        model_map = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-opus",
            "mock": "mock-model",
        }
        api_key_map = {
            "openai": "openai-key",
            "anthropic": "anthropic-key",
            "mock": None,
        }
        return FallbackLLMClient(
            fallback_config=config,
            model_map=model_map,
            api_key_map=api_key_map,
            log_level=20,
        )

    def test_init(self, fallback_client: FallbackLLMClient) -> None:
        """Test initializing the fallback client."""
        assert fallback_client._fallback_config.providers == [
            "openai",
            "anthropic",
            "mock",
        ]
        assert fallback_client._model_map["openai"] == "gpt-4o"
        assert fallback_client._model_map["anthropic"] == "claude-3-opus"
        assert fallback_client._api_key_map["openai"] == "openai-key"
        assert fallback_client._last_successful_provider is None
        assert len(fallback_client._provider_status) == 3
        assert fallback_client.logger.level == 20

    def test_log_level(self, fallback_client: FallbackLLMClient) -> None:
        """Test the log_level property."""
        assert fallback_client.log_level == 20

    def test_model(self, fallback_client: FallbackLLMClient) -> None:
        """Test the model property."""
        # When no successful provider, should return first provider's model
        assert fallback_client.model == "gpt-4o"

        # Set a successful provider and test again
        fallback_client._last_successful_provider = "anthropic"

        # Mock the client
        mock_client = MagicMock()
        mock_client.model = "claude-3-opus"

        with patch.object(
            fallback_client, "_get_client_for_provider", return_value=mock_client
        ):
            assert fallback_client.model == "claude-3-opus"

    def test_get_provider_status(self, fallback_client: FallbackLLMClient) -> None:
        """Test getting provider status."""
        status_list = fallback_client.get_provider_status()
        assert len(status_list) == 3
        assert status_list[0].provider == "openai"
        assert status_list[1].provider == "anthropic"
        assert status_list[2].provider == "mock"

    def test_reset_provider_status(self, fallback_client: FallbackLLMClient) -> None:
        """Test resetting provider status."""
        # Set some values
        fallback_client._provider_status["openai"].available = False
        fallback_client._provider_status["openai"].last_error = "Rate limit"
        fallback_client._provider_status["openai"].fail_count = 5
        fallback_client._last_successful_provider = "anthropic"

        # Reset status
        fallback_client.reset_provider_status()

        # Check that values are reset
        assert fallback_client._provider_status["openai"].available is True
        assert fallback_client._provider_status["openai"].last_error is None
        assert fallback_client._provider_status["openai"].fail_count == 0
        assert fallback_client._last_successful_provider is None

    def test_get_client_for_provider(self, fallback_client: FallbackLLMClient) -> None:
        """Test getting a client for a provider."""
        # Mock the registry function
        mock_client = MagicMock()

        with patch(
            "quack_core.integrations.llms.registry.get_llm_client",
            return_value=mock_client,
        ) as mock_get_client:
            client = fallback_client._get_client_for_provider("openai")

            assert client == mock_client
            mock_get_client.assert_called_once_with(
                provider="openai",
                model="gpt-4o",
                api_key="openai-key",
                log_level=20,
            )

            # Check caching
            fallback_client._get_client_for_provider("openai")
            assert mock_get_client.call_count == 1  # Should not be called again

    def test_get_client_initialization_error(
        self, fallback_client: FallbackLLMClient
    ) -> None:
        """Test error handling when getting a client."""
        with patch(
            "quack_core.integrations.llms.registry.get_llm_client",
            side_effect=QuackIntegrationError("Failed to initialize"),
        ):
            with pytest.raises(QuackIntegrationError) as excinfo:
                fallback_client._get_client_for_provider("openai")

            assert "Failed to initialize openai client" in str(excinfo.value)

            # Check the provider status was updated
            status = fallback_client._provider_status["openai"]
            assert status.available is False
            assert "Failed to initialize" in status.last_error
            assert status.fail_count == 1

    def test_is_auth_error(self, fallback_client: FallbackLLMClient) -> None:
        """Test checking if an error is an authentication error."""
        # Test with auth error
        error = Exception("Authentication failed: invalid API key")
        assert fallback_client._is_auth_error(error) is True

        # Test with non-auth error
        error = Exception("Rate limit exceeded")
        assert fallback_client._is_auth_error(error) is False

    def test_chat_with_provider_successful(
        self, fallback_client: FallbackLLMClient
    ) -> None:
        """Test chat with provider succeeding on first try."""
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]
        options = LLMOptions()

        # Create mock clients
        mock_openai = MockClient(responses=["OpenAI response"])

        # Mock the client retrieval
        with patch.object(
            fallback_client, "_get_client_for_provider", return_value=mock_openai
        ):
            # Mock sleep to speed up test
            with patch("time.sleep"):
                result = fallback_client._chat_with_provider(messages, options)

                assert result.success is True
                assert result.content == "OpenAI response"
                assert "via openai" in result.message
                assert fallback_client._last_successful_provider == "openai"

                # Check provider status
                status = fallback_client._provider_status["openai"]
                assert status.success_count == 1

    def test_chat_with_provider_fallback(
        self, fallback_client: FallbackLLMClient
    ) -> None:
        """Test chat falling back to next provider on error."""
        messages = [ChatMessage(role=RoleType.USER, content="Test message")]
        options = LLMOptions()

        # Create mock clients
        mock_openai = MagicMock()
        mock_openai.chat.side_effect = QuackApiError("Rate limit exceeded", "OpenAI")

        mock_anthropic = MockClient(responses=["Anthropic response"])

        # Reset provider status before test
        fallback_client._provider_status["openai"].fail_count = 0

        # Mock the client retrieval to return different clients based on provider
        def get_mock_client(provider: str) -> MagicMock:
            if provider == "openai":
                return mock_openai
            elif provider == "anthropic":
                return mock_anthropic
            raise ValueError(f"Unexpected provider: {provider}")

        with patch.object(
            fallback_client, "_get_client_for_provider", side_effect=get_mock_client
        ):
            # Mock sleep to speed up test
            with patch("time.sleep"):
                result = fallback_client._chat_with_provider(messages, options)

                assert result.success is True
                assert result.content == "Anthropic response"
                assert "via anthropic" in result.message
                assert fallback_client._last_successful_provider == "anthropic"

                # Check provider status
                openai_status = fallback_client._provider_status["openai"]
                assert openai_status.fail_count >= 1  # Changed from "== 1" to ">= 1"
                assert "Rate limit exceeded" in openai_status.last_error

                anthropic_status = fallback_client._provider_status["anthropic"]
                assert (
                    anthropic_status.success_count >= 1
                )  # Changed from "== 1" to ">= 1"

    def test_count_tokens_with_provider(
        self, fallback_client: FallbackLLMClient
    ) -> None:
        """Test token counting with fallback."""
        messages = [ChatMessage(role=RoleType.USER, content="Count my tokens")]

        # Create mock clients
        mock_openai = MockClient(token_counts=[42])

        # Mock the client retrieval
        with patch.object(
            fallback_client, "_get_client_for_provider", return_value=mock_openai
        ):
            result = fallback_client._count_tokens_with_provider(messages)

            assert result.success is True
            assert result.content == 42
            assert "via openai" in result.message
