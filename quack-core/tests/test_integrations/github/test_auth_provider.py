# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/github/test_auth_provider.py
# === QV-LLM:END ===

"""
Real behavioral tests for GitHubAuthProvider (integrations/github/auth.py).

Per RULING-235: the external boundary mocked here is the HTTP client the
provider talks to GitHub's REST API through. GitHubAuthProvider.__init__
takes an explicit `http_client` injection point (its own docstring: "for
testing") -- a FakeHTTPClient standing in for `requests`/`requests.Session`
is exactly the sanctioned boundary-mock, never a mock of
GitHubAuthProvider/quack_core itself. Every test below drives the REAL
GitHubAuthProvider.authenticate() / refresh_credentials() /
get_credentials() / save_credentials() / _load_credentials() /
_save_token_data() code, with only the network response faked.

Credentials-file I/O goes through the REAL quack_core.core.fs.service.

PER RULING-237: two production bugs discovered while writing this file (SOW-4,
round 3) are now FIXED in this stream's own chain, and the canaries below that
pinned them as failing-red have been flipped to assert real, correct
(non-crashing) behavior instead. History kept here, not deleted, per
append-don't-revert (CLAUDE.md s5):

BUG A (FIXED) -- integrations/core/base.py::BaseAuthProvider._resolve_path()
used to crash with an unhandled ValueError for ANY credentials_file path
outside the FileSystemService singleton's base_dir (== CWD): its own
except-Exception fallback repeated the identical sandboxed call
(standalone.resolve_path and standalone.normalize_path are literal aliases of
the same underlying method, confirmed by reading service/path_operations.py),
so the "fallback" was a guaranteed second failure, not a genuine alternative.
Fix (this stream, citing RULING-237 s2.1): mirror BaseConfigProvider's own
sibling _resolve_path in the same file, which already had the correct shape
-- on failure, log a warning and fall back to the raw, unresolved path string
rather than repeating the same sandboxed call or silently returning None.
`allow_absolute=True` was considered and rejected: core/fs/SERVICE-CONTRACT.md
s4 names `unsafe_allow_absolute_paths` as a deliberate, Master-ratified (R-2)
security opt-out for "fully trusted environments" only -- flipping it by
default in a shared base class used by every integration would silently
weaken a security invariant repo-wide, far outside this fix's scope.
`test_resolve_path_outside_sandbox_hits_bug_a_now_fixed` below is the real
canary: it constructs a provider with an absolute, out-of-sandbox
credentials_file and asserts the RESOLVED path is correct and usable, not
merely that no exception was raised.

BUG B (FIXED) -- github/auth.py used to import
`from quack_core.core.fs import service as fs` then call
fs.get_file_info / fs.read_json / fs.write_json. But
core/fs/service/__init__.py's public API is deliberately restricted to
FileSystemService / create_service / get_service only (its own __getattr__
raises AttributeError for anything else) -- those module-level convenience
functions live in core/fs/service/standalone, not service/__init__. Fix
(this stream, citing RULING-237 s2.2): changed the import to
`from quack_core.core.fs.service import standalone as fs`, matching the
already-correct precedent in integrations/pandoc/*.py exactly (drop-in, no
call-site changes needed -- standalone exposes the same four function
names). Same bug, same fix, independently applied to
google/mail/service.py:11 (a sibling file, out of this test file's scope but
covered by its own suite). The `_hits_bug_b`-named tests below now assert
the REAL, CORRECT (post-fix) success behavior instead of the AttributeError
they used to pin -- names kept as history (what they used to prove), bodies
changed to prove the fix actually works, not just that "no exception was
raised."

Boundary mocked in every test below: the GitHub REST API HTTP call
(`requests`-shaped `.get()`). No quack_core function under test is mocked.
"""

import json
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import requests
from quack_core.integrations.github.auth import GitHubAuthProvider


