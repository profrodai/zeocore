# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/service/operations.py
# module: quack_core.integrations.llms.service.operations
# role: service
# neighbors: __init__.py, dependencies.py, initialization.py, integration.py
# exports: chat, count_tokens, get_provider_status, reset_provider_status
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
LLM _operations for the integration service.

This module provides methods for interacting with LLMs, such as chat and token counting.
"""

from collections.abc import Callable, Sequence

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.models import ChatMessage, LLMOptions


def chat(
    self,
    messages: Sequence[ChatMessage] | Sequence[dict],
    options: LLMOptions | None = None,
    callback: Callable[[str], None] | None = None,
) -> IntegrationResult[str]:
    """
    Send a chat completion request to the LLM.

    Args:
        self: LLMIntegration instance
        messages: Sequence of messages for the conversation
        options: Additional options for the completion request
        callback: Optional callback function for streaming responses

    Returns:
        IntegrationResult[str]: Result of the chat completion request
    """
    if init_error := self._ensure_initialized():
        return init_error

    if not self.client:
        return IntegrationResult(success=False, error="LLM client not initialized")

    result = self.client.chat(messages, options, callback)

    # Add a note if we're using the mock client
    if self._using_mock and result.success:
        result.message = f"{result.message or 'Success'} (using mock LLM)"

    return result


def count_tokens(
    self, messages: Sequence[ChatMessage] | Sequence[dict]
) -> IntegrationResult[int]:
    """
    Count the number of tokens in the messages.

    Args:
        self: LLMIntegration instance
        messages: Sequence of messages to count tokens for

    Returns:
        IntegrationResult[int]: Result containing the token count
    """
    if init_error := self._ensure_initialized():
        return init_error

    if not self.client:
        return IntegrationResult(success=False, error="LLM client not initialized")

    result = self.client.count_tokens(messages)

    # Add a note if we're using the mock client
    if self._using_mock and result.success:
        result.message = f"{result.message or 'Success'} (using mock estimation)"

    return result


def get_provider_status(self) -> list[dict] | None:
    """
    Get the status of all providers when using fallback.

    Args:
        self: LLMIntegration instance

    Returns:
        list[dict] | None: Status information for all providers or None if not using fallback
    """
    if self._fallback_client is not None:
        return [
            status.model_dump()
            for status in self._fallback_client.get_provider_status()
        ]
    return None


def reset_provider_status(self) -> bool:
    """
    Reset the status of all providers, forcing re-evaluation.

    Args:
        self: LLMIntegration instance

    Returns:
        bool: True if successful, False if not using fallback
    """
    if self._fallback_client is not None:
        self._fallback_client.reset_provider_status()
        return True
    return False
