"""Local Revolut enrollment: offline, no network, private temp directory."""

from __future__ import annotations

import json
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import SecretStr

from zeo_core.integrations.revolut import RevolutAPIError, RevolutEnvironment
from zeo_core.integrations.revolut.local import (
    LocalCredentialStore,
    LocalEnrollmentError,
    LocalRevolutEnrollment,
    LocalStoreError,
    TokenFailure,
    TokenGrant,
)
from zeo_core.integrations.revolut.local.__main__ import main
from zeo_core.integrations.revolut.local.store import (
    KEY_FILENAME,
    STATE_FILENAME,
    dump_public,
)

NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)
REDIRECT = "https://example.test/revolut/callback"
CANARY = "local-canary-81c2"


class FakeGateway:
    def __init__(self, store: LocalCredentialStore) -> None:
        self._store = store
        self.exchanges: list[str] = []
        self.refreshes = 0
        self.outcome: TokenFailure | BaseException | None = None
        self.marker_seen_before_send: list[bool] = []

    def exchange(self, *, code: SecretStr, **_: object) -> TokenGrant | TokenFailure:
        self.exchanges.append(code.get_secret_value())
        if isinstance(self.outcome, TokenFailure):
            return self.outcome
        return TokenGrant(
            access_token=SecretStr(f"{CANARY}-access-1"),
            refresh_token=SecretStr(f"{CANARY}-refresh"),
            expires_in=2400,
        )

    def refresh(self, **_: object) -> TokenGrant | TokenFailure:
        state = self._store.load()
        assert state is not None
        self.marker_seen_before_send.append(state.refresh_attempt is not None)
        self.refreshes += 1
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        if self.outcome is not None:
            return self.outcome
        return TokenGrant(
            access_token=SecretStr(f"{CANARY}-access-{self.refreshes + 1}"),
            expires_in=2400,
        )


class FakeClient:
    def __init__(self, token: SecretStr, rejected: set[str]) -> None:
        self.token = token.get_secret_value()
        self._rejected = rejected
        self.closed = False

    def list_accounts(self) -> str:
        if self.token in self._rejected:
            raise RevolutAPIError("AUTHENTICATION", "rejected", status_code=401)
        return self.token

    def close(self) -> None:
        self.closed = True


class Harness:
    def __init__(self, directory: Path) -> None:
        self.now = NOW
        self.store = LocalCredentialStore(directory / "private")
        self.gateway = FakeGateway(self.store)
        self.rejected: set[str] = set()
        self.clients: list[FakeClient] = []

        def client(token: SecretStr, environment: RevolutEnvironment) -> FakeClient:
            assert environment is RevolutEnvironment.SANDBOX
            self.clients.append(FakeClient(token, self.rejected))
            return self.clients[-1]

        self.enrollment = LocalRevolutEnrollment(
            RevolutEnvironment.SANDBOX,
            store=self.store,
            gateway=self.gateway,
            clock=lambda: self.now,
            client_factory=client,  # type: ignore[arg-type]
        )

    def enroll(self) -> None:
        self.enrollment.setup(redirect_uri=REDIRECT)
        url = self.enrollment.authorize(client_id="client-id")
        state = parse_qs(urlsplit(url).query)["state"][0]
        self.enrollment.complete(f"{REDIRECT}?code=auth-code&state={state}")

    def read(self) -> str:
        return self.enrollment.read(lambda client: client.list_accounts())  # type: ignore[return-value]

    def raw(self) -> dict[str, object]:
        loaded: dict[str, object] = json.loads(
            (self.store.directory / STATE_FILENAME).read_text()
        )
        return loaded


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


def test_setup_writes_owner_only_files_outside_any_repository(
    harness: Harness, tmp_path: Path
) -> None:
    certificate = harness.enrollment.setup(redirect_uri=REDIRECT)
    assert "BEGIN CERTIFICATE" in Path(certificate).read_text()
    for name in (KEY_FILENAME, STATE_FILENAME):
        mode = stat.S_IMODE((harness.store.directory / name).stat().st_mode)
        assert mode == 0o600
    assert stat.S_IMODE(harness.store.directory.stat().st_mode) == 0o700
    assert b"PRIVATE KEY" in (harness.store.directory / KEY_FILENAME).read_bytes()

    with pytest.raises(LocalEnrollmentError) as again:
        harness.enrollment.setup(redirect_uri=REDIRECT)
    assert again.value.code == "KEY_EXISTS"
    for invalid in ("http://example.test/cb", "https:///cb", "not a url"):
        with pytest.raises(LocalEnrollmentError) as bad:
            harness.enrollment.setup(redirect_uri=invalid, new_key=True)
        assert bad.value.code == "REDIRECT_URI"

    repository = tmp_path / "repo"
    (repository / ".git").mkdir(parents=True)
    inside = LocalRevolutEnrollment(
        RevolutEnvironment.SANDBOX,
        store=LocalCredentialStore(repository / "secrets"),
        gateway=harness.gateway,
    )
    with pytest.raises(LocalStoreError, match="inside a repository"):
        inside.setup(redirect_uri=REDIRECT)


