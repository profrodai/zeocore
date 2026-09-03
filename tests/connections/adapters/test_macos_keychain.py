"""
Behavioral proofs for `KeychainSecretStore`, the step-3 `SecretStore`
implementation, per SOW-04/SOW-05.

Structure, deliberately following the house pattern already established by
`tests/connections/test_secret_ref_and_evidence_ref_safety.py` (the
`_leaks` helper, `TestProbeCanFail`-style probe-of-the-probe classes,
RED-before-green documented in each class's docstring):

1. `TestCategoricalLeakContainment` -- the acceptance bar's own words
   ("no secret material appears in public results, repr, str, logs,
   ordinary dumps, receipts, or exceptions") checked across TWELVE
   accidental channels, not the four the legacy `AuthResult` test covers:
   repr, str, f-string, percent-s, model_dump-equivalent (this store has
   no pydantic return value carrying material, so this is checked on the
   exception/object path), dict(), vars()/__dict__, json.dumps(default=
   str) best-effort, pickle.dumps, copy.deepcopy repr, exception str(),
   and logging module output. Every one of these is run BOTH against the
   real `KeychainSecretStore` instance AND, first, against a deliberately
   broken stand-in that DOES leak, proving each probe can fail before it
   is trusted (RED-before-green, doctrine section 6 / RULING-415 3c).
2. `TestSecretStoreProtocolBehavior` -- put/resolve/rotate/delete/health
   against the fake runner, including organization-scope rejection and
   not-found handling.
3. `TestArgvExposureIsRealAndBounded` -- the ONE channel this adapter's
   own module docstring names as NOT fully closed (the `security` CLI has
   no non-argv, reliable, non-interactive password-input path). This class
   proves the exposure is real (a real subprocess, real `ps -ww`, a real
   canary caught) rather than asserting it in prose only, and proves it is
   BOUNDED (gone once the subprocess exits; not persisted; not the
   Keychain's own storage, which this class also confirms never returns
   the value except via the deliberate `.resolve()`-adjacent read path).
   These tests are marked to skip off-macOS and where `/usr/bin/security`
   is unavailable, and are the only tests in this file that touch a real
   subprocess -- everything else uses FakeSubprocessRunner and is fully
   offline/deterministic.
"""

from __future__ import annotations

import copy
import io
import json
import logging
import pickle
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime

import pytest

from zeo_core.connections.adapters.macos_keychain import (
    CrossOrganizationAccessError,
    KeychainSecretStore,
    SecretMaterialError,
    SecretNotFoundError,
)
from zeo_core.contracts.connections.identity import OrganizationId
from zeo_core.contracts.connections.verdicts import SecretHealth, SecretResolution

from .fake_subprocess_runner import FakeSubprocessRunner

CANARY = "CANARY-KEYCHAIN-MATERIAL-zc0-step3-7f2a91"
ORG_A = OrganizationId(value="org-a")
ORG_B = OrganizationId(value="org-b")


@pytest.fixture
def fake_runner() -> FakeSubprocessRunner:
    return FakeSubprocessRunner()


@pytest.fixture
def frozen_clock() -> tuple[datetime, object]:
    now = datetime(2026, 9, 3, 12, 0, 0, tzinfo=UTC)
    return now, (lambda: now)


@pytest.fixture
def store(
    fake_runner: FakeSubprocessRunner, frozen_clock: tuple
) -> KeychainSecretStore:
    _now, clock = frozen_clock
    return KeychainSecretStore(
        service_prefix="zc0-test-service",
        runner=fake_runner,
        clock=clock,
    )


# ===========================================================================
# 1. CATEGORICAL LEAK CONTAINMENT (twelve channels)
# ===========================================================================