@pytest.fixture
def github_creds_relpath() -> Generator[Path]:
    """A credentials_file path RELATIVE to the worktree CWD, so it stays
    inside the FileSystemService singleton's base_dir -- kept relative (not
    testing sandbox-escape here) so these tests stay focused on BUG B's
    fixed behavior; BUG A's own dedicated canary
    (test_resolve_path_outside_sandbox_hits_bug_a_now_fixed) covers the
    out-of-sandbox path. Cleaned up after each test."""
    scratch = Path("test_scratch_github_creds")
    scratch.mkdir(exist_ok=True)
    try:
        yield scratch / "creds.json"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class FakeResponse(requests.Response):
    """Stands in for requests.Response -- the external boundary. Subclasses
    the real requests.Response (a no-arg __init__, safe to override) rather
    than duck-typing it, so it satisfies _HTTPClient's Protocol structurally
    for mypy (auth.py:26 declares `def get(...) -> requests.Response`,
    which a same-shaped-but-unrelated FakeResponse class does not satisfy
    even though every method it calls at runtime -- json(), raise_for_status(),
    .status_code, .text -- was already implemented identically here). Zero
    behavior change: only widens what mypy accepts, the fake methods below
    are untouched."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        text: str = "",
    ) -> None:
        super().__init__()
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        # requests.Response.text is a read-only @property derived from
        # ._content -- set the backing field directly rather than the
        # property (which subclassing now makes mypy correctly enforce).
        self._content = text.encode()

    def json(self, **kwargs: Any) -> dict[str, Any]:  # noqa: ANN401 -- overrides requests.Response.json's own **kwargs: Any passthrough to the stdlib json decoder
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            err = requests.exceptions.HTTPError(f"{self.status_code} error")
            err.response = self
            raise err


class FakeHTTPClient:
    """Implements the provider's `_HTTPClient` protocol (a `.get()` method) --
    the injectable external boundary. Never touches the network for real."""

    def __init__(
        self, response: FakeResponse | None = None, exc: Exception | None = None
    ) -> None:
        self._response = response
        self._exc = exc
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:  # noqa: ANN401 -- matches the real _HTTPClient protocol's own **kwargs: Any (auth.py's passthrough to requests.Session.get)
        self.calls.append((url, kwargs))
        if self._exc:
            raise self._exc
        assert self._response is not None
        return self._response


class TestGitHubAuthProviderConstruction:
    def test_name_property(self) -> None:
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        assert provider.name == "GitHub"

    def test_env_token_loaded_on_init(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "env-token-123")
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        assert provider.token == "env-token-123"  # noqa: S105 -- test fixture, fake credential value, not a real secret

    def test_no_env_token_leaves_token_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        assert provider.token is None

    def test_resolve_path_outside_sandbox_hits_bug_a_now_fixed(self) -> None:
        """RULING-237 s2.1: BUG A fixed. Before the fix, constructing a
        BaseAuthProvider subclass (GitHubAuthProvider) with a
        credentials_file OUTSIDE the FileSystemService singleton's base_dir
        raised an unhandled ValueError from _resolve_path's own
        except-branch fallback (standalone.resolve_path and
        standalone.normalize_path are aliases of the same sandboxed method,
        so the "fallback" was a guaranteed second identical failure -- see
        module docstring). After the fix, construction succeeds and
        credentials_file resolves to the real, correct, usable absolute
        path -- asserting the RESOLVED VALUE, not merely that no exception
        was raised, per the ruling's own proof requirement."""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_creds = str(Path(outside_dir) / "outside-creds.json")

            provider = GitHubAuthProvider(
                credentials_file=outside_creds, http_client=FakeHTTPClient()
            )

            # Resolution did not crash, and did not silently swallow to
            # None -- it returned the real path, still usable by the OS
            # directly (the fallback shape chosen per RULING-237 s2.1,
            # matching BaseConfigProvider's own sibling fallback). This is
            # BUG A's fix, proven: construction that used to raise an
            # unhandled ValueError now returns a correct, usable path.
            assert provider.credentials_file is not None
            assert Path(provider.credentials_file) == Path(outside_creds)

            # Corrected-guess note (not softened to force a pass): writing
            # THROUGH this out-of-sandbox path still correctly fails, via a
            # DIFFERENT, already-correctly-sandboxed call site --
            # BaseAuthProvider._ensure_credentials_directory() (base.py)
            # calls standalone.create_directory() on the parent dir, which
            # enforces the same base_dir sandbox as everything else in
            # core/fs (SERVICE-CONTRACT.md s4, Master-ratified R-2). That is
            # NOT part of RULING-237's two named bugs (it is neither
            # _resolve_path's fallback nor the broken `fs` import) and is
            # correct, intentional sandboxing behavior, not a bug --
            # confirmed live before writing this assertion. Directly
            # exercising fs.write_json (BUG B's own fix) on an in-sandbox
            # parent, independent of this out-of-sandbox path, is already
            # covered by TestSaveCredentials::test_save_credentials_hits_bug_b.
            assert provider.save_credentials() is False
            assert not Path(outside_creds).exists()