def test_consent_url_is_fixed_host_read_only_and_state_bound(harness: Harness) -> None:
    with pytest.raises(LocalEnrollmentError) as early:
        harness.enrollment.authorize(client_id="client-id")
    assert early.value.code == "NOT_SET_UP"
    harness.enrollment.setup(redirect_uri=REDIRECT)
    with pytest.raises(LocalEnrollmentError):
        harness.enrollment.authorize(client_id="  ")
    url = urlsplit(harness.enrollment.authorize(client_id="client-id"))
    assert (url.scheme, url.netloc, url.path) == (
        "https",
        "sandbox-business.revolut.com",
        "/app-confirm",
    )
    query = parse_qs(url.query)
    assert set(query) == {
        "client_id",
        "redirect_uri",
        "response_type",
        "scope",
        "state",
    }
    assert query["scope"] == ["READ"] and query["response_type"] == ["code"]
    state = query["state"][0]

    for wrong in (
        f"https://evil.test/revolut/callback?code=c&state={state}",
        f"{REDIRECT}/other?code=c&state={state}",
        f"{REDIRECT}?code=c&state=forged",
        f"{REDIRECT}?state={state}",
        f"{REDIRECT}?code=a&code=b&state={state}",
    ):
        with pytest.raises(LocalEnrollmentError) as refused:
            harness.enrollment.complete(wrong)
        assert refused.value.code == "CONSENT_MISMATCH"
    assert harness.gateway.exchanges == []


def test_complete_stores_tokens_privately_and_status_reveals_none(
    harness: Harness,
) -> None:
    harness.enrollment.setup(redirect_uri=REDIRECT)
    with pytest.raises(LocalEnrollmentError) as early:
        harness.enrollment.complete(f"{REDIRECT}?code=c&state=s")
    assert early.value.code == "NOT_AUTHORIZED"
    harness.gateway.outcome = TokenFailure(kind="refused")
    url = harness.enrollment.authorize(client_id="client-id")
    state = parse_qs(urlsplit(url).query)["state"][0]
    with pytest.raises(LocalEnrollmentError) as refused:
        harness.enrollment.complete(f"{REDIRECT}?code=c&state={state}")
    assert refused.value.code == "EXCHANGE_REFUSED"

    harness.gateway.outcome = None
    harness.enrollment.complete(f"{REDIRECT}?code=auth-code&state={state}")
    assert harness.gateway.exchanges[-1] == "auth-code"
    status = harness.enrollment.status()
    assert status is not None and status.consent_state is None
    assert CANARY not in repr(status) and CANARY not in dump_public(status)
    assert json.loads(dump_public(status))["enrolled"] is True
    assert harness.raw()["access_token"] == f"{CANARY}-access-1"  # private file only
    assert harness.read() == f"{CANARY}-access-1"
    assert harness.gateway.refreshes == 0 and harness.clients[-1].closed


def test_refresh_marker_is_durable_before_the_request_and_cleared_after(
    harness: Harness,
) -> None:
    harness.enroll()
    harness.now = NOW + timedelta(minutes=36)
    assert harness.read() == f"{CANARY}-access-2"
    assert harness.gateway.marker_seen_before_send == [True]
    assert harness.raw()["refresh_attempt"] is None
    # Revolut kept the refresh token; the next refresh still has one.
    harness.now += timedelta(minutes=36)
    assert harness.read() == f"{CANARY}-access-3"


