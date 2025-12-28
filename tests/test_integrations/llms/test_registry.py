# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/test_registry.py
# role: tests
# neighbors: __init__.py, test_config.py, test_config_provider.py, test_fallback.py, test_integration.py, test_llms.py (+3 more)
# exports: TestLLMRegistry
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

"""
Tests for the LLM client registry.

This module tests the registry functionality that allows dynamic loading
and management of LLM client implementations.
"""

from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackIntegrationError
from quack_core.integrations.llms.clients.base import LLMClient
from quack_core.integrations.llms.clients.mock import MockLLMClient
from quack_core.integrations.llms.registry import (
    _LLM_REGISTRY,
    get_llm_client,
    register_llm_client,
)


class TestLLMRegistry:
    """Tests for the LLM client registry."""

    def test_registry_initial_state(self) -> None:
        """Test that the registry has the expected initial state."""
        # The registry should have these providers by default
        expected_providers = {"openai", "anthropic", "mock"}
        assert set(_LLM_REGISTRY.keys()) >= expected_providers

    def test_register_llm_client(self) -> None:
        """Test registering a new LLM client."""

        # Create a test client class
        class TestClient(LLMClient):
            def _chat_with_provider(self, *args, **kwargs):
                return MagicMock()

            def _count_tokens_with_provider(self, *args, **kwargs):
                return MagicMock()

        # Register the test client
        register_llm_client("test", TestClient)

        # Check that it was added to the registry
        assert "test" in _LLM_REGISTRY
        assert _LLM_REGISTRY["test"] == TestClient

        # Clean up
        del _LLM_REGISTRY["test"]

    def test_register_llm_client_lowercase(self) -> None:
        """Test that client names are converted to lowercase in the registry."""

        # Create a test client class
        class TestClient(LLMClient):
            def _chat_with_provider(self, *args, **kwargs):
                return MagicMock()

            def _count_tokens_with_provider(self, *args, **kwargs):
                return MagicMock()

        # Register the test client with mixed case
        register_llm_client("TestClient", TestClient)

        # Check that it was added to the registry with lowercase name
        assert "testclient" in _LLM_REGISTRY
        assert _LLM_REGISTRY["testclient"] == TestClient

        # Clean up
        del _LLM_REGISTRY["testclient"]

    def test_get_llm_client_openai(self) -> None:
        """Test getting the OpenAI client."""
        with patch(
            "quack_core.integrations.llms.registry._LLM_REGISTRY"
        ) as mock_registry:
            # Create a mock client class and instance
            mock_client = MagicMock()
            mock_client_class = MagicMock(return_value=mock_client)

            # Set up the dictionary-like behavior correctly
            mock_registry.__getitem__.return_value = mock_client_class
            mock_registry.__contains__.return_value = True  # Make 'in' operator work

            # Call the function
            client = get_llm_client("openai", model="gpt-4o", api_key="test-key")

            # Verify the result
            assert client == mock_client
            mock_client_class.assert_called_once_with(
                model="gpt-4o", api_key="test-key"
            )

    def test_get_llm_client_anthropic(self) -> None:
        """Test getting the Anthropic client."""
        # Patch where the AnthropicClient is *imported* in the registry module
        with patch(
            "quack_core.integrations.llms.registry._LLM_REGISTRY"
        ) as mock_registry:
            # Create a mock client instance
            mock_instance = MagicMock()
            mock_client_class = MagicMock(return_value=mock_instance)

            # Set up the dictionary-like behavior correctly
            mock_registry.__getitem__.return_value = mock_client_class
            mock_registry.__contains__.return_value = True  # Make 'in' operator work

            # Import the real function
            from quack_core.integrations.llms.registry import get_llm_client

            # Call get_llm_client with the "anthropic" provider
            client = get_llm_client(
                "anthropic", model="claude-3-opus", api_key="test-key"
            )

            # Check if our mock was returned and the class was called with correct args
            assert client == mock_instance
            mock_client_class.assert_called_once_with(
                model="claude-3-opus", api_key="test-key"
            )

    def test_get_llm_client_mock(self) -> None:
        """Test getting the Mock client."""
        client = get_llm_client("mock", script=["Test response"])

        assert isinstance(client, MockLLMClient)
        assert client._script == ["Test response"]

    def test_get_llm_client_case_insensitive(self) -> None:
        """Test that provider names are case-insensitive."""
        with patch(
            "quack_core.integrations.llms.registry.get_llm_client", wraps=get_llm_client
        ) as mock_get_client:
            # Use a real client but patch the OpenAIClient constructor
            with patch(
                "quack_core.integrations.llms.registry._LLM_REGISTRY"
            ) as mock_registry:
                mock_client = MagicMock()
                mock_client_class = MagicMock(return_value=mock_client)
                mock_registry.__getitem__.return_value = mock_client_class
                mock_registry.__contains__.return_value = True

                # Try with mixed case
                client = get_llm_client("OpenAI", model="gpt-4o", api_key="test-key")

                assert client == mock_client
                # Verify case-insensitive lookup
                mock_registry.__getitem__.assert_called_with("openai")

    def test_get_llm_client_unknown(self) -> None:
        """Test getting an unknown client."""
        with pytest.raises(QuackIntegrationError) as excinfo:
            get_llm_client("unknown")

        assert "Unsupported LLM provider: unknown" in str(excinfo.value)
        assert "Registered providers" in str(excinfo.value)

    def test_get_llm_client_initialization_error(self) -> None:
        """Test handling client initialization errors."""
        # Use a context manager to temporarily remove items from the registry
        original_registry = _LLM_REGISTRY.copy()

        try:
            # Remove all items from registry to trigger error
            _LLM_REGISTRY.clear()

            with pytest.raises(QuackIntegrationError) as excinfo:
                get_llm_client("openai")

            assert "Unsupported LLM provider" in str(excinfo.value)
        finally:
            # Restore the registry
            _LLM_REGISTRY.update(original_registry)
