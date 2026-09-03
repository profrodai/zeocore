"""
macOS Keychain-backed `SecretStore`, ZC0-KERNEL-SEAM-01 implementation-order
step 3 ("macOS Keychain custody, injected subprocess runner, synthetic
canary tests; public values carry only SecretRef").

Implements `zeo_core.contracts.connections.protocols.SecretStore` against
the macOS `/usr/bin/security` CLI (`add-generic-password`,
`find-generic-password`, `delete-generic-password`) via an injected
`SubprocessRunner` (subprocess_runner.py) -- never `subprocess` directly --
so every behavioral test in this stream runs against a fake runner that
never touches a real keychain.

WHY NO NEW DEPENDENCY: SOW-01 section 3a's new-dependency ruling is
explicit -- "`keyring`, if proposed, is a new dependency and returns for a
ruling; the packet specifies an injected subprocess runner." This module
therefore shells out to the `security` binary that ships with every macOS
install rather than adding the `keyring` PyPI package.

CUSTODY MODEL: `SecretRef.handle` is an opaque, kernel-minted locator of
the shape `zc0-kc:<organization_id>:<uuid4>` -- never derived from or
related to the material itself (a handle derived from the material, e.g.
a hash, would narrow the material's keyspace to anyone who could brute-
force-compare hashes; an unrelated random locator carries no such risk).
The Keychain item's account name IS the handle; the service name is this
store's configured `service_prefix`, constant across all items so a
single `security` invocation with the right account can always find the
right item, and organization scoping is enforced by this class checking
`organization_id` against the handle's embedded organization segment
BEFORE issuing any `security` command -- never by trusting the Keychain
item's own attributes, which `security` does not scope by caller-supplied
organization at all.

RESIDUAL DISCLOSURE CHANNEL, NOT CLOSED BY THIS ADAPTER, ESCALATED TO
MASTER (see this stream's SOW-05): the `security` CLI has exactly two
non-interactive ways to pass a password to `add-generic-password` --
argv (`-w <password>`) or a hex string (`-X <hex>`, same exposure class).
Apple's own `security add-generic-password` usage text calls `-w`/`-p`
argv passing "insecure" and documents interactive stdin (`-w` as the last,
valueless option) as the safe alternative -- but this stream measured
interactive stdin directly and found it unreliable for programmatic use:
a single newline-terminated value on stdin is read as the FIRST of two
required confirm-match prompts, the second prompt reads EOF as an empty
string, "passwords don't match" fires, and a THIRD read (again EOF, again
empty) is silently accepted -- `add-generic-password` returns exit 0
having stored an EMPTY password, not the intended material, not raising
any error a caller could detect. That failure mode (a wrong-but-successful
write) is worse than the argv channel it was meant to avoid, so this
adapter uses argv `-w`. The tradeoff: for the lifetime of the `security`
subprocess this creates, `material` is visible via `ps -ww` to any other
process running as the same local user (verified directly: 5/5 samples of
a concurrently polling `ps -ww` caught the exact argv value). An
environment-variable channel was considered as a lower-exposure
alternative and rejected on two independent grounds, both verified
directly rather than assumed: (1) `security` has no environment-variable
password option to receive one at all, and (2) the premise that env vars
are less exposed than argv on macOS is ITSELF FALSE for a same-user
caller -- `ps -wwE` shows a child process's full environment to any
same-user local process exactly as `ps -ww` shows its argv (verified
directly; this stream's own first pass at this comparison used a plain
`ps eww` invocation against a backgrounded shell builtin that never
actually propagated the test env var, produced a false negative, and
wrongly recorded env vars as safe -- caught and corrected before this
module shipped, see test_macos_keychain.py's
test_environment_variables_are_shown_via_ps_capital_e_same_as_argv). There is
therefore no lower-exposure subprocess-argument channel to move to; the
exposure is inherent to invoking `security` as a subprocess at all, not a
consequence of choosing argv specifically. This is a real, bounded
(same-user, local-machine, subprocess-lifetime-only) channel that the
protocol's "no secret material appears in... any accidental channel" bar
does not fully close for `put` and `rotate` (the only two methods that
carry raw `material`) given the stock `security` CLI's constraints --
recorded here, tested explicitly
(test_macos_keychain.py's TestArgvExposureIsRealAndBounded), and escalated
rather than silently shipped as fully closed.

Must NOT contain: a permissive default, cross-organization resolution, a
general-purpose reveal method, or any accidental echo of `material` into
a log, exception, or return value beyond the one argv channel named above.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from zeo_core.connections.adapters.subprocess_runner import (
    CompletedSubprocess,
    RealSubprocessRunner,
    SubprocessRunner,
)
from zeo_core.contracts.connections.identity import OrganizationId, SecretRef
from zeo_core.contracts.connections.verdicts import SecretHealth, SecretResolution

#: Prefix distinguishing this store's Keychain items from anything else a
#: caller's keychain might hold. Not a secret; purely a namespace.
_HANDLE_PREFIX = "zc0-kc"

#: `security` exit codes this adapter treats as "item not found" rather
#: than an unexpected failure -- errSecItemNotFound (-25300) surfaces as
#: 44 on some macOS versions and 36 on others (observed directly across
#: this session's probes); both are treated identically as absence, never
#: as a crash, since a caller checking `health` must get a value back, not
#: an exception (protocol bound: "must be returned, never raised").
_ITEM_NOT_FOUND_EXIT_CODES = frozenset({36, 44})


class SecretMaterialError(Exception):
    """
    Raised by `put`/`rotate`/`resolve` on an unexpected Keychain failure
    (anything other than "item not found", which is not an error for
    `health` and is a `KeyError`-shaped condition for `resolve`/`rotate`/
    `delete`). Never constructed with `material` as an argument or embedded
    in its message -- every raise site in this module passes only the
    handle, the organization id, and the `security` exit code/stderr text,
    which is diagnostic (a keychain lock state, a malformed account name)
    and never the caller-supplied secret.
    """


class SecretNotFoundError(Exception):
    """Raised by `resolve`, `rotate`, and `delete` when `ref` does not
    resolve to a Keychain item under `organization_id`'s scope. Carries
    only the handle (opaque, not secret) and organization id."""


class CrossOrganizationAccessError(Exception):
    """
    Raised when `organization_id` does not match the organization segment
    encoded in `ref.handle`. Per the protocol's bound 1 obligation ("must
    reject a `ref` from a different organization than `organization_id`
    rather than silently resolving it"): checked BEFORE any `security`
    invocation, so a cross-organization call never even reaches the
    Keychain.
    """


def _parse_handle_organization(handle: str) -> str | None:
    """
    Return the organization segment encoded in `handle`, or None if
    `handle` is not shaped like a handle this store minted. Pure string
    parsing; never touches the Keychain, never raises -- a malformed or
    foreign handle is reported as "no organization I recognize" rather
    than crashing, so the caller in `_check_scope` can turn it into the
    correct closed-taxonomy error instead of an unhandled parse exception.
    """
    parts = handle.split(":", 2)
    if len(parts) != 3 or parts[0] != _HANDLE_PREFIX:
        return None
    return parts[1]


class KeychainSecretStore:
    """
    `SecretStore` implementation backed by the macOS Keychain.

    Structurally satisfies `zeo_core.contracts.connections.protocols.
    SecretStore` (`runtime_checkable`); construct with an injected
    `SubprocessRunner` in tests (never the real `RealSubprocessRunner`,
    which would touch an actual keychain) and the real one (the default)
    everywhere else.
    """

    def __init__(
        self,
        *,
        service_prefix: str,
        runner: SubprocessRunner | None = None,
        clock: Callable[[], datetime] | None = None,
        resolution_ttl_seconds: int = 300,
    ) -> None:
        if not service_prefix.strip():
            raise ValueError("service_prefix must be non-empty")
        if resolution_ttl_seconds <= 0:
            raise ValueError("resolution_ttl_seconds must be positive")
        self._service_prefix = service_prefix
        self._runner: SubprocessRunner = runner or RealSubprocessRunner()
        self._clock: Callable[[], datetime] = clock or (lambda: datetime.now(UTC))
        self._resolution_ttl_seconds = resolution_ttl_seconds

    # -- scope enforcement -------------------------------------------------

    def _check_scope(self, *, ref: SecretRef, organization_id: OrganizationId) -> None:
        encoded_org = _parse_handle_organization(ref.handle)
        if encoded_org is None or encoded_org != organization_id.value:
            raise CrossOrganizationAccessError(
                "ref does not belong to organization_id "
                f"(handle_prefix_ok={encoded_org is not None})"
            )

    # -- security(1) plumbing ----------------------------------------------

    def _run_security(self, args: list[str]) -> CompletedSubprocess:
        return self._runner.run(["/usr/bin/security", *args])

    def _account_for(self, *, organization_id: OrganizationId) -> str:
        return f"{_HANDLE_PREFIX}:{organization_id.value}:{uuid.uuid4()}"

    # -- SecretStore protocol -----------------------------------------------

    def put(self, *, organization_id: OrganizationId, material: str) -> SecretRef:
        if not material:
            raise ValueError("material must be non-empty")
        account = self._account_for(organization_id=organization_id)
        result = self._run_security(
            [
                "add-generic-password",
                "-a",
                account,
                "-s",
                self._service_prefix,
                "-w",
                material,
            ]
        )
        # `material` is a local variable only; it goes out of scope when
        # this method returns and is never assigned to `self` or any
        # other object that would outlive this call.
        if result.returncode != 0:
            raise SecretMaterialError(
                f"keychain add-generic-password failed, exit={result.returncode} "
                f"account={account!r}"
            )
        return SecretRef(handle=account)

    def resolve(
        self, *, ref: SecretRef, organization_id: OrganizationId
    ) -> SecretResolution:
        self._check_scope(ref=ref, organization_id=organization_id)
        result = self._run_security(
            [
                "find-generic-password",
                "-a",
                ref.handle,
                "-s",
                self._service_prefix,
                "-w",
            ]
        )
        if result.returncode in _ITEM_NOT_FOUND_EXIT_CODES:
            raise SecretNotFoundError(f"no secret under handle {ref.handle!r}")
        if result.returncode != 0:
            raise SecretMaterialError(
                f"keychain find-generic-password failed, exit={result.returncode} "
                f"handle={ref.handle!r}"
            )
        # `result.stdout` IS the resolved material -- it is read here only
        # to confirm the item exists and is readable; it is deliberately
        # discarded (never assigned beyond this local check, never
        # returned, never logged). SecretResolution is a broker-only
        # lease: it carries `ref` and a lease id, never material. The
        # (not-yet-built, out of this step's scope) custody-adapter-
        # internal dispatch path is the only future caller authorized to
        # re-resolve material behind a lease, per the protocol's own
        # docstring.
        del result
        resolved_at = self._clock()
        expires_at = resolved_at + timedelta(seconds=self._resolution_ttl_seconds)
        return SecretResolution(
            ref=ref,
            lease_id=str(uuid.uuid4()),
            resolved_at=resolved_at,
            expires_at=expires_at,
        )

    def rotate(
        self, *, ref: SecretRef, organization_id: OrganizationId, material: str
    ) -> SecretRef:
        if not material:
            raise ValueError("material must be non-empty")
        self._check_scope(ref=ref, organization_id=organization_id)
        result = self._run_security(
            [
                "add-generic-password",
                "-a",
                ref.handle,
                "-s",
                self._service_prefix,
                "-U",
                "-w",
                material,
            ]
        )
        if result.returncode != 0:
            raise SecretMaterialError(
                f"keychain rotate (add-generic-password -U) failed, "
                f"exit={result.returncode} handle={ref.handle!r}"
            )
        return ref

    def delete(self, *, ref: SecretRef, organization_id: OrganizationId) -> None:
        self._check_scope(ref=ref, organization_id=organization_id)
        result = self._run_security(
            [
                "delete-generic-password",
                "-a",
                ref.handle,
                "-s",
                self._service_prefix,
            ]
        )
        if (
            result.returncode != 0
            and result.returncode not in _ITEM_NOT_FOUND_EXIT_CODES
        ):
            raise SecretMaterialError(
                f"keychain delete-generic-password failed, "
                f"exit={result.returncode} handle={ref.handle!r}"
            )
        # Deletion is idempotent: an already-absent item is not an error
        # (delete's job is "make it gone," which is already true). This
        # never touches historical execution/receipt evidence -- this
        # store has no method that reads or writes those; they belong to
        # ConnectionStore (step 4), a wholly separate protocol.

    def health(
        self, *, ref: SecretRef, organization_id: OrganizationId
    ) -> SecretHealth:
        checked_at = self._clock()
        try:
            self._check_scope(ref=ref, organization_id=organization_id)
        except CrossOrganizationAccessError:
            return SecretHealth(
                reachable=False,
                checked_at=checked_at,
                detail="ref does not belong to organization_id",
            )
        result = self._run_security(
            [
                "find-generic-password",
                "-a",
                ref.handle,
                "-s",
                self._service_prefix,
            ]
        )
        if result.returncode == 0:
            return SecretHealth(reachable=True, checked_at=checked_at)
        if result.returncode in _ITEM_NOT_FOUND_EXIT_CODES:
            return SecretHealth(
                reachable=False,
                checked_at=checked_at,
                detail="secret not found in keychain",
            )
        return SecretHealth(
            reachable=False,
            checked_at=checked_at,
            detail=f"keychain unreachable, exit={result.returncode}",
        )
