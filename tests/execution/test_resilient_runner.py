"""Behavioral proofs for the policy-aware execution runner."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import pytest
from pydantic import BaseModel

from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.execution import (
    AsyncExecutionTarget,
    AttemptContext,
    AttemptError,
    ExecutionMode,
    ExecutionOutcome,
    ExecutionPolicy,
    FailureKind,
    OperationMode,
    SyncExecutionTarget,
    async_capability_target,
    run_async,
    run_sync,
    sync_capability_target,
)
from zeo_core.tools import ToolContext, bound_capability_of, capability


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.advance(seconds)

    async def async_sleep(self, seconds: float) -> None:
        self.sleep(seconds)


class MutableCancellation:
    def __init__(self, cancelled: bool = False) -> None:
        self.cancelled = cancelled

    def is_cancelled(self) -> bool:
        return self.cancelled


def policy(
    *targets: str,
    total: float = 120,
    attempt: float = 120,
    backoff: tuple[float, ...] = (),
    retryable: frozenset[FailureKind] | None = None,
    mode: OperationMode = OperationMode.READ_ONLY,
    allow_simulated: bool = False,
) -> ExecutionPolicy:
    kwargs: dict[str, Any] = {}
    if retryable is not None:
        kwargs["retryable_failures"] = retryable
    return ExecutionPolicy(
        operation_mode=mode,
        total_timeout_seconds=total,
        attempt_timeout_seconds=attempt,
        attempt_targets=targets,
        backoff_seconds=backoff,
        allow_simulated=allow_simulated,
        **kwargs,
    )


def target(
    target_id: str,
    invoke: Callable[[AttemptContext], object],
    *,
    response_type: type[Any] = str,
    mode: ExecutionMode = ExecutionMode.LIVE,
    internal_max_attempts: int = 1,
    preflight_failure: FailureKind | None = None,
) -> SyncExecutionTarget[object]:
    return SyncExecutionTarget(
        target_id=target_id,
        response_type=response_type,
        invoke=invoke,
        execution_mode=mode,
        internal_max_attempts=internal_max_attempts,
        preflight_failure=preflight_failure,
    )


def test_one_total_budget_has_no_hidden_sixty_second_outer_deadline() -> None:
    clock = FakeClock()
    seen: list[tuple[float, float]] = []

    def call(ctx: AttemptContext) -> str:
        seen.append((ctx.timeout_seconds, ctx.remaining_total_seconds))
        return "done"

    result = run_sync(
        policy("ollama"),
        {"ollama": target("ollama", call)},
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert seen == [(120, 120)]
    assert result.attempts[0].timeout_seconds == 120


def test_read_only_timeout_retries_once_and_records_both_attempts() -> None:
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("provider detail must not be retained")
        return "ok"

    result = run_sync(
        policy("ollama", "ollama"),
        {"ollama": target("ollama", call)},
    )

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert calls == 2
    assert [record.failure_kind for record in result.attempts] == [
        FailureKind.TIMEOUT,
        None,
    ]


def test_exhausted_budget_stops_without_sleep_or_extra_call() -> None:
    clock = FakeClock()
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        clock.advance(9)
        raise AttemptError(FailureKind.TIMEOUT)

    result = run_sync(
        policy("a", "a", total=10, attempt=10, backoff=(2,)),
        {"a": target("a", call)},
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result.outcome is ExecutionOutcome.EXHAUSTED
    assert calls == 1
    assert clock.sleeps == []


def test_cancellation_during_backoff_stops_before_next_call() -> None:
    clock = FakeClock()
    token = MutableCancellation()
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        raise AttemptError(FailureKind.TRANSIENT)

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        token.cancelled = True

    result = run_sync(
        policy("a", "a", backoff=(1,)),
        {"a": target("a", call)},
        cancellation=token,
        monotonic=clock.monotonic,
        sleep=sleep,
    )

    assert result.outcome is ExecutionOutcome.CANCELLED
    assert calls == 1
    assert len(result.attempts) == 1


@pytest.mark.parametrize(
    "kind",
    [
        FailureKind.VALIDATION,
        FailureKind.AUTHORIZATION,
        FailureKind.AUTHENTICATION,
    ],
)
def test_never_retry_failures_make_exactly_one_call(kind: FailureKind) -> None:
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        raise AttemptError(kind, dispatch_started=False)

    result = run_sync(
        policy("a", "a"),
        {"a": target("a", call)},
    )

    expected = (
        ExecutionOutcome.REFUSED
        if kind in {FailureKind.VALIDATION, FailureKind.AUTHORIZATION}
        else ExecutionOutcome.FAILED_SAFE
    )
    assert result.outcome is expected
    assert calls == 1
    assert result.attempts[0].dispatch_started is False


@pytest.mark.parametrize(
    "kind, expected",
    [
        (FailureKind.AUTHORIZATION, ExecutionOutcome.REFUSED),
        (FailureKind.AUTHENTICATION, ExecutionOutcome.FAILED_SAFE),
    ],
)
def test_preflight_failure_makes_zero_provider_calls(
    kind: FailureKind, expected: ExecutionOutcome
) -> None:
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        return "unexpected"

    result = run_sync(
        policy("a", "b"),
        {
            "a": target("a", call, preflight_failure=kind),
            "b": target("b", call),
        },
    )

    assert result.outcome is expected
    assert result.failure_kind is kind
    assert result.attempts == ()
    assert calls == 0


def test_precancelled_execution_makes_zero_calls() -> None:
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        return "unexpected"

    result = run_sync(
        policy("a"),
        {"a": target("a", call)},
        cancellation=MutableCancellation(cancelled=True),
    )

    assert result.outcome is ExecutionOutcome.CANCELLED
    assert calls == 0
    assert result.attempts == ()


def test_nested_internal_retries_are_refused_before_call() -> None:
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        return "unexpected"

    result = run_sync(
        policy("a"),
        {"a": target("a", call, internal_max_attempts=3)},
    )

    assert result.outcome is ExecutionOutcome.REFUSED
    assert result.machine_code == "ZEO_EXEC_NESTED_RETRIES"
    assert calls == 0


def test_explicit_fallback_records_actual_provider_identity() -> None:
    calls: list[str] = []

    def call_a(_ctx: AttemptContext) -> str:
        calls.append("a")
        raise AttemptError(FailureKind.TRANSIENT)

    def call_b(_ctx: AttemptContext) -> str:
        calls.append("b")
        return "from-b"

    result = run_sync(
        policy("a", "b"),
        {"a": target("a", call_a), "b": target("b", call_b)},
    )

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert calls == ["a", "b"]
    assert result.selected_target_id == "b"
    assert [record.target_id for record in result.attempts] == ["a", "b"]


def test_absent_fallback_plan_never_selects_available_second_target() -> None:
    calls: list[str] = []

    def call_a(_ctx: AttemptContext) -> str:
        calls.append("a")
        raise AttemptError(FailureKind.TRANSIENT)

    def call_b(_ctx: AttemptContext) -> str:
        calls.append("b")
        return "from-b"

    result = run_sync(
        policy("a"),
        {"a": target("a", call_a), "b": target("b", call_b)},
    )

    assert result.outcome is ExecutionOutcome.EXHAUSTED
    assert calls == ["a"]


def test_simulated_target_can_never_produce_live_label() -> None:
    simulated = target(
        "mock",
        lambda _ctx: "scripted",
        mode=ExecutionMode.SIMULATED,
    )

    refused = run_sync(policy("mock"), {"mock": simulated})
    accepted = run_sync(
        policy("mock", allow_simulated=True),
        {"mock": simulated},
    )

    assert refused.outcome is ExecutionOutcome.REFUSED
    assert refused.attempts == ()
    assert accepted.outcome is ExecutionOutcome.SUCCEEDED
    assert accepted.execution_mode is ExecutionMode.SIMULATED


def test_effectful_operation_is_structurally_refused_before_persistence_exists() -> (
    None
):
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        return "must-not-run"

    result = run_sync(
        policy("provider", mode=OperationMode.EFFECTFUL),
        {"provider": target("provider", call)},
    )

    assert result.outcome is ExecutionOutcome.REFUSED
    assert result.machine_code == "ZEO_EXEC_EFFECTFUL_REQUIRES_PERSISTENCE"
    assert calls == 0


def test_exception_text_is_not_retained_in_result_or_attempt_records() -> None:
    canary = "ya29.A0ARrdaM_LIVE_OAUTH_TOKEN_xyz"

    def call(_ctx: AttemptContext) -> str:
        raise RuntimeError(canary)

    result = run_sync(policy("a"), {"a": target("a", call)})
    rendered = result.model_dump_json()

    assert result.outcome is ExecutionOutcome.FAILED_SAFE
    assert canary not in rendered
    assert "RuntimeError" not in rendered


def test_malformed_advisory_response_retries_only_when_explicit() -> None:
    calls = 0

    def call(_ctx: AttemptContext) -> object:
        nonlocal calls
        calls += 1
        return 3 if calls == 1 else "valid"

    result = run_sync(
        policy(
            "a",
            "a",
            mode=OperationMode.ADVISORY,
            retryable=frozenset({FailureKind.MALFORMED_RESPONSE}),
        ),
        {"a": target("a", call)},
    )

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert calls == 2
    assert result.attempts[0].failure_kind is FailureKind.MALFORMED_RESPONSE


def test_rate_limit_honors_bounded_retry_after() -> None:
    clock = FakeClock()
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AttemptError(
                FailureKind.RATE_LIMIT,
                retry_after_seconds=0.3,
            )
        return "ok"

    result = run_sync(
        policy("a", "a", backoff=(0.1,)),
        {"a": target("a", call)},
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert sum(clock.sleeps) == pytest.approx(0.3)
    assert result.attempts[0].backoff_before_next_seconds == pytest.approx(0.3)


def test_injected_jitter_is_bounded_and_deterministic() -> None:
    clock = FakeClock()
    calls = 0

    def call(_ctx: AttemptContext) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AttemptError(FailureKind.TRANSIENT)
        return "ok"

    configured = ExecutionPolicy(
        total_timeout_seconds=10,
        attempt_timeout_seconds=5,
        attempt_targets=("a", "a"),
        backoff_seconds=(2,),
        jitter_fraction=0.5,
    )
    result = run_sync(
        configured,
        {"a": target("a", call)},
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        jitter=lambda: 1.0,
    )

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert sum(clock.sleeps) == pytest.approx(3)
    assert result.attempts[0].backoff_before_next_seconds == 3


def test_async_runner_matches_sync_classification_and_bounds() -> None:
    sync_clock = FakeClock()
    async_clock = FakeClock()
    sync_calls = 0
    async_calls = 0

    def sync_call(_ctx: AttemptContext) -> str:
        nonlocal sync_calls
        sync_calls += 1
        if sync_calls == 1:
            raise TimeoutError
        return "ok"

    async def async_call(_ctx: AttemptContext) -> str:
        nonlocal async_calls
        async_calls += 1
        if async_calls == 1:
            raise TimeoutError
        return "ok"

    configured = policy("a", "a", attempt=30)
    sync_result = run_sync(
        configured,
        {"a": target("a", sync_call)},
        monotonic=sync_clock.monotonic,
        sleep=sync_clock.sleep,
    )
    async_result = asyncio.run(
        run_async(
            configured,
            {
                "a": AsyncExecutionTarget(
                    target_id="a",
                    response_type=str,
                    invoke=async_call,
                )
            },
            monotonic=async_clock.monotonic,
            sleep=async_clock.async_sleep,
        )
    )

    assert sync_result.outcome is async_result.outcome is ExecutionOutcome.SUCCEEDED
    assert [r.failure_kind for r in sync_result.attempts] == [
        r.failure_kind for r in async_result.attempts
    ]
    assert [r.timeout_seconds for r in sync_result.attempts] == [
        r.timeout_seconds for r in async_result.attempts
    ]


class EchoRequest(BaseModel):
    text: str


class EchoResponse(BaseModel):
    text: str


@capability(
    id="execution.echo@1.0.0",
    description="Read-only echo used to prove capability adaptation.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(request={"text": "hi"}, response={"text": "hi"}),),
)
def echo(request: EchoRequest, ctx: ToolContext) -> CapabilityResult[EchoResponse]:
    _ = ctx
    return CapabilityResult.ok(data=EchoResponse(text=request.text))


def tool_context() -> ToolContext:
    return ToolContext(
        run_id="execution-test",
        tool_name="echo",
        tool_version="1.0.0",
        logger=logging.getLogger("execution-test"),
        fs=object(),
        work_dir=".",
        output_dir=".",
    )


def test_read_only_bound_capability_runs_through_sync_adapter() -> None:
    cap = bound_capability_of(echo)
    adapted = sync_capability_target(
        "local",
        cap,
        EchoRequest(text="hello"),
        tool_context(),
    )

    result = run_sync(policy("local"), {"local": adapted})

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert isinstance(result.value, CapabilityResult)
    assert result.value.data == EchoResponse(text="hello")


def test_read_only_bound_capability_runs_through_async_adapter() -> None:
    cap = bound_capability_of(echo)
    adapted = async_capability_target(
        "local",
        cap,
        EchoRequest(text="hello"),
        tool_context(),
    )

    result = asyncio.run(run_async(policy("local"), {"local": adapted}))

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert isinstance(result.value, CapabilityResult)
    assert result.value.data == EchoResponse(text="hello")
