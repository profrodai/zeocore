# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/__init__.py
# module: quack_core.integrations.llms.__init__
# role: module
# neighbors: models.py, protocols.py, config.py, registry.py, fallback.py
# exports: LLMClient, OpenAIClient, AnthropicClient, OllamaClient, MockLLMClient, FallbackLLMClient, LLMConfig, LLMConfigProvider (+11 more)
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
LLM integration for quack_core.

This module provides a lightweight integration with Large Language Models (LLMs),
offering a standardized interface for making chat completions across different
LLM providers.
"""

from quack_core.integrations.core.protocols import IntegrationProtocol
from quack_core.integrations.llms.clients import (
    LLMClient,
    MockLLMClient,
)
from quack_core.integrations.llms.clients.anthropic import AnthropicClient
from quack_core.integrations.llms.clients.ollama import OllamaClient
from quack_core.integrations.llms.clients.openai import OpenAIClient
from quack_core.integrations.llms.config import LLMConfig, LLMConfigProvider
from quack_core.integrations.llms.fallback import FallbackConfig, FallbackLLMClient
from quack_core.integrations.llms.models import (
    ChatMessage,
    FunctionCall,
    LLMOptions,
    RoleType,
    ToolCall,
)
from quack_core.integrations.llms.protocols import LLMProviderProtocol
from quack_core.integrations.llms.registry import (
    get_llm_client,
    register_llm_client,
)

# Register the FallbackLLMClient after importing both modules
register_llm_client("fallback", FallbackLLMClient)

__all__ = [
    # Main client classes
    "LLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "OllamaClient",
    "MockLLMClient",
    "FallbackLLMClient",
    # Configuration
    "LLMConfig",
    "LLMConfigProvider",
    "FallbackConfig",
    # Models
    "ChatMessage",
    "FunctionCall",
    "LLMOptions",
    "ToolCall",
    "RoleType",
    # Protocols
    "LLMProviderProtocol",
    # Registry
    "get_llm_client",
    "register_llm_client",
    # Factory function for integration discovery
    "create_integration",
    # Module
    "get_mock_llm",
]


def create_integration() -> IntegrationProtocol:
    """
    Create and return an LLM integration instance.

    This function is used as an entry point for automatic integration discovery.

    Returns:
        IntegrationProtocol: Configured LLM integration
    """
    from quack_core.integrations.llms.service import LLMIntegration

    return LLMIntegration()


def get_mock_llm(script: list[str] | None = None) -> MockLLMClient:
    """
    Create a mock LLM client with a predefined script of responses.

    This is a convenience function for testing and educational purposes.

    Args:
        script: List of responses the mock LLM should return in sequence.

    Returns:
        MockLLMClient: A mock LLM client.
    """
    return MockLLMClient(script=script)
