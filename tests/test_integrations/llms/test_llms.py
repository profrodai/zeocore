# quack-core/tests/test_integrations/llms/test_llms.py
"""
Main entry point for LLM integration tests.

This file imports all the specific test modules to ensure they are discovered
by pytest when running the test suite.
"""

# Import client tests
from tests.test_integrations.llms.clients.test_anthropic import (
    TestAnthropicClient,
)
from tests.test_integrations.llms.clients.test_base import TestLLMClient
from tests.test_integrations.llms.clients.test_mock import TestMockLLMClient
from tests.test_integrations.llms.clients.test_openai import TestOpenAIClient

# Import model and protocol tests
from tests.test_integrations.llms.test_config import TestLLMConfig
from tests.test_integrations.llms.test_config_provider import (
    TestLLMConfigProvider,
)
from tests.test_integrations.llms.test_models import TestLLMModels
from tests.test_integrations.llms.test_protocols import TestLLMProtocols
from tests.test_integrations.llms.test_registry import TestLLMRegistry
from tests.test_integrations.llms.test_service import TestLLMService

# Export the test classes for direct import
__all__ = [
    # Client tests
    "TestLLMClient",
    "TestOpenAIClient",
    "TestAnthropicClient",
    "TestMockLLMClient",
    # Model and protocol tests
    "TestLLMModels",
    "TestLLMProtocols",
    # Configuration tests
    "TestLLMConfig",
    "TestLLMConfigProvider",
    # Integration tests
    "TestLLMRegistry",
    "TestLLMService",
]
