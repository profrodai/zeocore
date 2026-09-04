"""Hard-timeout subprocess targets for the resilient execution runner."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TypeVar

from zeo_core.execution.models import ExecutionMode, FailureKind
from zeo_core.execution.runner import (
    AttemptContext,
    AttemptError,
    SyncExecutionTarget,
)

T = TypeVar("T")


@dataclass(frozen=True)
class SubprocessInvocation:
    """One shell-free child invocation whose request travels over stdin."""

    argv: tuple[str, ...]
    input_bytes: bytes = field(default=b"", repr=False)
    cwd: str | None = None
    env: Mapping[str, str] = field(default_factory=dict, repr=False)
    termination_grace_seconds: float = 0.5
    cancellation_poll_seconds: float = 0.1

    def __post_init__(self) -> None:
        if not self.argv:
            raise ValueError("argv must contain an executable")
        if not os.path.isabs(self.argv[0]):
            raise ValueError("argv[0] must be an absolute executable path")
        if self.termination_grace_seconds < 0:
            raise ValueError("termination_grace_seconds cannot be negative")
        if self.cancellation_poll_seconds <= 0:
            raise ValueError("cancellation_poll_seconds must be positive")


def _terminate_process_group(
    process: subprocess.Popen[bytes], grace_seconds: float
) -> None:
    """Terminate and then kill the child group without retaining its output."""

    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        return
    process.wait()


def _run_subprocess(
    context: AttemptContext,
    invocation: SubprocessInvocation,
) -> bytes:
    started = time.monotonic()
    try:
        process = subprocess.Popen(  # noqa: S603 -- argv is explicit and shell is false
            invocation.argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=invocation.cwd,
            env=dict(invocation.env),
            shell=False,
            start_new_session=os.name == "posix",
        )
    except OSError as error:
        raise AttemptError(FailureKind.PERMANENT, dispatch_started=False) from error
    pending_input: bytes | None = invocation.input_bytes
    try:
        while True:
            if context.cancellation.is_cancelled():
                _terminate_process_group(process, invocation.termination_grace_seconds)
                raise AttemptError(FailureKind.CANCELLED)
            remaining = context.timeout_seconds - (time.monotonic() - started)
            if remaining <= 0:
                _terminate_process_group(process, invocation.termination_grace_seconds)
                raise AttemptError(FailureKind.TIMEOUT)
            poll = min(remaining, invocation.cancellation_poll_seconds)
            try:
                stdout, _stderr = process.communicate(
                    input=pending_input,
                    timeout=poll,
                )
            except subprocess.TimeoutExpired:
                pending_input = None
                continue
            if process.returncode != 0:
                raise AttemptError(FailureKind.PERMANENT)
            return stdout
    except BaseException:
        _terminate_process_group(process, invocation.termination_grace_seconds)
        raise


def subprocess_target(
    target_id: str,
    invocation: SubprocessInvocation | Callable[[AttemptContext], SubprocessInvocation],
    *,
    response_type: type[T],
    parse_stdout: Callable[[bytes], T],
    execution_mode: ExecutionMode = ExecutionMode.LIVE,
) -> SyncExecutionTarget[T]:
    """Build one hard-timeout target around a shell-free subprocess."""

    def call(context: AttemptContext) -> T:
        spec = invocation(context) if callable(invocation) else invocation
        output = _run_subprocess(context, spec)
        try:
            return parse_stdout(output)
        except Exception as error:
            raise AttemptError(FailureKind.MALFORMED_RESPONSE) from error

    return SyncExecutionTarget(
        target_id=target_id,
        response_type=response_type,
        invoke=call,
        execution_mode=execution_mode,
    )