@pytest.mark.parametrize(
    "lost", [KeyboardInterrupt(), SystemExit(1), TokenFailure(kind="unknown")]
)
def test_lost_refresh_answer_blocks_for_good_and_consent_does_not_clear_it(
    harness: Harness, lost: TokenFailure | BaseException
) -> None:
    harness.enroll()
    harness.now = NOW + timedelta(minutes=36)
    harness.gateway.outcome = lost
    with pytest.raises((LocalEnrollmentError, KeyboardInterrupt, SystemExit)):
        harness.read()
    assert harness.raw()["refresh_attempt"] is not None  # the marker survived

    # The stored token may still be accepted; reading it changes nothing.
    harness.gateway.outcome = None
    harness.now = NOW + timedelta(minutes=10)
    assert harness.read() == f"{CANARY}-access-1"

    # Once a refresh is needed: blocked. Time and repetition clear nothing.
    for days in (0, 30):
        harness.now = NOW + timedelta(days=days, minutes=36)
        for _ in range(2):
            with pytest.raises(LocalEnrollmentError) as blocked:
                harness.read()
            assert blocked.value.code == "OUTCOME_UNKNOWN"
    assert harness.gateway.refreshes == 1
    assert json.loads(dump_public(harness.enrollment.status()))[  # type: ignore[arg-type]
        "refresh_outcome_unknown"
    ]

    # A fresh consent on the SAME registration authorizes new tokens. It does
    # not settle what Revolut did with the lost request, so nothing is cleared.
    url = harness.enrollment.authorize(client_id="client-id")
    state = parse_qs(urlsplit(url).query)["state"][0]
    harness.enrollment.complete(f"{REDIRECT}?code=again&state={state}")
    assert harness.raw()["refresh_attempt"] is not None
    assert harness.raw()["blocked_reason"] == "OUTCOME_UNKNOWN"
    # The new access token serves reads while it is valid and accepted ...
    assert harness.read() == f"{CANARY}-access-1"
    # ... and refreshing stays blocked once it is needed, for good.
    harness.now += timedelta(days=90)
    with pytest.raises(LocalEnrollmentError) as still:
        harness.read()
    assert still.value.code == "OUTCOME_UNKNOWN"
    assert harness.gateway.refreshes == 1


def test_a_refused_grant_is_answered_by_a_new_one_but_an_unknown_is_not(
    harness: Harness,
) -> None:
    harness.enroll()
    harness.now = NOW + timedelta(minutes=36)
    harness.gateway.outcome = TokenFailure(kind="refused")
    with pytest.raises(LocalEnrollmentError):
        harness.read()
    assert harness.raw()["blocked_reason"] == "GRANT_REFUSED"
    assert harness.raw()["refresh_attempt"] is None  # a definite answer
    harness.gateway.outcome = None
    url = harness.enrollment.authorize(client_id="client-id")
    state = parse_qs(urlsplit(url).query)["state"][0]
    harness.enrollment.complete(f"{REDIRECT}?code=again&state={state}")
    assert harness.raw()["blocked_reason"] is None
    harness.now += timedelta(minutes=36)
    assert harness.read().startswith(CANARY)


def test_a_new_registration_records_that_it_followed_an_unresolved_outcome(
    harness: Harness,
) -> None:
    harness.enroll()
    harness.now = NOW + timedelta(minutes=36)
    harness.gateway.outcome = TokenFailure(kind="unknown")
    with pytest.raises(LocalEnrollmentError):
        harness.read()
    harness.gateway.outcome = None

    harness.enrollment.setup(redirect_uri=REDIRECT, new_key=True)
    raw = harness.raw()
    # No credential of the old registration survives ...
    assert raw["access_token"] is None and raw["refresh_attempt"] is None
    # ... but the fact is not laundered away, across any number of new keys.
    assert raw["follows_unresolved_refresh"] is True
    harness.enrollment.setup(redirect_uri=REDIRECT, new_key=True)
    assert harness.raw()["follows_unresolved_refresh"] is True
    status = harness.enrollment.status()
    assert status is not None
    assert json.loads(dump_public(status))["follows_unresolved_refresh"] is True

    clean = Harness(harness.store.directory.parent / "clean")
    clean.enroll()
    clean.enrollment.setup(redirect_uri=REDIRECT, new_key=True)
    assert clean.raw()["follows_unresolved_refresh"] is False