class TestAuthenticateSuccess:
    def test_authenticate_with_explicit_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(response=FakeResponse(200, {"login": "octocat"}))
        provider = GitHubAuthProvider(http_client=fake_client)

        result = provider.authenticate(token="explicit-token")  # noqa: S106 -- test fixture, fake credential value, not a real secret

        assert result.success is True
        assert result.token == "explicit-token"  # noqa: S105 -- test fixture, fake credential value, not a real secret
        assert provider.authenticated is True
        assert provider._user_info == {"login": "octocat"}
        # confirms the real code path actually called the boundary once,
        # with the real Authorization header shape
        assert len(fake_client.calls) == 1
        url, kwargs = fake_client.calls[0]
        assert url == "https://api.github.com/user"
        assert kwargs["headers"]["Authorization"] == "token explicit-token"

    def test_authenticate_with_credentials_file_hits_bug_b(
        self, github_creds_relpath: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RULING-237: BUG B fixed. authenticate()'s success path
        unconditionally calls self._save_token_data(self.token) with no
        try/except, so this exercises the real fs.write_json call through
        the fixed `standalone` import -- asserts the token actually
        persists to the real credentials file, not just that no exception
        was raised."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(response=FakeResponse(200, {"login": "duck"}))
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=fake_client
        )

        result = provider.authenticate(token="tok-abc")  # noqa: S106 -- test fixture, fake credential value, not a real secret

        assert result.success is True
        assert result.token == "tok-abc"  # noqa: S105 -- test fixture, fake credential value, not a real secret
        assert github_creds_relpath.exists()
        saved = json.loads(github_creds_relpath.read_text())
        assert saved["token"] == "tok-abc"  # noqa: S105 -- test fixture, fake credential value, not a real secret

    def test_authenticate_falls_back_to_env_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "fallback-env-token")
        fake_client = FakeHTTPClient(response=FakeResponse(200, {"login": "x"}))
        # No explicit token passed to __init__ path either -- provider
        # picks up env var at construction, authenticate() re-confirms it.
        provider = GitHubAuthProvider(http_client=fake_client)

        result = provider.authenticate()

        assert result.success is True
        assert result.token == "fallback-env-token"  # noqa: S105 -- test fixture, fake credential value, not a real secret

    def test_authenticate_loads_token_from_credentials_file_hits_bug_b(
        self, github_creds_relpath: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RULING-237: BUG B fixed. authenticate()'s no-explicit-token
        branch calls self._load_credentials() first (real fs.read_json,
        fixed import) before it ever reaches the HTTP boundary -- asserts
        the token actually loaded from the real file drives a real
        successful authentication."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        github_creds_relpath.write_text('{"token": "from-file-token"}')
        fake_client = FakeHTTPClient(response=FakeResponse(200, {"login": "y"}))
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=fake_client
        )

        result = provider.authenticate()

        assert result.success is True
        assert result.token == "from-file-token"  # noqa: S105 -- test fixture, fake credential value, not a real secret
        assert len(fake_client.calls) == 1
        _, kwargs = fake_client.calls[0]
        assert kwargs["headers"]["Authorization"] == "token from-file-token"


