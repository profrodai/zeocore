"""
Injected subprocess runner for macOS Keychain custody, per the packet's
binding order item 3: "macOS Keychain custody, injected subprocess
runner, synthetic canary tests." This module has no keychain-specific
logic; it exists so `macos_keychain.py` never calls `subprocess.run`
directly, letting tests substitute a fake runner that never touches a
real keychain and letting a future caller substitute a differently
sandboxed real runner without changing the adapter's custody logic.

SECRET-TRANSPORT BOUND (Principal decision msg_e79f76af, carried into this
stream by Master's re-brief after SOW-05): "secret material MUST NOT
appear in argv, process titles, environment variables, command objects,
repr/str, logs, exceptions, pytest output, or recorded subprocess
diagnostics. The injected runner must model argv separately from secret
stdin." `run_with_secret_stdin` below is the ONE method on this Protocol
that may carry `material` at all, and its signature makes the bound
structural rather than conventional: `argv` is typed `list[str]` with no
parameter through which a caller could smuggle material into it, and
`secret_lines` is a SEPARATE parameter feeding only the subprocess's
stdin pipe, never joined into `argv`, never interpolated into a shell
string (there is no shell -- `shell=False` throughout, argv stays a list).
A caller cannot construct a call that puts `secret_lines`' content into
`argv` without editing this module's own `run_with_secret_stdin` body --
the separation is enforced by the parameter list, not by a comment
promising the caller will behave.

Must NOT contain: keychain-specific argument construction (that is
`macos_keychain.py`'s job), logging of `args`/`secret_lines`/captured
output (a caller that logs the returned `CompletedSubprocess` is
responsible for knowing whether that output can carry secret material --
this module does not log anything itself, and `RealSubprocessRunner`
below never writes `secret_lines` anywhere except the child's stdin pipe).
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

    Two methods, deliberately not one: `run` is for argv-only invocations
    that carry no secret material at all (`find-generic-password` without
    `-w`, `delete-generic-password`). `run_with_secret_stdin` is the ONLY
    method that may transport `material` -- it is a structurally distinct
    call shape, not an optional parameter on `run`, so a caller cannot
    accidentally reach for `run` and pass material as an argv element by
    habit; the two call shapes look different at every call site.
    """

    def run(self, args: list[str]) -> CompletedSubprocess:
        """
        Run `args` (argv[0] is the executable) to completion and return
        its result. Must not raise on a nonzero exit -- the caller reads
        `returncode` -- so a Keychain "item not found" (`security` exit
        44/36) is an ordinary return, not an exception path a caller must
        guess about. `args` must never contain secret material -- use
        `run_with_secret_stdin` for any call that does.
        """
        ...

    def run_with_secret_stdin(
        self, args: list[str], *, secret_lines: list[str]
    ) -> CompletedSubprocess:
        """
        Run `args` exactly like `run`, except `secret_lines` is written to
        the child process's stdin, one line per list element (each
        terminated with a newline), and closed once fully written. `args`
        itself must still never contain material -- `secret_lines` is the
        only channel through which this call may carry it. Per the
        Principal's bound, a `security add-generic-password ... -w` call
        (interactive form: `-w` as the FINAL argv element, no value)
        prompts for the password TWICE (a confirm-match read), so a
        caller storing new material passes `secret_lines=[material,
        material]` -- verified directly against the real `/usr/bin/
        security` binary before this method's caller relies on it (see
        macos_keychain.py's module docstring and
        test_macos_keychain.py's TestStdinTransportProvenOnRealExecutable).
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

    def run_with_secret_stdin(
        self, args: list[str], *, secret_lines: list[str]
    ) -> CompletedSubprocess:
        # `input=` on subprocess.run feeds the child's stdin and is never
        # placed on argv, never becomes a process-title-visible value,
        # and is not an environment variable -- it is piped bytes on a
        # pipe the OS gives only to the parent and the child. This is the
        # one place in this module `secret_lines` is read; it is not
        # copied into a local that outlives this call, not logged, and
        # not included in the returned CompletedSubprocess beyond
        # whatever the child itself chose to print (proven empty for
        # `security`'s own diagnostics in the adapter's tests).
        stdin_payload = "".join(f"{line}\n" for line in secret_lines)
        completed = subprocess.run(  # noqa: S603
            args,
            input=stdin_payload,
            capture_output=True,
            text=True,
            check=False,
        )
        del stdin_payload
        return CompletedSubprocess(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