@pytest.mark.parametrize(
    ("stored", "selected"),
    [
        (RevolutEnvironment.SANDBOX, RevolutEnvironment.PRODUCTION),
        (RevolutEnvironment.PRODUCTION, RevolutEnvironment.SANDBOX),
    ],
)
def test_stored_enrollment_is_never_reinterpreted_for_another_environment(
    tmp_path: Path, stored: RevolutEnvironment, selected: RevolutEnvironment
) -> None:
    store = LocalCredentialStore(tmp_path / "private")
    gateway = FakeGateway(store)
    built: list[RevolutEnvironment] = []

    def factory(token: SecretStr, environment: RevolutEnvironment) -> FakeClient:
        built.append(environment)
        return FakeClient(token, set())

    def enrollment(environment: RevolutEnvironment) -> LocalRevolutEnrollment:
        return LocalRevolutEnrollment(
            environment,
            store=store,
            gateway=gateway,
            clock=lambda: NOW + timedelta(minutes=36),  # a refresh would be due
            client_factory=factory,  # type: ignore[arg-type]
        )

    owner = enrollment(stored)
    owner.setup(redirect_uri=REDIRECT)
    url = owner.authorize(client_id="client-id")
    state = parse_qs(urlsplit(url).query)["state"][0]
    other = enrollment(selected)

    # Completion, before any token exists.
    with pytest.raises(LocalEnrollmentError) as refused:
        other.complete(f"{REDIRECT}?code=c&state={state}")
    assert refused.value.code == "ENVIRONMENT_MISMATCH" and gateway.exchanges == []

    owner.complete(f"{REDIRECT}?code=c&state={state}")
    exchanges = list(gateway.exchanges)
    for attempt in (
        lambda: other.read(lambda client: client.list_accounts()),  # and refresh
        lambda: other.authorize(client_id="client-id"),
        lambda: other.status(),
        lambda: other.setup(redirect_uri=REDIRECT),
    ):
        with pytest.raises(LocalEnrollmentError) as mismatch:
            attempt()
        assert mismatch.value.code == "ENVIRONMENT_MISMATCH"
    # Nothing was built, exchanged or refreshed for the wrong environment.
    assert built == [] and gateway.refreshes == 0 and gateway.exchanges == exchanges
    assert store.load() is not None and store.load().environment is stored  # type: ignore[union-attr]

    # Changing environment is an explicit new setup, never a reinterpretation.
    other.setup(redirect_uri=REDIRECT, new_key=True)
    fresh = store.load()
    assert fresh is not None and fresh.environment is selected
    assert fresh.access_token is None and fresh.client_id is None


# ---------------------------------------------------------------------------
# Counterexamples from the independent post-merge review of PR 73 (L1, L2).
# Transplanted with type annotations; scheduling and final assertions are the
# reviewer's. Both FAILED at the reviewed head 223314c1.
# ---------------------------------------------------------------------------


def test_same_registration_consent_must_not_clear_unresolved_refresh(
    tmp_path: Path,
) -> None:
    h = Harness(tmp_path)
    h.enroll()
    h.now = NOW + timedelta(minutes=36)
    h.gateway.outcome = TokenFailure(kind="unknown")
    with pytest.raises(LocalEnrollmentError):
        h.read()
    before = h.store.load()
    assert before is not None and before.refresh_attempt is not None
    assert before.client_id is not None
    h.gateway.outcome = None
    url = h.enrollment.authorize(client_id=before.client_id)
    state = parse_qs(urlsplit(url).query)["state"][0]
    h.enrollment.complete(f"{REDIRECT}?code=fresh&state={state}")
    after = h.store.load()
    assert after is not None and after.refresh_attempt is not None, (
        "same registration erased unresolved provider outcome"
    )


def test_sandbox_store_must_not_supply_credentials_to_production(
    tmp_path: Path,
) -> None:
    h = Harness(tmp_path)
    h.enroll()
    seen: list[RevolutEnvironment] = []

    def factory(token: SecretStr, environment: RevolutEnvironment) -> FakeClient:
        seen.append(environment)
        return FakeClient(token, set())

    production = LocalRevolutEnrollment(
        RevolutEnvironment.PRODUCTION,
        store=h.store,
        gateway=h.gateway,
        clock=lambda: NOW,
        client_factory=factory,  # type: ignore[arg-type]
    )
    try:
        production.read(lambda client: client.list_accounts())
    except LocalEnrollmentError:
        pass
    assert not seen, "sandbox credential reached a production-selected client"


def test_unreachable_provider_changes_nothing_but_a_refusal_blocks(
    harness: Harness,
) -> None:
    harness.enroll()
    harness.now = NOW + timedelta(minutes=36)
    harness.gateway.outcome = TokenFailure(kind="unavailable")
    with pytest.raises(LocalEnrollmentError) as offline:
        harness.read()
    assert offline.value.code == "UNAVAILABLE"
    assert harness.raw()["refresh_attempt"] is None  # nothing reached Revolut
    harness.gateway.outcome = None
    assert harness.read() == f"{CANARY}-access-3"

    harness.now += timedelta(minutes=36)
    harness.gateway.outcome = TokenFailure(kind="refused")
    with pytest.raises(LocalEnrollmentError) as refused:
        harness.read()
    assert refused.value.code == "GRANT_REFUSED"
    harness.gateway.outcome = None
    with pytest.raises(LocalEnrollmentError) as still:
        harness.read()
    assert still.value.code == "GRANT_REFUSED" and harness.gateway.refreshes == 3


