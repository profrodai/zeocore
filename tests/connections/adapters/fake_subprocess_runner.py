"""
In-memory fake `SubprocessRunner` that never touches a real keychain.

Simulates just enough of `/usr/bin/security`'s `add-generic-password`,
`find-generic-password`, and `delete-generic-password` behavior for
`KeychainSecretStore`'s tests to run deterministically, offline, and with
no risk of leaving real Keychain items behind -- including the
interactive-stdin double-prompt confirm-match semantics this stream
measured directly against the real binary (see
test_macos_keychain.py's TestStdinTransportProvenOnRealExecutable), so a
test written against this fake and a test written against the real
executable exercise the same logical behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from zeo_core.connections.adapters.subprocess_runner import CompletedSubprocess

_NOT_FOUND_EXIT = 44


@dataclass
class FakeSubprocessRunner:
    """
    Records every argv-only invocation (`self.calls`) and every
    secret-stdin invocation (`self.stdin_calls`, argv and line-count only
    -- see below) separately, and simulates a tiny in-memory keychain
    keyed by (account, service).

    `self.calls`/`self.stdin_calls` are the RECON surface for tests that
    must prove `material` was passed via stdin and NEVER argv -- reading
    them is not a leak on this fake's part, it is this fake deliberately
    exposing what a real subprocess invocation would have received, for a
    test to assert against. `self.stdin_calls` stores only the ARGV of a
    secret-stdin call plus how many lines stdin carried, never the lines'
    content itself, by construction (see `run_with_secret_stdin` below) --
    matching the real store's own guarantee.
    """

    calls: list[list[str]] = field(default_factory=list)
    stdin_calls: list[tuple[list[str], int]] = field(default_factory=list)
    _store: dict[tuple[str, str], str] = field(default_factory=dict)
    force_exit_code: int | None = None
    force_stderr: str = ""

    def run(self, args: list[str]) -> CompletedSubprocess:
        self.calls.append(list(args))
        return self._dispatch(args, secret_lines=None)

    def run_with_secret_stdin(
        self, args: list[str], *, secret_lines: list[str]
    ) -> CompletedSubprocess:
        # Deliberately records ONLY the argv and the line COUNT, never
        # `secret_lines` itself -- this fake's own recon surface must not
        # become a second place material could be read back from, which
        # would make FakeSubprocessRunner itself an accidental channel in
        # every test that uses it.
        self.stdin_calls.append((list(args), len(secret_lines)))
        return self._dispatch(args, secret_lines=secret_lines)

    def _dispatch(
        self, args: list[str], *, secret_lines: list[str] | None
    ) -> CompletedSubprocess:
        if self.force_exit_code is not None:
            return CompletedSubprocess(
                returncode=self.force_exit_code, stdout="", stderr=self.force_stderr
            )

        command = args[1] if len(args) > 1 else ""
        account = _arg_value(args, "-a")
        service = _arg_value(args, "-s")
        key = (account or "", service or "")

        if command == "add-generic-password":
            update = "-U" in args
            if key in self._store and not update:
                return CompletedSubprocess(
                    returncode=45, stdout="", stderr="item already exists"
                )
            material = _resolve_material(args, secret_lines)
            if material is None:
                # Mirrors the real binary's measured confirm-match
                # failure mode: fewer than two matching stdin lines ->
                # an EMPTY password is stored, exit 0, no error surfaced
                # -- this fake exists partly so a caller shape that would
                # trigger this on the real binary fails the SAME way here.
                self._store[key] = ""
                return CompletedSubprocess(
                    returncode=0,
                    stdout="",
                    stderr="password data for new item: retype password for new item: ",
                )
            self._store[key] = material
            return CompletedSubprocess(
                returncode=0,
                stdout="",
                stderr=(
                    "password data for new item: retype password for new item: "
                    if secret_lines is not None
                    else ""
                ),
            )

        if command == "find-generic-password":
            if key not in self._store:
                return CompletedSubprocess(
                    returncode=_NOT_FOUND_EXIT, stdout="", stderr="item not found"
                )
            wants_password = "-w" in args
            stdout = self._store[key] if wants_password else ""
            return CompletedSubprocess(returncode=0, stdout=stdout, stderr="")

        if command == "delete-generic-password":
            if key not in self._store:
                return CompletedSubprocess(
                    returncode=_NOT_FOUND_EXIT, stdout="", stderr="item not found"
                )
            del self._store[key]
            return CompletedSubprocess(returncode=0, stdout="", stderr="")

        return CompletedSubprocess(returncode=1, stdout="", stderr="unknown command")


def _resolve_material(args: list[str], secret_lines: list[str] | None) -> str | None:
    """
    Mirrors `security add-generic-password ... -w` (interactive form,
    `-w` as the final argv element, no value): the caller must supply
    exactly two matching lines on stdin (the confirm-match prompt this
    stream measured on the real binary). Fewer than two lines, or two
    lines that disagree, is the "passwords don't match" -> empty-password
    failure mode; this returns None in exactly that case so `_dispatch`
    can store the empty string, matching the real binary's exit-0,
    wrong-material behavior rather than raising -- the whole point of
    this fake is to let a caller's shape be wrong in the SAME way the
    real binary would let it be wrong.
    """
    if args and args[-1] != "-w":
        return None
    if secret_lines is None or len(secret_lines) < 2:
        return None
    if secret_lines[0] != secret_lines[1]:
        return None
    return secret_lines[0]


def _arg_value(args: list[str], flag: str) -> str | None:
    if flag not in args:
        return None
    idx = args.index(flag)
    if idx + 1 >= len(args):
        return None
    nxt = args[idx + 1]
    if nxt.startswith("-"):
        return None
    return nxt
