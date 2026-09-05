"""Behavioral proofs for hard-timeout subprocess execution targets."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest
from pydantic import BaseModel

from zeo_core.execution import (
    AttemptContext,
    ExecutionOutcome,
    ExecutionPolicy,
    FailureKind,
    SubprocessInvocation,
    run_sync,
    subprocess_target,
)


class ProcessReply(BaseModel):
    value: str


class MutableCancellation:
    def __init__(self) -> None:
        self.cancelled = False

    def is_cancelled(self) -> bool:
        return self.cancelled


def policy(
    *targets: str,
    total: float = 2,
    attempt: float = 1,
    retryable: frozenset[FailureKind] | None = None,
) -> ExecutionPolicy:
    kwargs: dict[str, object] = {}
    if retryable is not None:
        kwargs["retryable_failures"] = retryable
    return ExecutionPolicy(
        total_timeout_seconds=total,
        attempt_timeout_seconds=attempt,
        attempt_targets=targets,
        **kwargs,
    )


def parse_reply(raw: bytes) -> ProcessReply:
    return ProcessReply.model_validate_json(raw)


def test_request_uses_stdin_and_returns_only_typed_output() -> None:
    code = (
        "import json,sys; request=json.load(sys.stdin); "
        "json.dump({'value': request['value'].upper()}, sys.stdout)"
    )
    invocation = SubprocessInvocation(
        argv=(sys.executable, "-c", code),
        input_bytes=json.dumps({"value": "tea"}).encode(),
    )
    target = subprocess_target(
        "local",
        invocation,
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )

    result = run_sync(policy("local"), {"local": target})

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert result.value == ProcessReply(value="TEA")
    assert result.attempts[0].dispatch_started is True


def test_timeout_terminates_child_and_returns_sanitized_failure() -> None:
    canary = "PROCESS-STDERR-CANARY-7f98"
    code = "import sys,time; print(sys.stdin.read(), file=sys.stderr); time.sleep(10)"
    target = subprocess_target(
        "slow",
        SubprocessInvocation(
            argv=(sys.executable, "-c", code),
            input_bytes=canary.encode(),
            cancellation_poll_seconds=0.01,
        ),
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )

    started = time.monotonic()
    result = run_sync(policy("slow", total=0.2, attempt=0.1), {"slow": target})
    elapsed = time.monotonic() - started

    assert elapsed < 1
    assert result.outcome is ExecutionOutcome.EXHAUSTED
    assert result.failure_kind is FailureKind.TIMEOUT
    assert canary not in result.model_dump_json()


def test_timeout_kills_descendant_process_group(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("process-group proof requires POSIX")
    marker = tmp_path / "descendant-survived"
    descendant = (
        "import pathlib,sys,time; time.sleep(0.35); "
        "pathlib.Path(sys.argv[1]).write_text('survived')"
    )
    parent = (
        "import subprocess,sys,time; "
        "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]]); "
        "time.sleep(10)"
    )
    target = subprocess_target(
        "tree",
        SubprocessInvocation(
            argv=(sys.executable, "-c", parent, descendant, str(marker)),
            cancellation_poll_seconds=0.01,
        ),
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )

    result = run_sync(policy("tree", total=0.2, attempt=0.1), {"tree": target})
    time.sleep(0.45)

    assert result.failure_kind is FailureKind.TIMEOUT
    assert not marker.exists()


def test_cancellation_terminates_running_child() -> None:
    token = MutableCancellation()
    target = subprocess_target(
        "slow",
        SubprocessInvocation(
            argv=(sys.executable, "-c", "import time; time.sleep(10)"),
            cancellation_poll_seconds=0.01,
        ),
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )
    timer = threading.Timer(0.05, lambda: setattr(token, "cancelled", True))
    timer.start()
    try:
        result = run_sync(
            policy("slow", total=1, attempt=1),
            {"slow": target},
            cancellation=token,
        )
    finally:
        timer.cancel()

    assert result.outcome is ExecutionOutcome.CANCELLED
    assert result.attempts[0].failure_kind is FailureKind.CANCELLED


def test_invocation_factory_can_change_target_between_attempts() -> None:
    def invocation(context: AttemptContext) -> SubprocessInvocation:
        if context.attempt_number == 1:
            code = "import time; time.sleep(10)"
        else:
            code = 'print(\'{"value": "fallback"}\')'
        return SubprocessInvocation(
            argv=(sys.executable, "-c", code),
            cancellation_poll_seconds=0.01,
        )

    target = subprocess_target(
        "provider",
        invocation,
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )

    result = run_sync(
        policy("provider", "provider", total=1, attempt=0.1),
        {"provider": target},
    )

    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert result.value == ProcessReply(value="fallback")
    assert [item.failure_kind for item in result.attempts] == [
        FailureKind.TIMEOUT,
        None,
    ]


def test_malformed_response_is_retryable_only_when_policy_names_it() -> None:
    target = subprocess_target(
        "bad-json",
        SubprocessInvocation(argv=(sys.executable, "-c", "print('not-json')")),
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )

    one = run_sync(policy("bad-json"), {"bad-json": target})
    two = run_sync(
        policy(
            "bad-json",
            "bad-json",
            retryable=frozenset({FailureKind.MALFORMED_RESPONSE}),
        ),
        {"bad-json": target},
    )

    assert one.outcome is ExecutionOutcome.FAILED_SAFE
    assert len(one.attempts) == 1
    assert two.outcome is ExecutionOutcome.EXHAUSTED
    assert len(two.attempts) == 2


def test_nonzero_exit_does_not_retain_stderr() -> None:
    canary = "CHILD-ERROR-CANARY-2a11"
    code = f"import sys; print('{canary}', file=sys.stderr); raise SystemExit(7)"
    target = subprocess_target(
        "failure",
        SubprocessInvocation(argv=(sys.executable, "-c", code)),
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )

    result = run_sync(policy("failure"), {"failure": target})

    assert result.outcome is ExecutionOutcome.FAILED_SAFE
    assert result.failure_kind is FailureKind.PERMANENT
    assert canary not in result.model_dump_json()


def test_child_does_not_inherit_parent_environment_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZEO_PROCESS_PARENT_CANARY", "must-not-cross")
    code = (
        "import json,os; "
        "print(json.dumps({'value': str(os.getenv('ZEO_PROCESS_PARENT_CANARY'))}))"
    )
    target = subprocess_target(
        "isolated",
        SubprocessInvocation(argv=(sys.executable, "-c", code)),
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )

    result = run_sync(policy("isolated"), {"isolated": target})

    assert result.value == ProcessReply(value="None")


def test_invocation_repr_redacts_stdin_and_environment_values() -> None:
    canary = "INVOCATION-CANARY-865c"
    invocation = SubprocessInvocation(
        argv=(sys.executable, "-c", "pass"),
        input_bytes=canary.encode(),
        env={"PROVIDER_INPUT": canary},
    )

    assert canary not in repr(invocation)


def test_invocation_rejects_empty_or_path_resolved_executables() -> None:
    with pytest.raises(ValueError, match="contain an executable"):
        SubprocessInvocation(argv=())
    with pytest.raises(ValueError, match="absolute executable path"):
        SubprocessInvocation(argv=("python", "-c", "pass"))


def test_missing_executable_records_pre_dispatch_failure(tmp_path: Path) -> None:
    target = subprocess_target(
        "missing",
        SubprocessInvocation(argv=(str(tmp_path / "does-not-exist"),)),
        response_type=ProcessReply,
        parse_stdout=parse_reply,
    )

    result = run_sync(policy("missing"), {"missing": target})

    assert result.outcome is ExecutionOutcome.FAILED_SAFE
    assert result.attempts[0].dispatch_started is False