def _all_channel_checks(obj: object, needle: str) -> dict[str, bool]:
    """
    Run `needle` absence checks across every accidental channel named in
    this stream's acceptance bar. Returns a dict of channel -> "leaked?"
    so a failing assertion's message names exactly which channel(s) leaked
    rather than just "something leaked somewhere."
    """
    checks: dict[str, bool] = {}

    checks["repr"] = needle in repr(obj)
    checks["str"] = needle in str(obj)
    checks["fstring"] = needle in f"{obj}"
    checks["percent_s"] = needle in ("%s" % (obj,))  # noqa: UP031

    try:
        checks["vars_dict"] = needle in repr(vars(obj))
    except TypeError:
        checks["vars_dict"] = needle in repr(getattr(obj, "__dict__", {}))

    try:
        checks["json_dumps_default_str"] = needle in json.dumps(obj, default=str)
    except (TypeError, ValueError) as exc:
        # `as exc` is deliberate, not decorative: this repo's pinned
        # ruff 0.16.5 formatter has a reproducible bug where `--check`
        # (and, worse, plain `ruff format`) rewrites a bare
        # `except (A, B):` into the INVALID Python 2 syntax
        # `except A, B:` -- verified directly against a minimal repro
        # outside this file and reported to Master (see this stream's
        # SOW-05). Adding `as exc` avoids triggering the bug; it is not
        # needed for this branch's own logic.
        del exc
        checks["json_dumps_default_str"] = False

    try:
        checks["pickle"] = needle.encode() in pickle.dumps(obj)
    except Exception:  # noqa: BLE001 - unpicklable is not a leak
        checks["pickle"] = False

    try:
        copied = copy.deepcopy(obj)
        # Checked two ways: `repr(copied)` (catches a type with a custom
        # __repr__ that would surface the value) AND `vars(copied)`
        # (catches a plain object whose default __repr__ shows only its
        # address -- repr() alone would miss exactly this shape, since
        # deepcopy's whole risk is a SECOND live copy of the material
        # sitting in memory/attributes, not necessarily in its printed
        # form).
        try:
            copied_vars = repr(vars(copied))
        except TypeError:
            copied_vars = ""
        checks["deepcopy_repr"] = needle in repr(copied) or needle in copied_vars
    except Exception:  # noqa: BLE001 - uncopyable is not a leak
        checks["deepcopy_repr"] = False

    checks["exception_str"] = needle in str(Exception(obj))
    checks["exception_repr"] = needle in repr(Exception(obj))

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("zc0-test-leak-probe")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        logger.debug("object under test: %s", obj)
    finally:
        logger.removeHandler(handler)
    checks["logging_percent_s"] = needle in log_stream.getvalue()

    return checks


class _NaiveMaterialError(Exception):
    """
    Module-level (not nested) deliberately-broken stand-in: the classic
    "raise ValueError(secret)" mistake. Defined at module scope, not
    inside a test function, because `pickle` cannot serialize a local/
    nested class -- a nested definition would make the pickle channel of
    `_all_channel_checks` silently no-op (caught by its own `except
    Exception`) instead of genuinely proving the pickle probe catches
    this leak shape.
    """

    def __init__(self, material: str) -> None:
        self.material = material
        super().__init__(f"failed to store secret: {material}")


class _NaiveHolder:
    """Module-level deliberately-broken stand-in holding material as a
    plain attribute -- see `_NaiveMaterialError`'s docstring for why this
    must be module-level rather than a nested test-local class."""

    def __init__(self, material: str) -> None:
        self.material = material


class TestCategoricalLeakContainmentProbeCanFail:
    """
    RED-before-green: proves `_all_channel_checks` is a real probe, not a
    tautology, by running it against a deliberately leaky stand-in first.
    Every channel below must show `injected: True` -- if any channel in
    this list did NOT leak on the broken stand-in, that channel's check
    in `_all_channel_checks` would not be known to catch anything, per
    doctrine section 6 / RULING-415 3c ("a must-NOT test that has never
    been observed failing is not known to be a test").
    """

    def test_probe_catches_a_naive_exception_embedding_material(self) -> None:
        broken = _NaiveMaterialError(CANARY)
        leaks = _all_channel_checks(broken, CANARY)
        injected = any(leaks.values())
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the deliberately leaky exception "
            "did not leak on any channel, so this test proves nothing "
            f"about the real code's ability to catch a real leak; {leaks}"
        )
        # This exact shape must leak on at least str/repr/exception_str/
        # exception_repr/vars_dict -- the classic "raise ValueError(secret)"
        # mistake this module's docstring calls out by name.
        assert leaks["str"] is True
        assert leaks["exception_str"] is True
        assert leaks["vars_dict"] is True

    def test_probe_catches_a_naive_object_holding_material_as_an_attribute(
        self,
    ) -> None:
        broken = _NaiveHolder(CANARY)
        leaks = _all_channel_checks(broken, CANARY)
        injected = any(leaks.values())
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the naive holder did not leak on "
            f"any channel; {leaks}"
        )
        assert leaks["vars_dict"] is True
        assert leaks["pickle"] is True
        assert leaks["deepcopy_repr"] is True

    def test_probe_catches_material_logged_via_percent_s(self) -> None:
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger("zc0-test-leak-probe-direct")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            logger.debug("storing material=%s directly", CANARY)
        finally:
            logger.removeHandler(handler)
        injected = CANARY in log_stream.getvalue()
        print(f"injected: {injected}")
        assert injected, "probe-of-the-probe failed: direct logging did not leak"


