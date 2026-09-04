"""One-attempt LLM adapters for ZeoCore's outer execution policy."""

from __future__ import annotations

from collections.abc import Sequence

from zeo_core.core.errors import ZeoApiError, ZeoIntegrationError
from zeo_core.execution.models import ExecutionMode, FailureKind
from zeo_core.execution.runner import (
    AttemptContext,
    AttemptError,
    SyncExecutionTarget,
)
from zeo_core.integrations.llms.models import ChatMessage, LLMOptions
from zeo_core.integrations.llms.protocols import OneAttemptLLMProviderProtocol


def _api_failure(error: ZeoApiError) -> FailureKind:
    """Classify only structured status; unknown provider prose is not evidence."""

    if error.status_code == 429:
        return FailureKind.RATE_LIMIT
    if error.status_code in {401, 403}:
        return FailureKind.AUTHENTICATION
    if error.status_code in {408, 504}:
        return FailureKind.TIMEOUT
    if error.status_code is not None and 500 <= error.status_code < 600:
        return FailureKind.TRANSIENT
    return FailureKind.PERMANENT


def llm_chat_target(
    target_id: str,
    client: OneAttemptLLMProviderProtocol,
    messages: Sequence[ChatMessage] | Sequence[dict],
    options: LLMOptions | None = None,
    *,
    execution_mode: ExecutionMode = ExecutionMode.LIVE,
) -> SyncExecutionTarget[str]:
    """Adapt one non-streaming LLM call without retaining provider error text."""

    def call(_context: AttemptContext) -> str:
        try:
            result = client.chat_once(messages, options)
        except ZeoApiError as error:
            raise AttemptError(_api_failure(error)) from error
        except ZeoIntegrationError as error:
            raise AttemptError(FailureKind.PERMANENT, dispatch_started=False) from error
        if not result.success or result.content is None:
            raise AttemptError(FailureKind.MALFORMED_RESPONSE)
        return result.content

    return SyncExecutionTarget(
        target_id=target_id,
        response_type=str,
        invoke=call,
        execution_mode=execution_mode,
        internal_max_attempts=1,
    )
