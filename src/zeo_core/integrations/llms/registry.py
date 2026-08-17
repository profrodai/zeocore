"""
Registry for LLM clients.

This module provides a registry for LLM clients, allowing for
dynamic loading and access to different LLM implementations.
"""

from typing import Any

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.core.logging import get_logger
from zeo_core.integrations.llms.clients.anthropic import AnthropicClient
from zeo_core.integrations.llms.clients.base import LLMClient
from zeo_core.integrations.llms.clients.mock import MockLLMClient
from zeo_core.integrations.llms.clients.ollama import OllamaClient
from zeo_core.integrations.llms.clients.openai import OpenAIClient

# Global registry of LLM clients
_LLM_REGISTRY: dict[str, type[LLMClient]] = {
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
    "ollama": OllamaClient,
    "mock": MockLLMClient,
}

logger = get_logger(__name__)


def register_llm_client(name: str, client_class: type[LLMClient]) -> None:
    """
    Register an LLM client implementation.

    Args:
        name: Name to register the client under
        client_class: LLM client class to register
    """
    _LLM_REGISTRY[name.lower()] = client_class
    logger.debug(f"Registered LLM client: {name}")


def get_llm_client(
    provider: str = "openai",
    model: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,  # noqa: ANN401 -- provider-specific kwargs forwarded to the resolved LLMClient subclass constructor
) -> LLMClient:
    """
    Get an LLM client instance.

    Args:
        provider: Provider name (e.g., "openai", "anthropic", "ollama", "mock")
        model: Model name to use
        api_key: API key for authentication
        **kwargs: Additional provider-specific arguments

    Returns:
        LLMClient: LLM client instance

    Raises:
        ZeoIntegrationError: If the provider is not supported
    """
    provider_lower = provider.lower()

    if provider_lower not in _LLM_REGISTRY:
        registered = ", ".join(_LLM_REGISTRY.keys())
        raise ZeoIntegrationError(
            f"Unsupported LLM provider: {provider}. Registered providers: {registered}"
        )

    client_class = _LLM_REGISTRY[provider_lower]

    try:
        # Pass provider-specific kwargs correctly
        client_kwargs: dict[str, Any] = {"model": model, "api_key": api_key}
        client_kwargs.update(kwargs)

        return client_class(**client_kwargs)
    except Exception as e:
        raise ZeoIntegrationError(
            f"Failed to initialize {provider} client: {e}",
            context={"provider": provider},
            original_error=e,
        ) from e
