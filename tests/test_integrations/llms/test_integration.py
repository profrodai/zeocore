# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/test_integration.py
# role: tests
# neighbors: __init__.py, test_config.py, test_config_provider.py, test_fallback.py, test_llms.py, test_models.py (+3 more)
# exports: TestLLMIntegration
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
Integration tests for the LLM module.

This module tests the integration between different components of the LLM module,
ensuring they work together properly in real-world scenarios.
"""

from unittest.mock import MagicMock, patch

import pytest

from quack_core.integrations.llms import (
    ChatMessage,
    LLMOptions,
    create_integration,
    get_llm_client,
    get_mock_llm,
)
from quack_core.integrations.llms.clients import AnthropicClient, OpenAIClient


class TestLLMIntegration:
    """Integration tests for the LLM module."""

    def test_create_integration(self) -> None:
        """Test the create_integration factory function."""
        with patch(
            "quack_core.integrations.llms.service.LLMIntegration"
        ) as mock_service:
            # Create a simple mock that matches what create_integration returns
            mock_instance = MagicMock()
            mock_instance.name = "LLM"
            mock_instance.version = "1.0.0"
            mock_instance.initialize.return_value = MagicMock()

            # Configure the mock to return our instance
            mock_service.return_value = mock_instance

            integration = create_integration()

            assert integration == mock_instance
            mock_service.assert_called_once()

            # Check integration protocol - use duck typing instead of isinstance
            assert hasattr(integration, "name")
            assert hasattr(integration, "version")
            assert hasattr(integration, "initialize")

    def test_get_mock_llm(self) -> None:
        """Test the get_mock_llm helper function."""
        # Test with default parameters
        client = get_mock_llm()
        assert client._script == ["This is a mock response from the LLM."]

        # Test with custom script
        custom_script = ["Response 1", "Response 2"]
        client = get_mock_llm(custom_script)
        assert client._script == custom_script

    def test_chat_workflow(self) -> None:
        """Test a complete chat workflow with a mock client."""
        # Get a mock client
        client = get_mock_llm(["Hello, I'm a mock LLM!"])

        # Create messages
        messages = [
            ChatMessage.from_dict(
                {"role": "system", "content": "Be helpful and polite."}
            ),
            ChatMessage.from_dict(
                {"role": "user", "content": "Tell me about yourself."}
            ),
        ]

        # Create options
        options = LLMOptions(temperature=0.7, max_tokens=100)

        # Send a chat request
        result = client.chat(messages, options)

        # Verify the result
        assert result.success is True
        assert result.content == "Hello, I'm a mock LLM!"

        # Count tokens
        token_result = client.count_tokens(messages)

        # Verify token count
        assert token_result.success is True
        assert token_result.content > 0

    @pytest.mark.integration
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_openai_client_creation(self) -> None:
        """Test creating an OpenAI client (mock the actual API calls)."""
        with patch("openai.OpenAI"):
            # Get an OpenAI client
            client = get_llm_client(provider="openai", model="gpt-4o")

            # Verify it's the right type
            assert isinstance(client, OpenAIClient)
            assert client.model == "gpt-4o"

    @pytest.mark.integration
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_anthropic_client_creation(self) -> None:
        """Test creating an Anthropic client (mock the actual API calls)."""
        with patch("anthropic.Anthropic"):
            # Get an Anthropic client
            client = get_llm_client(
                provider="anthropic", model="claude-3-opus-20240229"
            )

            # Verify it's the right type
            assert isinstance(client, AnthropicClient)
            assert client.model == "claude-3-opus-20240229"

    @pytest.mark.integration
    def test_module_imports(self) -> None:
        """Test all expected imports are available at module level."""
        # Import the module
        import quack_core.integrations.llms as llms

        # Check important classes
        assert hasattr(llms, "LLMClient")
        assert hasattr(llms, "OpenAIClient")
        assert hasattr(llms, "MockLLMClient")

        # Check models
        assert hasattr(llms, "ChatMessage")
        assert hasattr(llms, "LLMOptions")
        assert hasattr(llms, "FunctionCall")
        assert hasattr(llms, "ToolCall")

        # Check config
        assert hasattr(llms, "LLMConfig")
        assert hasattr(llms, "LLMConfigProvider")

        # Check protocols
        assert hasattr(llms, "LLMProviderProtocol")

        # Check functions
        assert hasattr(llms, "get_llm_client")
        assert hasattr(llms, "register_llm_client")
        assert hasattr(llms, "create_integration")
        assert hasattr(llms, "get_mock_llm")