class TestAuthenticateFailure:
    def test_authenticate_no_token_anywhere_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())

        result = provider.authenticate()

        assert result.success is False
        assert result.error == "No GitHub token provided"

    def test_authenticate_401_reports_invalid_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(response=FakeResponse(401, text="bad creds"))
        provider = GitHubAuthProvider(http_client=fake_client)

        result = provider.authenticate(token="bad-token")  # noqa: S106 -- test fixture, fake credential value, not a real secret

        assert result.success is False
        assert result.error == "Invalid GitHub token (unauthorized)"
        assert result.message == "bad creds"

    def test_authenticate_403_reports_lacking_permissions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(response=FakeResponse(403, text="forbidden"))
        provider = GitHubAuthProvider(http_client=fake_client)

        result = provider.authenticate(token="tok")  # noqa: S106 -- test fixture, fake credential value, not a real secret

        assert result.success is False
        assert result.error == "GitHub token lacks required permissions"

    def test_authenticate_other_http_error_generic_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(response=FakeResponse(500, text="server error"))
        provider = GitHubAuthProvider(http_client=fake_client)

        result = provider.authenticate(token="tok")  # noqa: S106 -- test fixture, fake credential value, not a real secret

        assert result.success is False
        assert result.error is not None
        assert "500" in result.error

    def test_authenticate_connection_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(
            exc=requests.exceptions.ConnectionError("network unreachable")
        )
        provider = GitHubAuthProvider(http_client=fake_client)

        result = provider.authenticate(token="tok")  # noqa: S106 -- test fixture, fake credential value, not a real secret

        assert result.success is False
        assert result.error is not None
        assert "GitHub API connection error" in result.error


class TestRefreshCredentials:
    def test_refresh_no_token_fails(self) -> None:
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        provider.token = None

        result = provider.refresh_credentials()

        assert result.success is False
        assert result.error == "No GitHub token available to refresh"

    def test_refresh_valid_token_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(response=FakeResponse(200, {"login": "z"}))
        provider = GitHubAuthProvider(http_client=fake_client)
        provider.token = "still-valid"  # noqa: S105 -- test fixture, fake credential value, not a real secret

        result = provider.refresh_credentials()

        assert result.success is True
        assert result.token == "still-valid"  # noqa: S105 -- test fixture, fake credential value, not a real secret
        assert provider._user_info == {"login": "z"}

    def test_refresh_request_exception_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(exc=requests.exceptions.Timeout("timed out"))
        provider = GitHubAuthProvider(http_client=fake_client)
        provider.token = "some-token"  # noqa: S105 -- test fixture, fake credential value, not a real secret

        result = provider.refresh_credentials()

        assert result.success is False
        assert result.error is not None
        assert "Failed to validate GitHub token" in result.error


class TestGetCredentials:
    def test_get_credentials_returns_current_token(self) -> None:
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        provider.token = "abc"  # noqa: S105 -- test fixture, fake credential value, not a real secret
        provider._user_info = {"login": "u"}

        creds = provider.get_credentials()

        assert creds == {"token": "abc", "user_info": {"login": "u"}}

    def test_get_credentials_loads_from_file_when_no_token_hits_bug_b(
        self, github_creds_relpath: Path
    ) -> None:
        """RULING-237: BUG B fixed. get_credentials() calls
        self._load_credentials() when self.token is falsy (real
        fs.get_file_info, fixed import) -- asserts the loaded token is
        actually returned, not just that no exception was raised."""
        github_creds_relpath.write_text('{"token": "loaded-tok"}')
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )
        provider.token = None

        creds = provider.get_credentials()

        assert creds == {"token": "loaded-tok", "user_info": None}
        assert provider.token == "loaded-tok"  # noqa: S105 -- test fixture, fake credential value, not a real secret

    def test_get_credentials_no_file_no_token(self) -> None:
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        provider.token = None
        provider.credentials_file = None

        creds = provider.get_credentials()

        assert creds == {"token": None, "user_info": None}


