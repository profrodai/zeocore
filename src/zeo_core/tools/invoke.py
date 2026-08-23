"""Sync/async-neutral invocation with guards, availability, and result normalization."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypeVar, cast

from pydantic import BaseModel, ValidationError

from zeo_core.contracts import (
    CapabilityDefinition,
    CapabilityOutcome,
    CapabilityResult,
    GuardResult,
    RequestGuard,
)
from zeo_core.contracts.capabilities.invocation import (
    CapabilityInvocationRecord,
    digest_payload,
    redact_value,
)
from zeo_core.tools.context import ToolContext
from zeo_core.tools.definition_builder import coordination_key
from zeo_core.tools.services import (
    SERVICE_ARTIFACTS,
    SERVICE_CANCELLATION,
    SERVICE_CLOCK,
    SERVICE_REDACTION_PATHS,
    ArtifactSink,
    Cancellation,
    Clock,
    NeverCancelled,
    RecordingArtifactSink,
    SystemClock,
)

RequestT = TypeVar("RequestT", bound=BaseModel)
ResponseT = TypeVar("ResponseT")

InvokeFn = Callable[
    [RequestT, ToolContext],
    CapabilityResult[ResponseT] | Awaitable[CapabilityResult[ResponseT]],
]


class BoundCapability:
    """Concrete capability object produced by @capability and class adapters."""

    def __init__(
        self,
        *,
        definition: CapabilityDefinition,
        fn: InvokeFn[Any, Any],
        request_model: type[BaseModel],
        guards: Sequence[RequestGuard] = (),
        is_async: bool,
        availability: Callable[[ToolContext], bool] | None = None,
    ) -> None:
        self.definition = definition
        self._fn = fn
        self.request_model = request_model
        self.guards = tuple(guards)
        self.is_async = is_async
        self._availability = availability

    def is_available(self, ctx: ToolContext) -> bool:
        if self._availability is not None:
            return self._availability(ctx)
        return requirements_available(self.definition, ctx)

    def invoke(
        self, request: BaseModel, ctx: ToolContext
    ) -> CapabilityResult[Any] | Awaitable[CapabilityResult[Any]]:
        if self.is_async:
            return invoke_async(self, request, ctx)
        return invoke_sync(self, request, ctx)


def context_clock(ctx: ToolContext) -> Clock:
    clock = ctx.get_service(SERVICE_CLOCK)
    if clock is None:
        return SystemClock()
    return cast(Clock, clock)


def context_cancellation(ctx: ToolContext) -> Cancellation:
    token = ctx.get_service(SERVICE_CANCELLATION)
    if token is None:
        return NeverCancelled()
    return cast(Cancellation, token)


def context_artifacts(ctx: ToolContext) -> ArtifactSink | None:
    sink = ctx.get_service(SERVICE_ARTIFACTS)
    return cast(ArtifactSink | None, sink)


def _needs_fs(definition: CapabilityDefinition) -> bool:
    req = definition.requirements.filesystem
    return req.read or req.write


def requirements_available(definition: CapabilityDefinition, ctx: ToolContext) -> bool:
    for name in definition.requirements.services:
        if ctx.get_service(name) is None:
            return False
    if _needs_fs(definition) and ctx.fs is None:
        return False
    return True


def missing_requirements(
    definition: CapabilityDefinition, ctx: ToolContext
) -> list[str]:
    missing: list[str] = []
    for name in sorted(definition.requirements.services):
        if ctx.get_service(name) is None:
            missing.append(name)
    if _needs_fs(definition) and ctx.fs is None:
        missing.append("fs")
    return missing


def _run_guards(capability: BoundCapability, request: BaseModel) -> GuardResult:
    for guard in capability.guards:
        result = guard.check(request)
        if not result.ok:
            return result
    return GuardResult.accept()


def _normalize_return(value: object, *, cancelled: bool) -> CapabilityResult[Any]:
    if cancelled:
        if (
            isinstance(value, CapabilityResult)
            and value.outcome == CapabilityOutcome.cancelled
        ):
            return value
        return CapabilityResult.fail(
            msg="Caller cancellation observed",
            code="ZEO_CAP_CANCELLED",
            outcome=CapabilityOutcome.cancelled,
        )
    if isinstance(value, CapabilityResult):
        return value
    return CapabilityResult.fail(
        msg="Capability must return CapabilityResult",
        code="ZEO_CAP_INVALID_RETURN",
        outcome=CapabilityOutcome.invalid_return,
        metadata={"returned_type": type(value).__name__},
    )


def _exception_result(exc: BaseException) -> CapabilityResult[Any]:
    if isinstance(exc, ValidationError):
        return CapabilityResult.fail(
            msg="Request failed validation",
            code="ZEO_CAP_GUARD_REJECTED",
            exception=exc,
            outcome=CapabilityOutcome.guard_rejected,
        )
    return CapabilityResult.fail(
        msg=f"Unexpected {type(exc).__name__}: {exc}",
        code="ZEO_CAP_UNEXPECTED",
        exception=exc if isinstance(exc, Exception) else None,
        outcome=CapabilityOutcome.unexpected_exception,
    )


def invoke_sync(
    capability: BoundCapability, request: BaseModel, ctx: ToolContext
) -> CapabilityResult[Any]:
    if context_cancellation(ctx).is_cancelled():
        return CapabilityResult.fail(
            msg="Caller cancellation observed",
            code="ZEO_CAP_CANCELLED",
            outcome=CapabilityOutcome.cancelled,
        )
    if not isinstance(request, capability.request_model):
        try:
            request = capability.request_model.model_validate(
                request if isinstance(request, dict) else request
            )
        except ValidationError as exc:
            return _exception_result(exc)

    guard = _run_guards(capability, request)
    if not guard.ok:
        return CapabilityResult.fail(
            msg=guard.message or "Request rejected by guard",
            code=guard.code or "ZEO_CAP_GUARD_REJECTED",
            outcome=CapabilityOutcome.guard_rejected,
            metadata={"issues": [i.model_dump() for i in guard.issues]},
        )

    if not capability.is_available(ctx):
        missing = missing_requirements(capability.definition, ctx)
        return CapabilityResult.unavailable(
            reason=(
                "Capability unavailable; missing: " + (", ".join(missing) or "unknown")
            ),
        )

    try:
        raw = capability._fn(request, ctx)
        if inspect.isawaitable(raw):
            return CapabilityResult.fail(
                msg="Async capability invoked with invoke_sync",
                code="ZEO_CAP_INVALID_RETURN",
                outcome=CapabilityOutcome.invalid_return,
            )
        return _normalize_return(
            raw, cancelled=context_cancellation(ctx).is_cancelled()
        )
    except BaseException as exc:  # noqa: BLE001 -- convert to structured result
        if context_cancellation(ctx).is_cancelled():
            return CapabilityResult.fail(
                msg="Caller cancellation observed",
                code="ZEO_CAP_CANCELLED",
                exception=exc if isinstance(exc, Exception) else None,
                outcome=CapabilityOutcome.cancelled,
            )
        return _exception_result(exc)


async def invoke_async(
    capability: BoundCapability, request: BaseModel, ctx: ToolContext
) -> CapabilityResult[Any]:
    if context_cancellation(ctx).is_cancelled():
        return CapabilityResult.fail(
            msg="Caller cancellation observed",
            code="ZEO_CAP_CANCELLED",
            outcome=CapabilityOutcome.cancelled,
        )
    if not isinstance(request, capability.request_model):
        try:
            request = capability.request_model.model_validate(request)
        except ValidationError as exc:
            return _exception_result(exc)

    guard = _run_guards(capability, request)
    if not guard.ok:
        return CapabilityResult.fail(
            msg=guard.message or "Request rejected by guard",
            code=guard.code or "ZEO_CAP_GUARD_REJECTED",
            outcome=CapabilityOutcome.guard_rejected,
            metadata={"issues": [i.model_dump() for i in guard.issues]},
        )

    if not capability.is_available(ctx):
        missing = missing_requirements(capability.definition, ctx)
        return CapabilityResult.unavailable(
            reason=(
                "Capability unavailable; missing: " + (", ".join(missing) or "unknown")
            ),
        )

    try:
        raw = capability._fn(request, ctx)
        if inspect.isawaitable(raw):
            raw = await raw
        return _normalize_return(
            raw, cancelled=context_cancellation(ctx).is_cancelled()
        )
    except BaseException as exc:  # noqa: BLE001
        if context_cancellation(ctx).is_cancelled():
            return CapabilityResult.fail(
                msg="Caller cancellation observed",
                code="ZEO_CAP_CANCELLED",
                exception=exc if isinstance(exc, Exception) else None,
                outcome=CapabilityOutcome.cancelled,
            )
        return _exception_result(exc)


def invocation_record(
    *,
    capability: BoundCapability,
    request: BaseModel,
    result: CapabilityResult[Any],
    ctx: ToolContext,
    invocation_id: str,
    started_at: object,
    ended_at: object,
) -> CapabilityInvocationRecord:
    extra = ctx.get_service(SERVICE_REDACTION_PATHS)
    extra_paths = (
        frozenset(extra)
        if isinstance(extra, (set, frozenset, list, tuple))
        else frozenset()
    )
    dumped = request.model_dump(mode="json")
    redacted_request, request_redactions = redact_value(dumped, extra_paths=extra_paths)
    result_dump = result.model_dump(mode="json")
    redacted_result, result_redactions = redact_value(
        result_dump, extra_paths=extra_paths
    )
    sink = context_artifacts(ctx)
    refs = tuple(sink.refs) if isinstance(sink, RecordingArtifactSink) else ()
    from datetime import datetime

    return CapabilityInvocationRecord(
        invocation_id=invocation_id,
        capability_id=capability.definition.id,
        request_digest=digest_payload(redacted_request),
        started_at=started_at
        if isinstance(started_at, datetime)
        else context_clock(ctx).now(),
        ended_at=ended_at
        if isinstance(ended_at, datetime)
        else context_clock(ctx).now(),
        outcome=result.outcome or CapabilityOutcome.integration_failure,
        status=result.status,
        error_code=result.machine_message,
        artifact_refs=refs,
        result_digest=digest_payload(redacted_result),
        redactions=request_redactions + result_redactions,
    )


def resource_coordination_key(
    capability: BoundCapability, request: BaseModel
) -> str | None:
    return coordination_key(request, capability.definition.effects.resource_key_fields)
