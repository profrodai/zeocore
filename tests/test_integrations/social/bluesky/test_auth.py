"""Tests for BlueskyAuthProvider.

Mocks at the session-client boundary (a fake `_BlueskySessionClient`, never
the provider's own methods), matching NotionAuthProvider's own test
pattern (`_FakeSDKClient`) and RULING-235's "mock at the boundary, not the
function under test."
"""

import json
import shutil
import stat
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.social.bluesky.auth import BlueskyAuthProvider


def _as_dict(value: object) -> dict[str, object]:
    """Narrow `BlueskyAuthProvider.get_credentials()`'s `object` return
    (the `AuthProviderProtocol` contract) back to the concrete
    `dict[str, object]` it always actually returns, for mypy's benefit in
    these tests."""
    assert isinstance(value, dict)
    return value


class _FakeSessionClient:
    def __init__(
        self, response: dict | None = None, error: Exception | None = None
    ) -> None:
        self._response = response or {
            "accessJwt": "access-tok",
            "refreshJwt": "refresh-tok",
            "did": "did:plc:abc123",
            "handle": "alice.bsky.social",
        }
        self._error = error
        self.create_post_record_calls: list[dict] = []

    def create_session(self, identifier: str, password: str) -> dict:
        if self._error:
            raise self._error
        return self._response

    def create_post_record(self, **kwargs: object) -> dict:
        self.create_post_record_calls.append(kwargs)
        return {"uri": "at://did:plc:abc/app.bsky.feed.post/xyz", "cid": "bafyabc"}


class _UnauthorizedError(Exception):
    status = 401


@pytest.fixture
def creds_relpath() -> Generator[Path]:
    """A credentials_file path RELATIVE to the worktree CWD, staying inside
    the FileSystemService singleton's sandboxed base_dir -- mirrors
    NotionAuthProvider's own `notion_creds_relpath` fixture."""
    scratch = Path("test_scratch_bluesky_creds")
    scratch.mkdir(exist_ok=True)
    try:
        yield scratch / "creds.json"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


@pytest.fixture
def fake_factory() -> MagicMock:
    return MagicMock(side_effect=lambda service_url: _FakeSessionClient())


class TestBlueskyAuthProviderBasics:
    def test_name_property(self) -> None:
        assert BlueskyAuthProvider().name == "Bluesky"

    def test_authenticate_no_credentials_anywhere(self) -> None:
        provider = BlueskyAuthProvider()
        result = provider.authenticate()

        assert result.success is False
        assert result.error == "No Bluesky identifier/app_password provided"

    def test_authenticate_with_provided_credentials(
        self, fake_factory: MagicMock, creds_relpath: Path
    ) -> None:
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=fake_factory
        )
        result = provider.authenticate(
            identifier="alice.bsky.social",
            app_password="app-pw",  # noqa: S106
        )

        assert result.success is True
        assert provider._access_jwt == "access-tok"  # noqa: S105 -- provider-owned fake credential
        assert provider.authenticated is True
        assert provider.did == "did:plc:abc123"
        assert provider.handle == "alice.bsky.social"
        fake_factory.assert_called_once_with("https://bsky.social")

    def test_authenticate_invalid_credentials_401(self, creds_relpath: Path) -> None:
        factory = MagicMock(
            side_effect=lambda service_url: _FakeSessionClient(
                error=_UnauthorizedError("bad password")
            )
        )
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=factory
        )
        result = provider.authenticate(identifier="alice", app_password="wrong")  # noqa: S106

        assert result.success is False
        assert result.error is not None
        assert "unauthorized" in result.error.lower()

    def test_authenticate_generic_error_wrapped(self, creds_relpath: Path) -> None:
        factory = MagicMock(
            side_effect=lambda service_url: _FakeSessionClient(
                error=RuntimeError("network exploded")
            )
        )
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=factory
        )
        result = provider.authenticate(identifier="alice", app_password="pw")  # noqa: S106

        assert result.success is False
        assert result.error is not None
        assert "network exploded" in result.error

    def test_custom_service_url_is_used(
        self, fake_factory: MagicMock, creds_relpath: Path
    ) -> None:
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=fake_factory
        )
        provider.authenticate(
            identifier="alice",
            app_password="pw",  # noqa: S106
            service_url="https://custom.pds.example",
        )

        fake_factory.assert_called_once_with("https://custom.pds.example")


