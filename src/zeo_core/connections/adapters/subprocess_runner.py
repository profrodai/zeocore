"""
Injected subprocess runner for macOS Keychain custody, per the packet's
binding order item 3: "macOS Keychain custody, injected subprocess
runner, synthetic canary tests." This module has no keychain-specific
logic; it exists so `macos_keychain.py` never calls `subprocess.run`
directly, letting tests substitute a fake runner that never touches a
real keychain and letting a future caller substitute a differently
sandboxed real runner without changing the adapter's custody logic.

Must NOT contain: keychain-specific argument construction (that is
`macos_keychain.py`'s job), secret material handling beyond passing
argv/stdin through unmodified, logging of `args` or captured output
(a caller that logs the returned `CompletedSubprocess` is responsible for
knowing whether that output can carry secret material -- this module does
not log anything itself).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CompletedSubprocess:
    """
    The minimal result shape `macos_keychain.py` needs from a subprocess
    invocation: exit code, stdout, stderr. A plain dataclass, not a
    pydantic model -- this type is never part of the public connections
    contract surface (it is not exported from `zeo_core.connections`) and
    carries no redaction obligation of its own; whatever data it holds is
    exactly what the real `security` CLI printed, and the adapter code
    that reads it is responsible for not re-exposing anything sensitive
    it might contain (see macos_keychain.py's handling of `find-generic-
    password -w` output, which is the one call whose stdout IS the secret
    material and is never logged, echoed, or included in an exception).
    """

    returncode: int
    stdout: str
    stderr: str


class SubprocessRunner(Protocol):
    """
    Structural type for anything that can run an argv list and return its
    result. `macos_keychain.py` depends on this Protocol, never on
    `subprocess` directly, so tests inject `FakeSubprocessRunner` (this
    module) instead of shelling out to a real keychain.
    """

    def run(self, args: list[str]) -> CompletedSubprocess:
        """
        Run `args` (argv[0] is the executable) to completion and return
        its result. Must not raise on a nonzero exit -- the caller reads
        `returncode` -- so a Keychain "item not found" (`security` exit
        44/36) is an ordinary return, not an exception path a caller must
        guess about.
        """
        ...


class RealSubprocessRunner:
    """
    The production `SubprocessRunner`: runs `args` via `subprocess.run`
    with no shell interpolation (`shell=False`, the default -- argv is
    passed as a list, never a formatted string, so no argument can break
    out into a second shell command). Captures stdout/stderr as text;
    never raises on nonzero exit (`check=False`) so the adapter can read
    `returncode` itself.
    """

    def run(self, args: list[str]) -> CompletedSubprocess:
        completed = subprocess.run(  # noqa: S603
            args,
            capture_output=True,
            text=True,
            check=False,
        )
        return CompletedSubprocess(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
