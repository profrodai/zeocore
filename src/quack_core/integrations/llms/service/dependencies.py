# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/service/dependencies.py
# module: quack_core.integrations.llms.service.dependencies
# role: service
# neighbors: __init__.py, operations.py, initialization.py, integration.py
# exports: check_llm_dependencies
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

"""
Dependency checking for LLM integration.

This module provides functions to check for available LLM providers and their dependencies.
"""

import importlib.util


def check_llm_dependencies() -> tuple[bool, str, list[str]]:
    """
    Check if LLM dependencies are available.

    Returns:
        tuple[bool, str, list[str]]: Success status, message, and list of available providers
    """
    available_providers = []

    # Check for OpenAI
    if importlib.util.find_spec("openai") is not None:
        available_providers.append("openai")

    # Check for Anthropic
    if importlib.util.find_spec("anthropic") is not None:
        available_providers.append("anthropic")

    # Check for Ollama (requires requests package)
    if importlib.util.find_spec("requests") is not None:
        # Try to connect to local Ollama server to check availability
        try:
            import requests

            try:
                response = requests.get("http://localhost:11434/api/version", timeout=1)
                if response.status_code == 200:
                    available_providers.append("ollama")
            except Exception:  # Using generic Exception for test compatibility
                # Failed to connect to Ollama server
                pass
        except ImportError:
            # Requests not installed
            pass

    # Always add MockLLM as it has no external dependencies
    available_providers.append("mock")

    if not available_providers or (
        len(available_providers) == 1 and available_providers[0] == "mock"
    ):
        return (
            False,
            "No LLM providers available. Install OpenAI or Anthropic package, or run Ollama locally.",
            available_providers,
        )

    return (
        True,
        f"Available LLM providers: {', '.join(available_providers)}",
        available_providers,
    )