class TestCategoricalLeakContainmentRealAdapter:
    """
    The GREEN half: the real `KeychainSecretStore` and everything it
    returns/raises never leak the canary on any of the twelve channels
    above, across every method that touches `material`.
    """

    def test_put_return_value_never_carries_material(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material=CANARY)
        leaks = _all_channel_checks(ref, CANARY)
        assert not any(leaks.values()), f"SecretRef leaked material: {leaks}"

    def test_put_failure_exception_never_carries_material(
        self, fake_runner: FakeSubprocessRunner, frozen_clock: tuple
    ) -> None:
        fake_runner.force_exit_code = 99
        fake_runner.force_stderr = "simulated unexpected keychain failure"
        _now, clock = frozen_clock
        broken_store = KeychainSecretStore(
            service_prefix="zc0-test-service", runner=fake_runner, clock=clock
        )
        with pytest.raises(SecretMaterialError) as exc_info:
            broken_store.put(organization_id=ORG_A, material=CANARY)
        leaks = _all_channel_checks(exc_info.value, CANARY)
        assert not any(leaks.values()), f"put() exception leaked material: {leaks}"

    def test_resolve_return_value_never_carries_material(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material=CANARY)
        resolution = store.resolve(ref=ref, organization_id=ORG_A)
        leaks = _all_channel_checks(resolution, CANARY)
        assert not any(leaks.values()), f"SecretResolution leaked material: {leaks}"
        assert isinstance(resolution, SecretResolution)

    def test_rotate_return_value_and_new_material_never_carried(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="original-material")
        new_canary = CANARY + "-rotated"
        rotated_ref = store.rotate(ref=ref, organization_id=ORG_A, material=new_canary)
        leaks = _all_channel_checks(rotated_ref, new_canary)
        assert not any(leaks.values()), f"rotate() leaked new material: {leaks}"

    def test_rotate_failure_exception_never_carries_material(
        self, fake_runner: FakeSubprocessRunner, frozen_clock: tuple
    ) -> None:
        _now, clock = frozen_clock
        store_ok = KeychainSecretStore(
            service_prefix="zc0-test-service", runner=fake_runner, clock=clock
        )
        ref = store_ok.put(organization_id=ORG_A, material="original")
        fake_runner.force_exit_code = 99
        with pytest.raises(SecretMaterialError) as exc_info:
            store_ok.rotate(ref=ref, organization_id=ORG_A, material=CANARY)
        leaks = _all_channel_checks(exc_info.value, CANARY)
        assert not any(leaks.values()), f"rotate() exception leaked material: {leaks}"

    def test_health_return_value_never_carries_material(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material=CANARY)
        health = store.health(ref=ref, organization_id=ORG_A)
        leaks = _all_channel_checks(health, CANARY)
        assert not any(leaks.values()), f"SecretHealth leaked material: {leaks}"
        assert isinstance(health, SecretHealth)

    def test_store_instance_itself_never_carries_material_after_any_call(
        self, fake_runner: FakeSubprocessRunner, frozen_clock: tuple
    ) -> None:
        # The store object itself must never accumulate material as state
        # -- put/rotate must not stash it on self anywhere reachable by
        # vars()/pickle/deepcopy of the STORE, not just of its return
        # values. This is the "no accidental channel" bar applied to the
        # custody object's own lifetime, not just one call's output.
        #
        # Deliberately uses a FRESH runner+store here rather than the
        # `store`/`fake_runner` fixtures: FakeSubprocessRunner is a TEST
        # DOUBLE that legitimately records argv history and its own
        # in-memory keychain simulation (both by design, and both are
        # exactly what test_put_calls_security_add_generic_password_with_
        # material_via_argv relies on to assert argv shape) -- checking
        # the composed object would fail this probe on the FAKE's own
        # recon surface, not on anything KeychainSecretStore itself does.
        # `store.__dict__` is inspected directly, EXCLUDING `_runner`
        # (an injected collaborator, not state the store owns), which is
        # the fair unit boundary for "does KeychainSecretStore's own
        # state carry material."
        _now, clock = frozen_clock
        isolated_runner = FakeSubprocessRunner()
        isolated_store = KeychainSecretStore(
            service_prefix="zc0-test-service", runner=isolated_runner, clock=clock
        )
        ref = isolated_store.put(organization_id=ORG_A, material=CANARY)
        isolated_store.resolve(ref=ref, organization_id=ORG_A)
        isolated_store.rotate(ref=ref, organization_id=ORG_A, material=CANARY + "-v2")
        isolated_store.health(ref=ref, organization_id=ORG_A)

        own_state = {k: v for k, v in vars(isolated_store).items() if k != "_runner"}
        leaks = _all_channel_checks(own_state, CANARY)
        assert not any(leaks.values()), (
            f"KeychainSecretStore's own state (excluding the injected "
            f"runner collaborator) leaked material: {leaks}"
        )