class TestSaveCredentials:
    def test_save_credentials_no_token_returns_false(self) -> None:
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        provider.token = None

        assert provider.save_credentials() is False

    def test_save_credentials_hits_bug_b(self, github_creds_relpath: Path) -> None:
        """RULING-237: BUG B fixed. save_credentials() delegates straight to
        self._save_token_data() (real fs.write_json, fixed import) --
        asserts the token actually persists to the real file."""
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )
        provider.token = "save-me"  # noqa: S105 -- test fixture, fake credential value, not a real secret

        assert provider.save_credentials() is True
        assert github_creds_relpath.exists()
        saved = json.loads(github_creds_relpath.read_text())
        assert saved["token"] == "save-me"  # noqa: S105 -- test fixture, fake credential value, not a real secret


class TestLoadCredentialsPrivate:
    def test_load_credentials_no_file_configured(self) -> None:
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        provider.credentials_file = None

        assert provider._load_credentials() is None

    def test_load_credentials_file_does_not_exist_hits_bug_b(
        self, github_creds_relpath: Path
    ) -> None:
        """RULING-237: BUG B fixed. _load_credentials()'s existence check
        calls the real fs.get_file_info() (fixed import) and correctly
        determines the file is missing -- the INTENDED early-return-None
        behavior, now reachable."""
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath),
            http_client=FakeHTTPClient(),
        )

        assert provider._load_credentials() is None

    def test_load_credentials_file_not_valid_json_hits_bug_b(
        self, github_creds_relpath: Path
    ) -> None:
        """RULING-237: BUG B fixed. Real fs.read_json() on malformed JSON
        returns a failed (non-raising) result; _load_credentials() logs and
        returns None -- the real, correct behavior."""
        github_creds_relpath.write_text("not json at all {{{")
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )

        assert provider._load_credentials() is None

    def test_load_credentials_hits_bug_b(self, github_creds_relpath: Path) -> None:
        """RULING-237: BUG B fixed. Real fs.get_file_info() + fs.read_json()
        round-trip a real credentials file and return its real parsed
        contents."""
        github_creds_relpath.write_text('{"token": "real-token", "saved_at": 123}')
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )

        result = provider._load_credentials()

        assert result == {"token": "real-token", "saved_at": 123}


class TestSaveTokenDataPrivate:
    def test_save_token_data_no_token_returns_false(
        self, github_creds_relpath: Path
    ) -> None:
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath),
            http_client=FakeHTTPClient(),
        )

        # Returns False before reaching any fs.* call (not token or not
        # credentials_file guard) -- real correct behavior, no bug involved.
        assert provider._save_token_data(None) is False

    def test_save_token_data_no_credentials_file_returns_false(self) -> None:
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        provider.credentials_file = None

        assert provider._save_token_data("tok") is False

    def test_save_token_data_hits_bug_b(self, github_creds_relpath: Path) -> None:
        """RULING-237: BUG B fixed. Real fs.write_json() (fixed import)
        actually persists the token + user_info to the real file."""
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )
        provider._user_info = {"login": "has-info"}

        assert provider._save_token_data("tok-123") is True  # noqa: S106 -- test fixture, fake credential value, not a real secret
        assert github_creds_relpath.exists()
        saved = json.loads(github_creds_relpath.read_text())
        assert saved["token"] == "tok-123"  # noqa: S105 -- test fixture, fake credential value, not a real secret
        assert saved["user_info"] == {"login": "has-info"}
