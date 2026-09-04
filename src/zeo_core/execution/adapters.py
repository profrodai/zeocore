"""Adapters from ZeoCore's one-attempt capabilities to resilient targets."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from zeo_core.contracts.common.enums import (
    CapabilityOutcome,
    CapabilityStatus,
    EffectKind,
)
from zeo_core.contracts.envelopes.result import CapabilityResult
from zeo_core.execution.models import ExecutionMode, FailureKind
from zeo_core.execution.runner import (
    AsyncExecutionTarget,
    AttemptContext,
    AttemptError,
    SyncExecutionTarget,
)
from zeo_core.tools.context import ToolContext
from zeo_core.tools.invoke import BoundCapability, invoke_async, invoke_sync


def _require_read_only(capability: BoundCapability) -> None:
    if capability.definition.effects.kinds != frozenset({EffectKind.READ}):
        raise ValueError(
            "resilient capability adapters currently support exactly READ effects; "
            "effectful execution requires persisted orchestration"
        )


def _unwrap(result: CapabilityResult[Any]) -> CapabilityResult[Any]:
    if result.status is CapabilityStatus.success:
        return result
    if result.outcome is CapabilityOutcome.guard_rejected:
        raise AttemptError(FailureKind.VALIDATION, dispatch_started=False)
    if result.outcome is CapabilityOutcome.cancelled:
        raise AttemptError(FailureKind.CANCELLED, dispatch_started=False)
    raise AttemptError(FailureKind.PERMANENT)


def sync_capability_target(
    target_id: str,
    capability: BoundCapability,
    request: BaseModel,
    ctx: ToolContext,
    *,
    execution_mode: ExecutionMode = ExecutionMode.LIVE,
) -> SyncExecutionTarget[CapabilityResult[Any]]:
    """Adapt one read-only BoundCapability without adding leaf retries."""

    _require_read_only(capability)

    def call(_attempt: AttemptContext) -> CapabilityResult[Any]:
        return _unwrap(invoke_sync(capability, request, ctx))

    return SyncExecutionTarget(
        target_id=target_id,
        response_type=CapabilityResult,
        invoke=call,
        execution_mode=execution_mode,
    )


def async_capability_target(
    target_id: str,
    capability: BoundCapability,
    request: BaseModel,
    ctx: ToolContext,
    *,
    execution_mode: ExecutionMode = ExecutionMode.LIVE,
) -> AsyncExecutionTarget[CapabilityResult[Any]]:
    """Adapt one read-only async BoundCapability without adding leaf retries."""

    _require_read_only(capability)

    async def call(_attempt: AttemptContext) -> CapabilityResult[Any]:
        return _unwrap(await invoke_async(capability, request, ctx))

    return AsyncExecutionTarget(
        target_id=target_id,
        response_type=CapabilityResult,
        invoke=call,
        execution_mode=execution_mode,
    )