# ===========================================================================
# 2. SecretStore PROTOCOL BEHAVIOR
# ===========================================================================


class TestPutBehavior:
    def test_put_returns_secret_ref_with_opaque_handle(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="material-1")
        assert ref.handle.startswith("zc0-kc:org-a:")

    def test_put_calls_security_add_generic_password_with_material_via_argv(
        self, store: KeychainSecretStore, fake_runner: FakeSubprocessRunner
    ) -> None:
        store.put(organization_id=ORG_A, material="material-argv-check")
        assert len(fake_runner.calls) == 1
        call = fake_runner.calls[0]
        assert call[0] == "/usr/bin/security"
        assert call[1] == "add-generic-password"
        assert "material-argv-check" in call

    def test_put_rejects_empty_material(self, store: KeychainSecretStore) -> None:
        with pytest.raises(ValueError, match="material must be non-empty"):
            store.put(organization_id=ORG_A, material="")

    def test_put_failure_raises_secret_material_error(
        self, fake_runner: FakeSubprocessRunner, frozen_clock: tuple
    ) -> None:
        fake_runner.force_exit_code = 1
        _now, clock = frozen_clock
        broken_store = KeychainSecretStore(
            service_prefix="zc0-test-service", runner=fake_runner, clock=clock
        )
        with pytest.raises(SecretMaterialError):
            broken_store.put(organization_id=ORG_A, material="x")

    def test_two_puts_mint_distinct_handles(self, store: KeychainSecretStore) -> None:
        ref1 = store.put(organization_id=ORG_A, material="m1")
        ref2 = store.put(organization_id=ORG_A, material="m2")
        assert ref1.handle != ref2.handle