def test_one_refresh_and_one_repeat_per_read_never_more(harness: Harness) -> None:
    harness.enroll()
    harness.rejected = {f"{CANARY}-access-1"}
    assert harness.read() == f"{CANARY}-access-2"
    assert harness.gateway.refreshes == 1

    harness.rejected = {f"{CANARY}-access-{n}" for n in range(1, 9)}
    with pytest.raises(LocalEnrollmentError) as rejected:
        harness.read()
    assert rejected.value.code == "TOKEN_REJECTED" and harness.gateway.refreshes == 2
    assert "revoked" not in str(rejected.value).lower()


def test_proactive_refresh_spends_the_same_single_allowance(harness: Harness) -> None:
    harness.enroll()
    harness.rejected = {f"{CANARY}-access-{n}" for n in range(1, 9)}
    harness.now = NOW + timedelta(minutes=36)
    with pytest.raises(LocalEnrollmentError) as rejected:
        harness.read()
    assert rejected.value.code == "TOKEN_REJECTED" and harness.gateway.refreshes == 1


def test_other_provider_errors_pass_through_without_a_refresh(harness: Harness) -> None:
    harness.enroll()

    def limited(client: object) -> str:
        raise RevolutAPIError("RATE_LIMIT", "slow down", status_code=429)

    with pytest.raises(RevolutAPIError) as passed:
        harness.enrollment.read(limited)
    assert passed.value.code == "RATE_LIMIT" and harness.gateway.refreshes == 0

    fresh = Harness(harness.store.directory.parent / "fresh")
    with pytest.raises(LocalEnrollmentError) as missing:
        fresh.read()
    assert missing.value.code == "NOT_ENROLLED"


def test_private_files_that_others_can_read_or_redirect_are_refused(
    harness: Harness,
) -> None:
    harness.enroll()
    state_file = harness.store.directory / STATE_FILENAME
    os.chmod(state_file, 0o644)
    with pytest.raises(LocalStoreError, match="only by its owner"):
        harness.read()
    os.chmod(state_file, 0o600)
    target = harness.store.directory / "elsewhere.json"
    state_file.rename(target)
    state_file.symlink_to(target)
    with pytest.raises(LocalStoreError):
        harness.read()


def test_new_key_discards_the_old_registration_entirely(harness: Harness) -> None:
    harness.enroll()
    old_key = (harness.store.directory / KEY_FILENAME).read_bytes()
    harness.enrollment.setup(redirect_uri=REDIRECT, new_key=True)
    assert (harness.store.directory / KEY_FILENAME).read_bytes() != old_key
    raw = harness.raw()
    assert raw["access_token"] is None and raw["client_id"] is None


def test_cli_walks_the_steps_without_printing_a_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "zeo_core.integrations.revolut.local.session.default_directory",
        lambda environment: tmp_path / "cli" / environment.value,
    )
    assert main(["status"]) == 0
    assert "Not set up." in capsys.readouterr().out
    assert main(["authorize", "--client-id", "client-id"]) == 1
    assert "NOT_SET_UP" in capsys.readouterr().err
    assert main(["setup", "--redirect-uri", REDIRECT]) == 0
    assert "client-certificate.pem" in capsys.readouterr().out
    assert main(["--environment", "sandbox", "authorize", "--client-id", "cid"]) == 0
    assert "sandbox-business.revolut.com" in capsys.readouterr().out
    monkeypatch.setattr("getpass.getpass", lambda prompt: f"{REDIRECT}?code=c&state=x")
    assert main(["complete"]) == 1
    assert "CONSENT_MISMATCH" in capsys.readouterr().err
    assert main(["status"]) == 0
    assert '"enrolled": false' in capsys.readouterr().out
    assert main(["accounts"]) == 1
    assert "NOT_ENROLLED" in capsys.readouterr().err
    for missing in (["setup"], ["authorize"]):
        monkeypatch.delenv("REVOLUT_REDIRECT_URI", raising=False)
        monkeypatch.delenv("REVOLUT_CLIENT_ID", raising=False)
        with pytest.raises(SystemExit):
            main(missing)
