# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/test_protocols.py
# role: tests
# neighbors: __init__.py, test_config.py, test_config_provider.py, test_fallback.py, test_integration.py, test_llms.py (+3 more)
# exports: TestLLMProtocols
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
Tests for LLM protocols.

This module tests the runtime protocol implementations for LLMs, ensuring
all required methods are present and correctly implemented.
"""

from unittest.mock import MagicMock

from quack_core.integrations.core import IntegrationResult
from quack_core.integrations.llms.models import ChatMessage, LLMOptions
from quack_core.integrations.llms.protocols import LLMProviderProtocol
from tests.test_integrations.llms.mocks.clients import MockClient


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
        result = client.chat(messages, options)
        assert result.success is True

        # Call count_tokens method
        result = client.count_tokens(messages)
        assert result.success is True

        # Check model property
        assert client.model == "test-model"

    def test_incomplete_protocol_implementation(self) -> None:
        """Test that incomplete implementations don't satisfy the protocol."""
        # Create a very basic mock that won't match the protocol
        mock = MagicMock()
        assert not isinstance(mock, LLMProviderProtocol)

        # Test with a more specific implementation that has properties but not all methods
        class PartialImpl:
            @property
            def model(self):
                return "test-model"

        partial = PartialImpl()
        assert not isinstance(partial, LLMProviderProtocol)

        # Test with a complete implementation
        class CompleteImpl:
            def chat(self, messages, options=None, callback=None):
                return IntegrationResult.success_result("test")

            def count_tokens(self, messages):
                return IntegrationResult.success_result(42)

            @property
            def model(self):
                return "test-model"

        complete = CompleteImpl()
        assert isinstance(complete, LLMProviderProtocol)
