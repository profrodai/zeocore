# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/test_llms.py
# role: tests
# neighbors: __init__.py, test_config.py, test_config_provider.py, test_fallback.py, test_integration.py, test_models.py (+3 more)
# exports: TestLLMClient, TestOpenAIClient, TestAnthropicClient, TestMockLLMClient, TestLLMModels, TestLLMProtocols, TestLLMConfig, TestLLMConfigProvider (+2 more)
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

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
