"""
In-memory fake `SubprocessRunner` that never touches a real keychain.

Simulates just enough of `/usr/bin/security`'s `add-generic-password`,
`find-generic-password`, and `delete-generic-password` behavior for
`KeychainSecretStore`'s tests to run deterministically, offline, and with
no risk of leaving real Keychain items behind. It does NOT simulate every
`security` quirk (e.g. the interactive-stdin double-prompt behavior this
stream measured directly against the real binary) -- only the argv shape
`macos_keychain.py` actually sends.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from zeo_core.connections.adapters.subprocess_runner import CompletedSubprocess

_NOT_FOUND_EXIT = 44


@dataclass
class FakeSubprocessRunner:
    """
    Records every invocation (`self.calls`, a list of argv lists) and
    simulates a tiny in-memory keychain keyed by (account, service).

    `self.calls` is the RECON surface for tests that must prove `material`
    was passed via argv and nowhere else (the argv-exposure tests) --
    reading it is not a leak on this fake's part, it is this fake
    deliberately exposing what a real subprocess invocation's argv would
    have contained, for a test to assert against.
    """

    calls: list[list[str]] = field(default_factory=list)
    _store: dict[tuple[str, str], str] = field(default_factory=dict)
    force_exit_code: int | None = None
    force_stderr: str = ""

    def run(self, args: list[str]) -> CompletedSubprocess:
        self.calls.append(list(args))
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
            material = _arg_value(args, "-w")
            self._store[key] = material or ""
            return CompletedSubprocess(returncode=0, stdout="", stderr="")

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
