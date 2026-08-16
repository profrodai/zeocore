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
Two PRE-EXISTING PRODUCTION BUGS were discovered writing this file (not
introduced by it, and out of this stream's circle of control to fix --
recorded here and in the SOW ledger for escalation):

BUG A -- integrations/core/base.py::BaseAuthProvider._resolve_path()
crashes with an unhandled ValueError for ANY credentials_file path outside
the FileSystemService singleton's base_dir (== CWD). Its own except-Exception
fallback (line 59-60) repeats the identical mistake (passes a possibly
ok=False PathResult straight into coerce_path_str, which fails fast on a
failed Result by design -- core/fs/normalize.py's _unwrap_result_like is
correct; base.py's caller is not). This affects every BaseAuthProvider
subclass (confirmed also crashes GoogleAuthProvider), for the overwhelmingly
common real-world case of a credentials file outside the process CWD. The
existing test suite never caught it because github/test_integration.py's
one test that would exercise the real construction path is `SKIPPED`, and
every other existing test either mocks _verify_client_secrets_file/
_initialize_config or never passes an out-of-CWD path.
WORKAROUND USED BELOW (not a fix): pass a credentials_file path RELATIVE to
the worktree CWD (via the `github_creds_relpath` fixture), which stays
inside base_dir and avoids the crash -- this still exercises real
_resolve_path/coerce_path_str code, just not the sandbox-escape branch,
which is the actual bug and not this stream's to silently patch.

BUG B -- github/auth.py itself does `from quack_core.core.fs import service
as fs` then calls fs.get_file_info / fs.read_json / fs.write_json. But
core/fs/service/__init__.py's public API is deliberately restricted to
FileSystemService / create_service / get_service only (its own __getattr__
raises AttributeError for anything else) -- those module-level convenience
functions live in core/fs/service/standalone, not service/__init__. Compare
integrations/pandoc/*.py, which correctly imports
`from quack_core.core.fs.service import standalone as fs`. This means
GitHubAuthProvider._load_credentials() and _save_token_data() are BROKEN
in production today: calling either with a real credentials_file raises
AttributeError, not the documented behavior. (Same bug, second occurrence:
google/mail/service.py:197 calls fs.create_directory() through the same
broken import.) Per RULING-234/CLAUDE.md's own discipline (assert real
behavior, never a guess softened to pass), the tests below for these two
methods assert the REAL (buggy) AttributeError outcome rather than a
fictional working one -- this pins the bug with a real failing-red canary
rather than hiding it, and is the honest thing to test until Master rules
on the fix. Every other GitHubAuthProvider method that does NOT go through
this broken fs.* call chain is tested against real, correct behavior.

Boundary mocked in every test below: the GitHub REST API HTTP call
(`requests`-shaped `.get()`). No quack_core function under test is mocked.
"""

import shutil
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import requests
from quack_core.integrations.github.auth import GitHubAuthProvider


@pytest.fixture
def github_creds_relpath() -> Generator[Path]:
    """A credentials_file path RELATIVE to the worktree CWD, so it stays
    inside the FileSystemService singleton's base_dir and avoids BUG A
    (see module docstring). Cleaned up after each test."""
    scratch = Path("test_scratch_github_creds")
    scratch.mkdir(exist_ok=True)
    try:
        yield scratch / "creds.json"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class FakeResponse:
    """Stands in for requests.Response -- the external boundary. Not a
    quack_core object; this is the fake that replaces the real HTTP call."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            err = requests.exceptions.HTTPError(f"{self.status_code} error")
            err.response = self  # type: ignore[assignment]
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
        """Pins BUG B (see module docstring): authenticate()'s success path
        unconditionally calls self._save_token_data(self.token) with no
        try/except, so a real credentials_file makes authenticate() ITSELF
        crash today via the broken `fs.write_json` import -- not just
        _save_token_data() in isolation. This is real, current behavior,
        asserted honestly rather than assumed away."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fake_client = FakeHTTPClient(response=FakeResponse(200, {"login": "duck"}))
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=fake_client
        )

        with pytest.raises(AttributeError, match="write_json"):
            provider.authenticate(token="tok-abc")  # noqa: S106 -- test fixture, fake credential value, not a real secret

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
        """authenticate()'s no-explicit-token branch calls
        self._load_credentials() first, which hits BUG B (fs.read_json)
        before it ever reaches the HTTP boundary. Pins the real crash."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        github_creds_relpath.write_text('{"token": "from-file-token"}')
        fake_client = FakeHTTPClient(response=FakeResponse(200, {"login": "y"}))
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=fake_client
        )

        with pytest.raises(AttributeError, match="get_file_info"):
            provider.authenticate()


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
        """get_credentials() calls self._load_credentials() when self.token
        is falsy, which hits BUG B (fs.get_file_info). Pins the real crash."""
        github_creds_relpath.write_text('{"token": "loaded-tok"}')
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )
        provider.token = None

        with pytest.raises(AttributeError, match="get_file_info"):
            provider.get_credentials()

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
        """save_credentials() delegates straight to self._save_token_data(),
        which hits BUG B (fs.write_json). Pins the real crash."""
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )
        provider.token = "save-me"  # noqa: S105 -- test fixture, fake credential value, not a real secret

        with pytest.raises(AttributeError, match="write_json"):
            provider.save_credentials()


class TestLoadCredentialsPrivate:
    def test_load_credentials_no_file_configured(self) -> None:
        provider = GitHubAuthProvider(http_client=FakeHTTPClient())
        provider.credentials_file = None

        assert provider._load_credentials() is None

    def test_load_credentials_file_does_not_exist_hits_bug_b(
        self, github_creds_relpath: Path
    ) -> None:
        """_load_credentials()'s existence check itself calls
        fs.get_file_info() (BUG B) before it can even determine the file is
        missing -- pins the real crash rather than the intended
        early-return-None behavior."""
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath),
            http_client=FakeHTTPClient(),
        )

        with pytest.raises(AttributeError, match="get_file_info"):
            provider._load_credentials()

    def test_load_credentials_file_not_valid_json_hits_bug_b(
        self, github_creds_relpath: Path
    ) -> None:
        github_creds_relpath.write_text("not json at all {{{")
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )

        with pytest.raises(AttributeError, match="get_file_info"):
            provider._load_credentials()

    def test_load_credentials_hits_bug_b(self, github_creds_relpath: Path) -> None:
        github_creds_relpath.write_text('{"token": "real-token", "saved_at": 123}')
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )

        with pytest.raises(AttributeError, match="get_file_info"):
            provider._load_credentials()


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
        provider = GitHubAuthProvider(
            credentials_file=str(github_creds_relpath), http_client=FakeHTTPClient()
        )
        provider._user_info = {"login": "has-info"}

        with pytest.raises(AttributeError, match="write_json"):
            provider._save_token_data("tok-123")