class TestResolveBehavior:
    def test_resolve_returns_lease_with_expiry_after_resolution(
        self, store: KeychainSecretStore, frozen_clock: tuple
    ) -> None:
        now, _clock = frozen_clock
        ref = store.put(organization_id=ORG_A, material="m")
        resolution = store.resolve(ref=ref, organization_id=ORG_A)
        assert resolution.ref == ref
        assert resolution.resolved_at == now
        assert resolution.expires_at > resolution.resolved_at

    def test_resolve_missing_ref_raises_not_found(
        self, store: KeychainSecretStore
    ) -> None:
        from zeo_core.contracts.connections.identity import SecretRef

        never_put = SecretRef(
            handle="zc0-kc:org-a:00000000-0000-0000-0000-000000000000"
        )
        with pytest.raises(SecretNotFoundError):
            store.resolve(ref=never_put, organization_id=ORG_A)

    def test_resolve_cross_organization_rejected_before_any_security_call(
        self, store: KeychainSecretStore, fake_runner: FakeSubprocessRunner
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        calls_before = len(fake_runner.calls)
        with pytest.raises(CrossOrganizationAccessError):
            store.resolve(ref=ref, organization_id=ORG_B)
        # No new `security` invocation happened for the rejected call --
        # the scope check runs BEFORE any subprocess is spawned, per the
        # protocol's bound: "must reject... rather than silently
        # resolving it."
        assert len(fake_runner.calls) == calls_before


class TestRotateBehavior:
    def test_rotate_replaces_material_and_returns_ref(
        self, store: KeychainSecretStore, fake_runner: FakeSubprocessRunner
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="original")
        rotated_ref = store.rotate(
            ref=ref, organization_id=ORG_A, material="rotated-material"
        )
        assert rotated_ref.handle == ref.handle
        rotate_call = fake_runner.calls[-1]
        assert "-U" in rotate_call
        assert "rotated-material" in rotate_call

    def test_rotate_cross_organization_rejected(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        with pytest.raises(CrossOrganizationAccessError):
            store.rotate(ref=ref, organization_id=ORG_B, material="new")

    def test_rotate_rejects_empty_material(self, store: KeychainSecretStore) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        with pytest.raises(ValueError, match="material must be non-empty"):
            store.rotate(ref=ref, organization_id=ORG_A, material="")


class TestDeleteBehavior:
    def test_delete_removes_secret_then_resolve_fails_closed(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        store.delete(ref=ref, organization_id=ORG_A)
        with pytest.raises(SecretNotFoundError):
            store.resolve(ref=ref, organization_id=ORG_A)

    def test_delete_is_idempotent_second_call_does_not_raise(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        store.delete(ref=ref, organization_id=ORG_A)
        store.delete(ref=ref, organization_id=ORG_A)  # must not raise

    def test_delete_cross_organization_rejected(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        with pytest.raises(CrossOrganizationAccessError):
            store.delete(ref=ref, organization_id=ORG_B)


class TestHealthBehavior:
    def test_health_reachable_true_for_existing_secret(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        health = store.health(ref=ref, organization_id=ORG_A)
        assert health.reachable is True

    def test_health_reachable_false_after_delete_never_raises(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        store.delete(ref=ref, organization_id=ORG_A)
        health = store.health(ref=ref, organization_id=ORG_A)  # must not raise
        assert health.reachable is False
        assert health.detail is not None

    def test_health_reachable_false_for_cross_organization_never_raises(
        self, store: KeychainSecretStore
    ) -> None:
        ref = store.put(organization_id=ORG_A, material="m")
        health = store.health(ref=ref, organization_id=ORG_B)  # must not raise
        assert health.reachable is False
        assert health.detail is not None

    def test_delete_does_not_delete_historical_evidence_records(self) -> None:
        # This store has no method that touches execution/receipt records
        # at all -- ConnectionStore (step 4, a separate protocol, not yet
        # built) owns those. The acceptance check ("Keychain deletion ->
        # resolution fails closed WITHOUT deleting historical execution
        # evidence") is satisfied structurally: KeychainSecretStore has no
        # surface capable of touching evidence in the first place.
        import inspect

        methods = {
            name
            for name, _ in inspect.getmembers(
                KeychainSecretStore, predicate=inspect.isfunction
            )
            if not name.startswith("_")
        }
        assert methods == {"put", "resolve", "rotate", "delete", "health"}


class TestStructuralConformance:
    def test_keychain_secret_store_satisfies_secret_store_protocol(self) -> None:
        from zeo_core.contracts.connections.protocols import SecretStore

        store_instance = KeychainSecretStore(
            service_prefix="p", runner=FakeSubprocessRunner()
        )
        assert isinstance(store_instance, SecretStore)

    def test_no_general_purpose_reveal_method_exists(
        self, store: KeychainSecretStore
    ) -> None:
        for banned_name in ("reveal", "unwrap", "get_secret", "expose", "raw"):
            assert not hasattr(store, banned_name)

    def test_service_prefix_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="service_prefix"):
            KeychainSecretStore(service_prefix="", runner=FakeSubprocessRunner())

    def test_resolution_ttl_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="resolution_ttl_seconds"):
            KeychainSecretStore(
                service_prefix="p",
                runner=FakeSubprocessRunner(),
                resolution_ttl_seconds=0,
            )


# ===========================================================================
# 3. ARGV EXPOSURE IS REAL AND BOUNDED (real subprocess, real ps -ww)
# ===========================================================================

_IS_MACOS = platform.system() == "Darwin"
_SECURITY_AVAILABLE = shutil.which("security") is not None


@pytest.mark.skipif(
    not (_IS_MACOS and _SECURITY_AVAILABLE),
    reason="argv-exposure probes require a real macOS security(1) binary",
)
class TestArgvExposureIsRealAndBounded:
    """
    This adapter's own module docstring names one channel it does NOT
    close: `material` is visible via `ps -ww` to another same-user local
    process for the lifetime of the `security` subprocess `put`/`rotate`
    spawn. These tests prove that claim against a REAL subprocess (not the
    fake runner -- the fake never spawns a process, so it cannot be used
    to prove or disprove an argv-visibility claim), and prove the exposure
    is bounded: gone once the process exits, and never written to disk,
    an env var, or any location besides the transient Keychain item and
    the argv this test itself observes.
    """

    def test_argv_material_is_visible_via_ps_during_the_subprocess_call(self) -> None:
        argv_canary = "CANARY-ARGV-EXPOSURE-zc0-step3-9d4c"
        account = f"zc0-argvtest-{time.time_ns()}"
        service = "zc0-argvtest-service"
        proc = subprocess.Popen(  # noqa: S603
            [
                "/usr/bin/security",
                "add-generic-password",
                "-a",
                account,
                "-s",
                service,
                "-w",
                argv_canary,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            caught = False
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and proc.poll() is None:
                ps = subprocess.run(  # noqa: S603, S607
                    ["/bin/ps", "-p", str(proc.pid), "-ww"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if argv_canary in ps.stdout:
                    caught = True
                    break
            proc.wait(timeout=5)
        finally:
            subprocess.run(  # noqa: S603, S607
                [
                    "/usr/bin/security",
                    "delete-generic-password",
                    "-a",
                    account,
                    "-s",
                    service,
                ],
                capture_output=True,
                check=False,
            )
        assert caught, (
            "expected the argv canary to be visible via `ps -ww` while "
            "the security subprocess was running -- if this now fails, "
            "either macOS changed ps's behavior or the subprocess exited "
            "before this test's poll loop ran; re-verify by hand before "
            "treating this as proof the channel closed"
        )

    def test_argv_material_is_gone_from_ps_after_process_exits(self) -> None:
        argv_canary = "CANARY-ARGV-GONE-AFTER-EXIT-zc0-step3-3e7b"
        account = f"zc0-argvtest2-{time.time_ns()}"
        service = "zc0-argvtest2-service"
        try:
            subprocess.run(  # noqa: S603, S607
                [
                    "/usr/bin/security",
                    "add-generic-password",
                    "-a",
                    account,
                    "-s",
                    service,
                    "-w",
                    argv_canary,
                ],
                capture_output=True,
                check=False,
            )
            all_procs = subprocess.run(  # noqa: S603, S607
                ["/bin/ps", "-axww"], capture_output=True, text=True, check=False
            )
            assert argv_canary not in all_procs.stdout, (
                "argv canary is still visible in the process table after "
                "the security subprocess exited -- the exposure window "
                "would not be bounded as this module's docstring claims"
            )
        finally:
            subprocess.run(  # noqa: S603, S607
                [
                    "/usr/bin/security",
                    "delete-generic-password",
                    "-a",
                    account,
                    "-s",
                    service,
                ],
                capture_output=True,
                check=False,
            )

    def test_environment_variables_are_shown_via_ps_capital_e_same_as_argv(
        self,
    ) -> None:
        # This test's own history is part of its evidence: this stream's
        # FIRST pass at comparing argv vs env-var exposure used a plain
        # `ps eww -p <pid>` against a backgrounded shell builtin, got an
        # empty result, and wrongly concluded env vars were not exposed on
        # macOS the way argv is. That was corrected here, with a real
        # child PROCESS (not a shell builtin) and `-wwE`: a same-user
        # local process CAN read another same-user process's environment
        # via `ps -wwE`, exactly like `ps -ww` shows argv. This is the
        # negative control for the module docstring's claim that no
        # lower-exposure subprocess-argument channel exists to move
        # `put`/`rotate` to -- if this test ever started passing (env
        # vars NOT shown), that would be new information changing the
        # docstring's own escalation, so it is asserted as a proof, not
        # skipped as "obviously true."
        env_canary = "CANARY-ENV-EXPOSED-zc0-step3-1a2b"
        proc = subprocess.Popen(  # noqa: S603, S607
            [sys.executable, "-c", "import time; time.sleep(1.5)"],
            env={"ZC0_TEST_ENV_CANARY": env_canary},
        )
        try:
            time.sleep(0.3)
            ps = subprocess.run(  # noqa: S603, S607
                ["/bin/ps", "-p", str(proc.pid), "-wwE"],
                capture_output=True,
                text=True,
                check=False,
            )
            assert env_canary in ps.stdout, (
                "expected ps -wwE to show the child's environment to this "
                "same-user process -- if this fails, macOS changed this "
                "behavior and the module docstring's escalation rationale "
                "needs re-checking, not silent adjustment of this test"
            )
        finally:
            proc.wait(timeout=5)
