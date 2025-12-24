# quack-core/src/quack_core/integrations/llms/clients/__init__.py
"""
LLM client implementations.

This module provides implementations of LLM clients for various providers,
including a base class with common functionality and provider-specific clients.
"""

from quack_core.integrations.llms.clients.anthropic import AnthropicClient
from quack_core.integrations.llms.clients.base import LLMClient
from quack_core.integrations.llms.clients.mock import MockLLMClient
from quack_core.integrations.llms.clients.openai import OpenAIClient

__all__ = [
    "AnthropicClient",
    "LLMClient",
    "MockLLMClient",
    "OpenAIClient",
]
