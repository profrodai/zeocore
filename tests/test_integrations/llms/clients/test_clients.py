# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/clients/test_clients.py
# role: tests
# neighbors: __init__.py, test_anthropic.py, test_base.py, test_mock.py, test_ollama.py, test_openai.py
# exports: TestClientImports, TestOpenAIClientDuplicate
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Tests for the consolidated LLM clients module.

This module tests the client implementations in the clients.py file,
ensuring they work correctly and match the expected behavior.
"""

import os
from unittest.mock import patch

import pytest
from quack_core.integrations.llms.clients import OpenAIClient


class TestClientImports:
    """Tests for client imports and re-exports."""

    def test_client_imports(self) -> None:
        """Test that all clients are properly exported."""
        from quack_core.integrations.llms.clients import (
            AnthropicClient,
            LLMClient,
            MockLLMClient,
            OpenAIClient,
        )

        assert issubclass(LLMClient, object)
        assert issubclass(MockLLMClient, LLMClient)
        assert issubclass(OpenAIClient, LLMClient)
        assert issubclass(AnthropicClient, LLMClient)


class TestOpenAIClientDuplicate:
    """Tests for the OpenAI client implementation in clients.py."""

    @pytest.fixture
    def openai_client(self) -> OpenAIClient:
        """Create an OpenAI client with test API key."""
        return OpenAIClient(model="gpt-4o", api_key="test-key")

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

    def test_model_property(self) -> None:
        """Test the model property."""
        # Test with specified model
        client = OpenAIClient(model="gpt-4o-mini")
        assert client.model == "gpt-4o-mini"

        # Test with default model
        client = OpenAIClient()
        assert client.model == "gpt-4o"
