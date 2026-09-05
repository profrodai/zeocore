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

SECRET-TRANSPORT BOUND AND ITS CORRECTION HISTORY (append-don't-revert,
per doctrine section 5): this module's first revision shipped `put`/
`rotate` on argv `-w <material>` and escalated the resulting `ps`
visibility as an unclosed channel (this stream's SOW-05). That escalation
was answered by the Principal's own step-three lease (msg_e79f76af),
which Master had not yet passed down at the time SOW-05 was written:
"secret material MUST NOT appear in argv, process titles, environment
variables, command objects, repr/str, logs, exceptions, pytest output, or
recorded subprocess diagnostics... [use] `-w` as the final option and
supply a synthetic secret through stdin only after the stream proves that
path works on the actual macOS executable without echo or prompt
leakage." SOW-05 also carried a FALSE categorical claim -- "interactive
stdin is unreliable for programmatic use" -- based on a real but narrow
defect in that revision's OWN probe: a SINGLE newline-terminated stdin
value leaves `add-generic-password`'s second confirm-match read at EOF,
which genuinely does store an empty password at exit 0. Master reproduced
this exact failure as the control case, then reproduced the CORRECT shape
-- `secret_lines=[material, material]`, i.e. the value fed TWICE,
matching the real double-prompt -- and it works, verified 3/3 runs,
storage confirmed byte-exact via `find-generic-password -w`. This stream
independently re-verified both findings against the real
`/usr/bin/security` binary before writing this revision (see
test_macos_keychain.py's TestStdinTransportProvenOnRealExecutable) rather
than accepting the correction on authority alone. The single-value
failure mode is now recorded as exactly what it is -- a caller-shape bug
in a probe, not a platform limitation -- and `put`/`rotate` below use
`SubprocessRunner.run_with_secret_stdin` with `secret_lines=[material,
material]`, `-w` as the FINAL argv element (never followed by a value),
so `material` is structurally incapable of reaching `args` -- the
Protocol's own signature (subprocess_runner.py) separates the two
parameters, not a comment promising the caller will behave. `-A` (broad,
unprompted app access) is never passed; this store relies on the default
ACL (the creating app -- `/usr/bin/security` itself, re-invoked -- stays
trusted across calls, verified directly during recon: `-T ""` denies even
`security`'s own later invocations and was rejected for that reason, not
adopted).

`security`'s own confirm-match prompts ("password data for new item:
retype password for new item: ") land on stderr, never stdout, and never
contain `material` itself -- verified directly, and asserted by
`test_stdin_transport_diagnostics_never_carry_material_on_the_real_binary`.

Must NOT contain: a permissive default, cross-organization resolution, a
general-purpose reveal method, `-A` broad access, or any accidental echo
of `material` into argv, a process title, an environment variable, a log,
an exception, or a return value.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, TypeVar, cast

if TYPE_CHECKING:
    from zeo_core.connections.orchestration import (
        EffectDispatchRequest,
        EffectDispatchResult,
        ReconciliationResult,
    )

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
_CustodyResult = TypeVar("_CustodyResult")


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
        self._leases: dict[str, tuple[SecretRef, OrganizationId, datetime]] = {}
        self._lease_lock = threading.Lock()

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

    def _run_security_with_secret(
        self, args: list[str], *, material: str
    ) -> CompletedSubprocess:
        # `args` must never contain `material` -- callers pass ONLY the
        # non-secret argv (ending in a bare "-w", per the Principal's
        # bound); `material` reaches the child exclusively through
        # `run_with_secret_stdin`'s `secret_lines` parameter, fed TWICE
        # to satisfy security(1)'s measured confirm-match prompt (see
        # this module's docstring and
        # TestStdinTransportProvenOnRealExecutable). This is the ONLY
        # place in this class that reads `material` into a call.
        if args and args[-1] != "-w":
            raise ValueError(
                "secret-carrying security invocations must end in a bare "
                "-w (interactive stdin form); got a differently-shaped "
                "argv, which would risk material landing in argv instead"
            )
        return self._runner.run_with_secret_stdin(
            ["/usr/bin/security", *args], secret_lines=[material, material]
        )

    def _account_for(self, *, organization_id: OrganizationId) -> str:
        return f"{_HANDLE_PREFIX}:{organization_id.value}:{uuid.uuid4()}"

    # -- SecretStore protocol -----------------------------------------------

    def put(self, *, organization_id: OrganizationId, material: str) -> SecretRef:
        if not material:
            raise ValueError("material must be non-empty")
        account = self._account_for(organization_id=organization_id)
        result = self._run_security_with_secret(
            [
                "add-generic-password",
                "-a",
                account,
                "-s",
                self._service_prefix,
                "-w",
            ],
            material=material,
        )
        # `material` is a local variable only; it goes out of scope when
        # this method returns and is never assigned to `self` or any
        # other object that would outlive this call. It was never placed
        # on `args` above -- `_run_security_with_secret` enforces that
        # the argv it receives ends in a bare "-w", and `material` only
        # ever travels through `run_with_secret_stdin`'s `secret_lines`.
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
        # `_dispatch_with_resolution` is the only custody-internal caller
        # authorized to re-resolve material behind this lease. Provider
        # code reaches it through KeychainEffectDispatcher, never through a
        # public reveal operation.
        del result
        resolved_at = self._clock()
        expires_at = resolved_at + timedelta(seconds=self._resolution_ttl_seconds)
        resolution = SecretResolution(
            ref=ref,
            lease_id=str(uuid.uuid4()),
            resolved_at=resolved_at,
            expires_at=expires_at,
        )
        with self._lease_lock:
            self._leases[resolution.lease_id] = (
                ref,
                organization_id,
                expires_at,
            )
        return resolution

    def _dispatch_with_resolution(
        self,
        *,
        resolution: SecretResolution,
        organization_id: OrganizationId,
        invoke: Callable[[str], _CustodyResult],
    ) -> _CustodyResult:
        """Use a one-shot lease inside a provider callback and return no secret.

        This is the custody-internal dispatch seam promised by
        ``SecretResolution``. The material exists only as the callback argument;
        the lease is consumed before invocation and every callback exception is
        replaced with a sanitized error so traceback chaining cannot retain it.
        """

        self._check_scope(ref=resolution.ref, organization_id=organization_id)
        with self._lease_lock:
            registered = self._leases.pop(resolution.lease_id, None)
        if registered is None:
            raise SecretMaterialError("secret resolution lease is unknown or consumed")
        registered_ref, registered_org, registered_expiry = registered
        if registered_ref != resolution.ref or registered_org != organization_id:
            raise SecretMaterialError("secret resolution lease binding mismatch")
        if (
            resolution.expires_at != registered_expiry
            or self._clock() >= registered_expiry
        ):
            raise SecretMaterialError("secret resolution lease expired")
        result = self._run_security(
            [
                "find-generic-password",
                "-a",
                resolution.ref.handle,
                "-s",
                self._service_prefix,
                "-w",
            ]
        )
        if result.returncode in _ITEM_NOT_FOUND_EXIT_CODES:
            raise SecretNotFoundError(
                f"no secret under handle {resolution.ref.handle!r}"
            )
        if result.returncode != 0:
            raise SecretMaterialError(
                "keychain dispatch resolution failed, "
                f"exit={result.returncode} handle={resolution.ref.handle!r}"
            )
        material = result.stdout
        del result
        provider_failed = False
        provider_result: object | None = None
        try:
            provider_result = invoke(material)
        except Exception:
            provider_failed = True
        del material
        if provider_failed:
            raise SecretMaterialError("provider dispatch failed inside custody")
        from zeo_core.connections.orchestration import (
            EffectDispatchResult,
            ReconciliationResult,
        )

        if not isinstance(
            provider_result, (EffectDispatchResult, ReconciliationResult)
        ):
            del provider_result
            raise SecretMaterialError("provider returned an invalid custody result")
        return cast("_CustodyResult", provider_result)

    def rotate(
        self, *, ref: SecretRef, organization_id: OrganizationId, material: str
    ) -> SecretRef:
        if not material:
            raise ValueError("material must be non-empty")
        self._check_scope(ref=ref, organization_id=organization_id)
        result = self._run_security_with_secret(
            [
                "add-generic-password",
                "-a",
                ref.handle,
                "-s",
                self._service_prefix,
                "-U",
                "-w",
            ],
            material=material,
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


class KeychainEffectDispatcher:
    """Provider dispatcher that confines raw material to one custody callback."""

    def __init__(
        self,
        *,
        store: KeychainSecretStore,
        invoke: Callable[[str, EffectDispatchRequest], EffectDispatchResult],
    ) -> None:
        self._store = store
        self._invoke = invoke

    def dispatch(self, request: EffectDispatchRequest) -> EffectDispatchResult:
        resolution = self._store.resolve(
            ref=request.connection.secret_handle,
            organization_id=request.organization_id,
        )
        result = self._store._dispatch_with_resolution(
            resolution=resolution,
            organization_id=request.organization_id,
            invoke=lambda material: self._invoke(material, request),
        )
        from zeo_core.connections.orchestration import EffectDispatchResult

        if not isinstance(result, EffectDispatchResult):  # defensive type narrowing
            raise SecretMaterialError("provider returned an invalid dispatch result")
        return result


class KeychainEffectReconciler:
    """Run one read-only reconciliation inside the same custody boundary."""

    def __init__(
        self,
        *,
        store: KeychainSecretStore,
        invoke: Callable[[str, EffectDispatchRequest], ReconciliationResult],
    ) -> None:
        self._store = store
        self._invoke = invoke

    def reconcile(self, request: EffectDispatchRequest) -> ReconciliationResult:
        resolution = self._store.resolve(
            ref=request.connection.secret_handle,
            organization_id=request.organization_id,
        )
        result = self._store._dispatch_with_resolution(
            resolution=resolution,
            organization_id=request.organization_id,
            invoke=lambda material: self._invoke(material, request),
        )
        from zeo_core.connections.orchestration import ReconciliationResult

        if not isinstance(result, ReconciliationResult):
            raise SecretMaterialError(
                "provider returned an invalid reconciliation result"
            )
        return result