class TestBlueskyAuthProviderCredentialPersistence:
    def test_authenticate_persists_credentials_0600_atomic(
        self, fake_factory: MagicMock, creds_relpath: Path
    ) -> None:
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=fake_factory
        )

        result = provider.authenticate(identifier="alice", app_password="secret-pw")  # noqa: S106
        assert result.success is True

        assert creds_relpath.exists()
        mode = stat.S_IMODE(creds_relpath.stat().st_mode)
        assert mode == 0o600, f"expected 0600, got {oct(mode)}"

        on_disk = json.loads(creds_relpath.read_text())
        assert on_disk["identifier"] == "alice"
        assert on_disk["app_password"] == "secret-pw"  # noqa: S105
        assert on_disk["did"] == "did:plc:abc123"
        assert "saved_at" in on_disk

    def test_authenticate_loads_from_credentials_file_when_not_provided(
        self, fake_factory: MagicMock, creds_relpath: Path
    ) -> None:
        creds_relpath.write_text(
            json.dumps(
                {
                    "identifier": "stored-user.bsky.social",
                    "app_password": "stored-pw",
                    "service_url": "https://bsky.social",
                }
            )
        )
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=fake_factory
        )

        result = provider.authenticate()

        assert result.success is True
        fake_factory.assert_called_once()

    def test_no_credentials_file_save_returns_false(self) -> None:
        provider = BlueskyAuthProvider(credentials_file=None)
        provider.identifier = "alice"
        provider.app_password = "pw"  # noqa: S105

        assert provider._save_token_data() is False

    def test_directory_creation_failure_returns_false(
        self, fake_factory: MagicMock, creds_relpath: Path
    ) -> None:
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=fake_factory
        )
        provider.identifier = "alice"
        provider.app_password = "pw"  # noqa: S105

        failing_dir_result = MagicMock(ok=False, error="disk full")
        with patch(
            "zeo_core.integrations.social.bluesky.auth.create_directory_with_fallback",
            return_value=failing_dir_result,
        ):
            assert provider._save_token_data() is False

    def test_load_credentials_no_credentials_file_returns_none(self) -> None:
        provider = BlueskyAuthProvider(credentials_file=None)
        assert provider._load_credentials() is None

    def test_load_credentials_file_does_not_exist_returns_none(
        self, creds_relpath: Path
    ) -> None:
        # creds_relpath fixture creates the parent dir but not the file itself.
        provider = BlueskyAuthProvider(credentials_file=str(creds_relpath))
        assert provider._load_credentials() is None

    def test_load_credentials_read_failure_returns_none(
        self, creds_relpath: Path
    ) -> None:
        creds_relpath.write_text("not valid json{{{")
        provider = BlueskyAuthProvider(credentials_file=str(creds_relpath))
        assert provider._load_credentials() is None


class TestBlueskyAuthProviderRefreshAndCredentials:
    def test_refresh_credentials_reauthenticates_with_stored_password(
        self, fake_factory: MagicMock, creds_relpath: Path
    ) -> None:
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=fake_factory
        )
        provider.authenticate(identifier="alice", app_password="pw")  # noqa: S106

        result = provider.refresh_credentials()

        assert result.success is True
        assert fake_factory.call_count == 2  # one for authenticate, one for refresh

    def test_refresh_credentials_no_prior_auth_errors(self) -> None:
        provider = BlueskyAuthProvider()
        result = provider.refresh_credentials()

        assert result.success is False
        assert result.error is not None
        assert "no bluesky identifier" in result.error.lower()

    def test_get_credentials_returns_current_state(
        self, fake_factory: MagicMock, creds_relpath: Path
    ) -> None:
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=fake_factory
        )
        provider.authenticate(identifier="alice", app_password="pw")  # noqa: S106

        creds = _as_dict(provider.get_credentials())

        assert creds["identifier"] == "alice"
        assert creds["did"] == "did:plc:abc123"
        assert creds["access_jwt"] == "access-tok"  # noqa: S105

    def test_get_credentials_loads_from_file_when_not_in_memory(
        self, creds_relpath: Path
    ) -> None:
        creds_relpath.write_text(
            json.dumps({"identifier": "loaded-user", "app_password": "loaded-pw"})
        )
        provider = BlueskyAuthProvider(credentials_file=str(creds_relpath))

        creds = _as_dict(provider.get_credentials())

        assert creds["identifier"] == "loaded-user"

    def test_save_credentials_delegates_to_save_token_data(
        self, fake_factory: MagicMock, creds_relpath: Path
    ) -> None:
        provider = BlueskyAuthProvider(
            credentials_file=str(creds_relpath), session_client_factory=fake_factory
        )
        provider.authenticate(identifier="alice", app_password="pw")  # noqa: S106

        assert provider.save_credentials() is True


class TestBuildClient:
    def test_build_client_uses_injected_factory(self, fake_factory: MagicMock) -> None:
        provider = BlueskyAuthProvider(session_client_factory=fake_factory)
        provider.service_url = "https://bsky.social"

        client = provider.build_client()

        fake_factory.assert_called_once_with("https://bsky.social")
        assert isinstance(client, _FakeSessionClient)

    def test_build_client_explicit_service_url_overrides_default(
        self, fake_factory: MagicMock
    ) -> None:
        provider = BlueskyAuthProvider(session_client_factory=fake_factory)

        provider.build_client("https://other.pds.example")

        fake_factory.assert_called_once_with("https://other.pds.example")

    def test_build_client_no_factory_returns_real_bluesky_client(self) -> None:
        from zeo_core.integrations.social.bluesky.client import BlueskyClient

        provider = BlueskyAuthProvider()
        client = provider.build_client("https://bsky.social")

        assert isinstance(client, BlueskyClient)
