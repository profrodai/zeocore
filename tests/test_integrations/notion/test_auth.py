"""Tests for Notion authentication provider."""

import os
import platform
import shutil
import stat
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.notion.auth import NotionAuthProvider


@pytest.fixture
def notion_creds_relpath() -> Generator[Path]:
    """A credentials_file path RELATIVE to the worktree CWD, so it stays
    inside the FileSystemService singleton's sandboxed base_dir. Absolute
    tmp_path-style paths outside the repo are rejected by core/fs's sandbox
    (confirmed against integrations/github/test_auth_provider.py's own
    documented BUG A / github_creds_relpath fixture, same underlying
    zeo_core.core.fs.service sandbox both providers go through) -- this is
    the sanctioned pattern, not a workaround around a real product bug.
    Cleaned up after each test."""
    scratch = Path("test_scratch_notion_creds")
    scratch.mkdir(exist_ok=True)
    try:
        yield scratch / "creds.json"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class _FakeUsersEndpoint:
    def __init__(
        self, response: dict | None = None, error: Exception | None = None
    ) -> None:
        self._response = response or {"id": "bot-1", "name": "Test Bot"}
        self._error = error

    def me(self) -> dict:
        if self._error:
            raise self._error
        return self._response


class _FakeSDKClient:
    def __init__(
        self, response: dict | None = None, error: Exception | None = None
    ) -> None:
        self.users = _FakeUsersEndpoint(response=response, error=error)


class _UnauthorizedError(Exception):
    status = 401


@pytest.fixture
def fake_factory() -> MagicMock:
    """Factory that always returns a working fake SDK client."""
    return MagicMock(side_effect=lambda token: _FakeSDKClient())


