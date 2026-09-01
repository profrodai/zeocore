"""
Regression test for `probe_with_retry` in tools/release-check.sh.

Bug (found 2026-09-01, fixed by this stream): on a connection failure,
curl already writes "000" to its own stdout (the `-w '%{http_code}'`
output) AND exits non-zero (verified: exit 6 against an unresolvable
host). The old code was:

    status=$(curl ... 2>/dev/null || echo "000")

`|| echo "000"` fires on that SAME non-zero exit, so command
substitution concatenates curl's own "000" with the fallback "000",
producing "000000" (6 characters) -- not a status code that exists.
The classifier at release-check.sh only allow-lists {200,404} and
falls through to INCONCLUSIVE for anything else, so this never flipped
a verdict (the check still failed closed) -- but the diagnostic a human
reads said "-> 000000", which is not a real HTTP status and undermines
the tool's whole purpose of explaining what happened in plain terms.

This test is bash-level, not Python-level: `probe_with_retry` is a
shell function with no Python equivalent to import. Rather than
hand-duplicate the function body (which could silently drift from the
real script), this test EXTRACTS the live function text out of
tools/release-check.sh by line range and sources it into a throwaway
bash script, so it always exercises the current source, not a copy.
That is the honest seam available here: release-check.sh is a
`set -uo pipefail` top-level script with required positional args and
no "function-library" mode, so it cannot be `source`d whole without
running the entire release gate.

No real network dependency: `.invalid` is a reserved TLD (RFC 2606)
that is guaranteed to never resolve, so this fails fast (~10ms) and
deterministically in any environment, sandboxed or not.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RELEASE_CHECK = REPO_ROOT / "tools" / "release-check.sh"

UNRESOLVABLE_URL = "https://pypi.invalid-does-not-resolve.example/x"


def _extract_probe_with_retry() -> str:
    """Pull the live `probe_with_retry` function (plus the retry-tuning
    globals it reads) straight out of tools/release-check.sh, so this
    test always runs the CURRENT function body, never a hand-copied one
    that could drift from it unnoticed.
    """
    text = RELEASE_CHECK.read_text()

    globals_match = re.search(
        r"^RETRY_ATTEMPTS=.*$\n^RETRY_WAIT_SECONDS=.*$",
        text,
        re.MULTILINE,
    )
    assert globals_match, (
        "tools/release-check.sh no longer declares RETRY_ATTEMPTS/"
        "RETRY_WAIT_SECONDS on consecutive lines -- update this test's "
        "extraction pattern to match the new shape."
    )

    func_match = re.search(
        r"^probe_with_retry\(\) \{.*?^\}$",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert func_match, (
        "tools/release-check.sh no longer defines probe_with_retry() in "
        "the expected `name() { ... }` shape -- update this test's "
        "extraction pattern to match the new shape."
    )

    return globals_match.group(0) + "\n" + func_match.group(0) + "\n"


def _run_probe_with_retry(url: str, *, retry_attempts: int = 1) -> tuple[str, int]:
    """Run the extracted probe_with_retry against `url` in a real bash
    subprocess (bash 3.2 compatibility matters here -- the fix relies on
    `[[ =~ ]]`, verified working on macOS's shipped bash 3.2). Returns
    (stdout_status, exit_code). retry_attempts=1 keeps the unreachable-
    host case fast (no sleep/backoff) since we already know the first
    attempt will fail deterministically.
    """
    func_src = _extract_probe_with_retry()
    # Override RETRY_ATTEMPTS after sourcing so the test stays fast
    # regardless of the real script's configured retry count.
    script = (
        "set -uo pipefail\n"
        + func_src
        + f"RETRY_ATTEMPTS={retry_attempts}\n"
        + 'probe_with_retry "$1"\n'
    )
    bash = shutil.which("bash") or "/bin/bash"
    proc = subprocess.run(  # noqa: S603 -- fixed argv, resolved bash binary, test-only, no shell
        [bash, "-c", script, "--", url],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return proc.stdout.strip(), proc.returncode


def test_probe_with_retry_returns_exactly_000_on_unreachable_host() -> None:
    """The regression: an unreachable host must yield the literal string
    "000" (3 characters) -- not "000000", not anything else. Asserting
    only "not 200/404" would have passed on the buggy "000000" output
    too, so this pins the EXACT string.
    """
    status, _exit_code = _run_probe_with_retry(UNRESOLVABLE_URL)
    assert status == "000", (
        f"probe_with_retry printed {status!r} (length {len(status)}) for "
        f"an unreachable host; expected the exact 3-character string "
        "'000'. A doubled '000000' means the || echo fallback fired "
        "on top of curl's own already-printed status."
    )


def test_probe_with_retry_output_is_three_characters() -> None:
    """Belt-and-suspenders on the length itself, independent of the
    literal value, since "wrong length" is the exact shape of this bug.
    """
    status, _exit_code = _run_probe_with_retry(UNRESOLVABLE_URL)
    assert len(status) == 3, (
        f"probe_with_retry printed {status!r}, which is {len(status)} "
        "characters long; every return path must yield a clean "
        "3-character HTTP-status-shaped string."
    )
