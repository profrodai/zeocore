"""Policy-aware sync and async runners for read-only and advisory operations."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from zeo_core.execution.models import (
    AttemptOutcome,
    AttemptRecord,
    ExecutionMode,
    ExecutionOutcome,
    ExecutionPolicy,
    FailureKind,
    OperationMode,
    ResilientExecutionResult,
)

T = TypeVar("T")


class CancellationToken(Protocol):
    """Minimal cancellation surface used by both runners."""

    def is_cancelled(self) -> bool: ...


class NeverCancelled:
    """Default token for callers that do not supply cancellation."""

    def is_cancelled(self) -> bool:
        return False


@dataclass(frozen=True)
class AttemptContext:
    """Budget passed to exactly one target invocation."""

    attempt_number: int
    target_id: str
    timeout_seconds: float
    remaining_total_seconds: float
    cancellation: CancellationToken


@dataclass(frozen=True)
class SyncExecutionTarget(Generic[T]):
    """One-attempt synchronous target."""

    target_id: str
    response_type: type[Any]
    invoke: Callable[[AttemptContext], T]
    execution_mode: ExecutionMode = ExecutionMode.LIVE
    internal_max_attempts: int = 1
    preflight_failure: FailureKind | None = None


@dataclass(frozen=True)
class AsyncExecutionTarget(Generic[T]):
    """One-attempt asynchronous target."""

    target_id: str
    response_type: type[Any]
    invoke: Callable[[AttemptContext], Awaitable[T]]
    execution_mode: ExecutionMode = ExecutionMode.LIVE
    internal_max_attempts: int = 1
    preflight_failure: FailureKind | None = None


class AttemptError(Exception):
    """A normalized failure that carries no provider text or secret material."""

    def __init__(
        self,
        kind: FailureKind,
        *,
        dispatch_started: bool = True,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(kind.value)
        if retry_after_seconds is not None and retry_after_seconds < 0:
            raise ValueError("retry_after_seconds cannot be negative")
        self.kind = kind
        self.dispatch_started = dispatch_started
        self.retry_after_seconds = retry_after_seconds


_FAILURE_CODES: dict[FailureKind, str] = {
    FailureKind.TIMEOUT: "ZEO_EXEC_TIMEOUT",
    FailureKind.TRANSIENT: "ZEO_EXEC_TRANSIENT",
    FailureKind.RATE_LIMIT: "ZEO_EXEC_RATE_LIMIT",
    FailureKind.MALFORMED_RESPONSE: "ZEO_EXEC_MALFORMED_RESPONSE",
    FailureKind.VALIDATION: "ZEO_EXEC_VALIDATION",
    FailureKind.AUTHORIZATION: "ZEO_EXEC_AUTHORIZATION",
    FailureKind.AUTHENTICATION: "ZEO_EXEC_AUTHENTICATION",
    FailureKind.CANCELLED: "ZEO_EXEC_CANCELLED",
    FailureKind.PERMANENT: "ZEO_EXEC_PERMANENT",
}


def _refused(code: str) -> ResilientExecutionResult:
    return ResilientExecutionResult(
        outcome=ExecutionOutcome.REFUSED,
        machine_code=code,
        total_elapsed_seconds=0,
    )


def _validate_targets(
    policy: ExecutionPolicy,
    targets: Mapping[str, SyncExecutionTarget[Any] | AsyncExecutionTarget[Any]],
) -> ResilientExecutionResult | None:
    if policy.operation_mode is OperationMode.EFFECTFUL:
        return _refused("ZEO_EXEC_EFFECTFUL_REQUIRES_PERSISTENCE")
    planned: list[SyncExecutionTarget[Any] | AsyncExecutionTarget[Any]] = []
    for target_id in policy.attempt_targets:
        target = targets.get(target_id)
        if target is None or target.target_id != target_id:
            return _refused("ZEO_EXEC_TARGET_UNAVAILABLE")
        if target.internal_max_attempts != 1:
            return _refused("ZEO_EXEC_NESTED_RETRIES")
        if (
            target.execution_mode is ExecutionMode.SIMULATED
            and not policy.allow_simulated
        ):
            return _refused("ZEO_EXEC_SIMULATION_NOT_ALLOWED")
        planned.append(target)
    response_type = planned[0].response_type
    if any(target.response_type is not response_type for target in planned[1:]):
        return _refused("ZEO_EXEC_RESPONSE_CONTRACT_MISMATCH")
    return None


def _classify_exception(exc: Exception) -> tuple[FailureKind, bool, float | None]:
    if isinstance(exc, AttemptError):
        return exc.kind, exc.dispatch_started, exc.retry_after_seconds
    if isinstance(exc, TimeoutError):
        return FailureKind.TIMEOUT, True, None
    return FailureKind.PERMANENT, True, None


def _delay_after_failure(
    *,
    policy: ExecutionPolicy,
    attempt_number: int,
    kind: FailureKind,
    retry_after_seconds: float | None,
    remaining_seconds: float,
    jitter: Callable[[], float],
) -> float | None:
    if kind not in policy.retryable_failures:
        return None
    if attempt_number >= policy.max_attempts:
        return None
    delay = policy.backoff_after(attempt_number)
    if retry_after_seconds is not None:
        delay = max(delay, retry_after_seconds)
    if policy.jitter_fraction:
        unit = min(1.0, max(0.0, jitter()))
        multiplier = 1 + policy.jitter_fraction * ((2 * unit) - 1)
        delay *= multiplier
    if delay >= remaining_seconds:
        return None
    return delay


def _failed_result(
    *,
    kind: FailureKind,
    attempts: list[AttemptRecord],
    elapsed: float,
    exhausted: bool,
) -> ResilientExecutionResult:
    if exhausted:
        outcome = ExecutionOutcome.EXHAUSTED
    elif kind in {FailureKind.VALIDATION, FailureKind.AUTHORIZATION}:
        outcome = ExecutionOutcome.REFUSED
    else:
        outcome = ExecutionOutcome.FAILED_SAFE
    return ResilientExecutionResult(
        outcome=outcome,
        attempts=tuple(attempts),
        failure_kind=kind,
        machine_code=_FAILURE_CODES[kind],
        total_elapsed_seconds=max(0, elapsed),
    )


def _cancelled(
    attempts: list[AttemptRecord], elapsed: float
) -> ResilientExecutionResult:
    return ResilientExecutionResult(
        outcome=ExecutionOutcome.CANCELLED,
        attempts=tuple(attempts),
        machine_code="ZEO_EXEC_CANCELLED",
        total_elapsed_seconds=max(0, elapsed),
    )


def _sleep_sync(
    seconds: float,
    *,
    policy: ExecutionPolicy,
    cancellation: CancellationToken,
    sleep: Callable[[float], None],
) -> bool:
    remaining = seconds
    while remaining > 0:
        if cancellation.is_cancelled():
            return False
        step = min(remaining, policy.cancellation_poll_seconds)
        sleep(step)
        remaining -= step
    return not cancellation.is_cancelled()


async def _sleep_async(
    seconds: float,
    *,
    policy: ExecutionPolicy,
    cancellation: CancellationToken,
    sleep: Callable[[float], Awaitable[None]],
) -> bool:
    remaining = seconds
    while remaining > 0:
        if cancellation.is_cancelled():
            return False
        step = min(remaining, policy.cancellation_poll_seconds)
        await sleep(step)
        remaining -= step
    return not cancellation.is_cancelled()


def run_sync(  # noqa: C901 -- explicit bounded execution state machine
    policy: ExecutionPolicy,
    targets: Mapping[str, SyncExecutionTarget[T]],
    *,
    cancellation: CancellationToken | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> ResilientExecutionResult:
    """Run an explicit synchronous attempt plan within one total budget."""

    rejected = _validate_targets(policy, targets)
    if rejected is not None:
        return rejected
    token = cancellation or NeverCancelled()
    start = monotonic()
    attempts: list[AttemptRecord] = []
    if token.is_cancelled():
        return _cancelled(attempts, monotonic() - start)

    for number, target_id in enumerate(policy.attempt_targets, start=1):
        elapsed = max(0, monotonic() - start)
        remaining = policy.total_timeout_seconds - elapsed
        if remaining <= 0:
            kind = attempts[-1].failure_kind if attempts else FailureKind.TIMEOUT
            return _failed_result(
                kind=kind or FailureKind.TIMEOUT,
                attempts=attempts,
                elapsed=elapsed,
                exhausted=True,
            )
        if token.is_cancelled():
            return _cancelled(attempts, elapsed)

        target = targets[target_id]
        if target.preflight_failure is not None:
            return _failed_result(
                kind=target.preflight_failure,
                attempts=attempts,
                elapsed=elapsed,
                exhausted=False,
            )
        timeout = min(policy.attempt_timeout_seconds, remaining)
        attempt_started = max(0, monotonic() - start)
        context = AttemptContext(
            attempt_number=number,
            target_id=target_id,
            timeout_seconds=timeout,
            remaining_total_seconds=remaining,
            cancellation=token,
        )
        try:
            value = target.invoke(context)
            if not isinstance(value, target.response_type):
                raise AttemptError(FailureKind.MALFORMED_RESPONSE)
        except Exception as exc:  # noqa: BLE001 -- normalized without provider text
            kind, dispatch_started, retry_after = _classify_exception(exc)
            ended = max(attempt_started, monotonic() - start)
            remaining_after = policy.total_timeout_seconds - ended
            delay = _delay_after_failure(
                policy=policy,
                attempt_number=number,
                kind=kind,
                retry_after_seconds=retry_after,
                remaining_seconds=remaining_after,
                jitter=jitter,
            )
            attempts.append(
                AttemptRecord(
                    attempt_number=number,
                    target_id=target_id,
                    execution_mode=target.execution_mode,
                    started_after_seconds=attempt_started,
                    ended_after_seconds=ended,
                    timeout_seconds=timeout,
                    dispatch_started=dispatch_started,
                    outcome=AttemptOutcome.FAILED,
                    failure_kind=kind,
                    machine_code=_FAILURE_CODES[kind],
                    backoff_before_next_seconds=delay or 0,
                )
            )
            if kind is FailureKind.CANCELLED or token.is_cancelled():
                return _cancelled(attempts, ended)
            if delay is None:
                return _failed_result(
                    kind=kind,
                    attempts=attempts,
                    elapsed=ended,
                    exhausted=kind in policy.retryable_failures,
                )
            if not _sleep_sync(
                delay,
                policy=policy,
                cancellation=token,
                sleep=sleep,
            ):
                return _cancelled(attempts, monotonic() - start)
            continue

        ended = max(attempt_started, monotonic() - start)
        attempts.append(
            AttemptRecord(
                attempt_number=number,
                target_id=target_id,
                execution_mode=target.execution_mode,
                started_after_seconds=attempt_started,
                ended_after_seconds=ended,
                timeout_seconds=timeout,
                dispatch_started=True,
                outcome=AttemptOutcome.SUCCEEDED,
            )
        )
        return ResilientExecutionResult(
            outcome=ExecutionOutcome.SUCCEEDED,
            value=value,
            attempts=tuple(attempts),
            selected_target_id=target_id,
            execution_mode=target.execution_mode,
            total_elapsed_seconds=ended,
        )

    raise AssertionError("validated attempt plan must return from the loop")


async def run_async(  # noqa: C901 -- sync-parity state machine
    policy: ExecutionPolicy,
    targets: Mapping[str, AsyncExecutionTarget[T]],
    *,
    cancellation: CancellationToken | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    jitter: Callable[[], float] = random.random,
) -> ResilientExecutionResult:
    """Run an explicit asynchronous attempt plan within one total budget."""

    rejected = _validate_targets(policy, targets)
    if rejected is not None:
        return rejected
    token = cancellation or NeverCancelled()
    start = monotonic()
    attempts: list[AttemptRecord] = []
    if token.is_cancelled():
        return _cancelled(attempts, monotonic() - start)

    for number, target_id in enumerate(policy.attempt_targets, start=1):
        elapsed = max(0, monotonic() - start)
        remaining = policy.total_timeout_seconds - elapsed
        if remaining <= 0:
            kind = attempts[-1].failure_kind if attempts else FailureKind.TIMEOUT
            return _failed_result(
                kind=kind or FailureKind.TIMEOUT,
                attempts=attempts,
                elapsed=elapsed,
                exhausted=True,
            )
        if token.is_cancelled():
            return _cancelled(attempts, elapsed)

        target = targets[target_id]
        if target.preflight_failure is not None:
            return _failed_result(
                kind=target.preflight_failure,
                attempts=attempts,
                elapsed=elapsed,
                exhausted=False,
            )
        timeout = min(policy.attempt_timeout_seconds, remaining)
        attempt_started = max(0, monotonic() - start)
        context = AttemptContext(
            attempt_number=number,
            target_id=target_id,
            timeout_seconds=timeout,
            remaining_total_seconds=remaining,
            cancellation=token,
        )
        try:
            async with asyncio.timeout(timeout):
                value = await target.invoke(context)
            if not isinstance(value, target.response_type):
                raise AttemptError(FailureKind.MALFORMED_RESPONSE)
        except Exception as exc:  # noqa: BLE001 -- normalized without provider text
            kind, dispatch_started, retry_after = _classify_exception(exc)
            ended = max(attempt_started, monotonic() - start)
            remaining_after = policy.total_timeout_seconds - ended
            delay = _delay_after_failure(
                policy=policy,
                attempt_number=number,
                kind=kind,
                retry_after_seconds=retry_after,
                remaining_seconds=remaining_after,
                jitter=jitter,
            )
            attempts.append(
                AttemptRecord(
                    attempt_number=number,
                    target_id=target_id,
                    execution_mode=target.execution_mode,
                    started_after_seconds=attempt_started,
                    ended_after_seconds=ended,
                    timeout_seconds=timeout,
                    dispatch_started=dispatch_started,
                    outcome=AttemptOutcome.FAILED,
                    failure_kind=kind,
                    machine_code=_FAILURE_CODES[kind],
                    backoff_before_next_seconds=delay or 0,
                )
            )
            if kind is FailureKind.CANCELLED or token.is_cancelled():
                return _cancelled(attempts, ended)
            if delay is None:
                return _failed_result(
                    kind=kind,
                    attempts=attempts,
                    elapsed=ended,
                    exhausted=kind in policy.retryable_failures,
                )
            if not await _sleep_async(
                delay,
                policy=policy,
                cancellation=token,
                sleep=sleep,
            ):
                return _cancelled(attempts, monotonic() - start)
            continue

        ended = max(attempt_started, monotonic() - start)
        attempts.append(
            AttemptRecord(
                attempt_number=number,
                target_id=target_id,
                execution_mode=target.execution_mode,
                started_after_seconds=attempt_started,
                ended_after_seconds=ended,
                timeout_seconds=timeout,
                dispatch_started=True,
                outcome=AttemptOutcome.SUCCEEDED,
            )
        )
        return ResilientExecutionResult(
            outcome=ExecutionOutcome.SUCCEEDED,
            value=value,
            attempts=tuple(attempts),
            selected_target_id=target_id,
            execution_mode=target.execution_mode,
            total_elapsed_seconds=ended,
        )

    raise AssertionError("validated attempt plan must return from the loop")