class TestNotionAuthProvider:
    """Tests for NotionAuthProvider."""

    def test_name_property(self) -> None:
        provider = NotionAuthProvider()
        assert provider.name == "Notion"

    def test_loads_token_from_env_on_init(self) -> None:
        with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
            provider = NotionAuthProvider()
            assert provider.token == "env_token"  # noqa: S105

    def test_authenticate_with_provided_token(self, fake_factory: MagicMock) -> None:
        provider = NotionAuthProvider(sdk_client_factory=fake_factory)
        result = provider.authenticate(token="explicit_token")  # noqa: S106 -- test fixture, fake credential value

        assert result.success is True
        assert result.token == "explicit_token"  # noqa: S105
        assert provider.authenticated is True
        fake_factory.assert_called_once_with("explicit_token")

    def test_authenticate_no_token_anywhere(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            provider = NotionAuthProvider()
            result = provider.authenticate()

            assert result.success is False
            assert result.error == "No Notion token provided"

    def test_authenticate_invalid_token_401(self) -> None:
        factory = MagicMock(
            side_effect=lambda token: _FakeSDKClient(
                error=_UnauthorizedError("bad token")
            )
        )
        provider = NotionAuthProvider(sdk_client_factory=factory)
        result = provider.authenticate(token="bad_token")  # noqa: S106 -- test fixture, fake credential value

        assert result.success is False
        assert result.error is not None
        assert "unauthorized" in result.error.lower()

    def test_authenticate_generic_api_error(self) -> None:
        factory = MagicMock(
            side_effect=lambda token: _FakeSDKClient(error=RuntimeError("boom"))
        )
        provider = NotionAuthProvider(sdk_client_factory=factory)
        result = provider.authenticate(token="some_token")  # noqa: S106 -- test fixture, fake credential value

        assert result.success is False
        assert result.error is not None
        assert "boom" in result.error

    def test_authenticate_loads_from_credentials_file(
        self, notion_creds_relpath: Path, fake_factory: MagicMock
    ) -> None:
        notion_creds_relpath.write_text('{"token": "file_token"}')

        with patch.dict(os.environ, {}, clear=True):
            provider = NotionAuthProvider(
                credentials_file=str(notion_creds_relpath),
                sdk_client_factory=fake_factory,
            )
            result = provider.authenticate()

            assert result.success is True
            assert result.token == "file_token"  # noqa: S105

    def test_refresh_credentials_no_token(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            provider = NotionAuthProvider()
            result = provider.refresh_credentials()

            assert result.success is False
            assert result.error == "No Notion token available to refresh"

    def test_refresh_credentials_valid(self, fake_factory: MagicMock) -> None:
        provider = NotionAuthProvider(sdk_client_factory=fake_factory)
        provider.token = "good_token"  # noqa: S105

        result = provider.refresh_credentials()

        assert result.success is True
        assert result.token == "good_token"  # noqa: S105

    def test_refresh_credentials_failure(self) -> None:
        factory = MagicMock(
            side_effect=lambda token: _FakeSDKClient(error=RuntimeError("dead"))
        )
        provider = NotionAuthProvider(sdk_client_factory=factory)
        provider.token = "stale_token"  # noqa: S105

        result = provider.refresh_credentials()

        assert result.success is False
        assert result.error is not None
        assert "dead" in result.error

    def test_get_credentials(self, fake_factory: MagicMock) -> None:
        provider = NotionAuthProvider(sdk_client_factory=fake_factory)
        provider.authenticate(token="tok")  # noqa: S106 -- test fixture, fake credential value

        creds = provider.get_credentials()
        assert isinstance(creds, dict)
        assert creds["token"] == "tok"  # noqa: S105
        assert creds["user_info"] == {"id": "bot-1", "name": "Test Bot"}

    def test_save_and_load_credentials_round_trip(
        self, notion_creds_relpath: Path, fake_factory: MagicMock
    ) -> None:
        creds_file = notion_creds_relpath
        provider = NotionAuthProvider(
            credentials_file=str(creds_file), sdk_client_factory=fake_factory
        )
        provider.authenticate(token="round_trip_token")  # noqa: S106 -- test fixture, fake credential value

        assert provider.save_credentials() is True
        assert creds_file.exists()

        # A fresh provider with no in-memory token loads it back from disk.
        provider2 = NotionAuthProvider(
            credentials_file=str(creds_file), sdk_client_factory=fake_factory
        )
        with patch.dict(os.environ, {}, clear=True):
            creds = provider2.get_credentials()
            assert isinstance(creds, dict)
            assert creds["token"] == "round_trip_token"  # noqa: S105

    @pytest.mark.skipif(platform.system() == "Windows", reason="POSIX file modes only")
    def test_save_credentials_writes_file_at_mode_0600(
        self, notion_creds_relpath: Path, fake_factory: MagicMock
    ) -> None:
        """config-secrets-hardening charter item 3 / RULING-356 s4.4 item 4:
        notion/auth.py:222 must pass mode=0600 through to the fs write path
        so a live bearer token never lands world- or group-readable."""
        creds_file = notion_creds_relpath
        provider = NotionAuthProvider(
            credentials_file=str(creds_file), sdk_client_factory=fake_factory
        )
        provider.authenticate(token="mode_check_token")  # noqa: S106 -- test fixture, fake credential value

        old_umask = os.umask(0o022)
        try:
            assert provider.save_credentials() is True
        finally:
            os.umask(old_umask)

        assert stat.S_IMODE(creds_file.stat().st_mode) == 0o600

    def test_save_credentials_no_token_returns_false(self) -> None:
        provider = NotionAuthProvider()
        provider.token = None
        assert provider.save_credentials() is False

    def test_build_client_uses_real_sdk_when_no_factory_injected(self) -> None:
        """_build_client's real (non-injected) path constructs an actual
        notion_client.Client -- confirms the default wiring is real."""
        import notion_client

        provider = NotionAuthProvider()
        client = provider._build_client("some_token")

        assert isinstance(client, notion_client.Client)

    def test_authenticate_falls_back_to_env_token_when_no_stored_token(
        self, fake_factory: MagicMock
    ) -> None:
        """authenticate() with no explicit token and no credentials file
        falls through to the NOTION_TOKEN env-var check inside
        authenticate() itself (not just __init__'s own env read)."""
        provider = NotionAuthProvider(sdk_client_factory=fake_factory)
        provider.token = None  # simulate __init__ having found nothing

        with patch.dict(os.environ, {"NOTION_TOKEN": "late_env_token"}):
            result = provider.authenticate()

            assert result.success is True
            assert result.token == "late_env_token"  # noqa: S105

    def test_load_credentials_file_does_not_exist(
        self, notion_creds_relpath: Path
    ) -> None:
        provider = NotionAuthProvider(credentials_file=str(notion_creds_relpath))
        # notion_creds_relpath fixture yields a path but does not create it.
        assert provider._load_credentials() is None

    def test_load_credentials_file_not_valid_json(
        self, notion_creds_relpath: Path
    ) -> None:
        notion_creds_relpath.write_text("not valid json{{{")
        provider = NotionAuthProvider(credentials_file=str(notion_creds_relpath))

        assert provider._load_credentials() is None
