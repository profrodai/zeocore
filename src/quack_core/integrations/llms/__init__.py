# quack-core/src/quack-core/integrations/llms/__init__.py
"""
LLM integration for QuackCore.

This module provides a lightweight integration with Large Language Models (LLMs),
offering a standardized interface for making chat completions across different
LLM providers.
"""

from quackcore.integrations.core.protocols import IntegrationProtocol
from quackcore.integrations.llms.clients import (
    LLMClient,
    MockLLMClient,
)
from quackcore.integrations.llms.clients.anthropic import AnthropicClient
from quackcore.integrations.llms.clients.ollama import OllamaClient
from quackcore.integrations.llms.clients.openai import OpenAIClient
from quackcore.integrations.llms.config import LLMConfig, LLMConfigProvider
from quackcore.integrations.llms.fallback import FallbackConfig, FallbackLLMClient
from quackcore.integrations.llms.models import (
    ChatMessage,
    FunctionCall,
    LLMOptions,
    RoleType,
    ToolCall,
)
from quackcore.integrations.llms.protocols import LLMProviderProtocol
from quackcore.integrations.llms.registry import (
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
    from quackcore.integrations.llms.service import LLMIntegration

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
