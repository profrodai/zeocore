"""Fresh-directory construction is an acceptance criterion, not a hope
(RULING-409 s6c / SOW-02's `done_when`).

RULING-409 s3 reproduced: from a fresh directory with no repo and no
config, `drive`/`calendar` RAISE (they resolve config in `__init__`) while
`mail` does not (it defers to `initialize()`). This test proves
`BlueskyIntegration` follows `mail`'s pattern rather than `drive`'s --
zero-argument construction from a genuinely empty directory must never
raise, and only `initialize()` may fail, and only for a reason connected to
actually authenticating (never bare config resolution).

Mirrors the shape of
`tests/test_integrations/google/test_fresh_directory_walkthrough.py`
(the charter's own named precedent for this class of test), but Bluesky
needs none of that test's platformdirs-migration machinery -- there is no
legacy CWD-relative default to migrate away from (greenfield). What is
shared is the actual walkthrough discipline: `monkeypatch.chdir(tmp_path)`
into a genuinely empty directory, then exercise the real, unmocked
construction and credential-save code paths, mocking only the true
external boundary (the AT Protocol network call).
"""

import json
import stat
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.social.bluesky import credential_paths as cp
from zeo_core.integrations.social.bluesky.service import BlueskyIntegration


@pytest.fixture(autouse=True)
def _isolated_singleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None]:
    from zeo_core.core.fs.service import get_service

    monkeypatch.chdir(tmp_path)
    get_service.cache_clear()
    cp._scoped_service_cache.clear()
    yield
    get_service.cache_clear()
    cp._scoped_service_cache.clear()


@pytest.fixture
def platformdirs_home(tmp_path: Path) -> Generator[Path]:
    """Stands in for the real machine's per-user config directory -- same
    role as the Google walkthrough's own `platformdirs_home` fixture."""
    d = tmp_path.parent / f"{tmp_path.name}-platformdirs-home"
    d.mkdir(exist_ok=True)
    with patch.object(cp.platformdirs, "user_config_dir", return_value=str(d)):
        yield d


class TestFreshDirectoryConstructionNeverRaises:
    """The literal acceptance predicate: construction from a directory
    with no repo and no config must never raise."""

    def test_zero_arg_construction_from_empty_directory_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        assert list(tmp_path.iterdir()) == []

        # This is the whole point: no try/except here. If __init__ resolves
        # config eagerly (the drive/calendar defect RULING-409 s3
        # reproduced), this line raises ZeoConfigurationError and the test
        # fails with that traceback, exactly as intended.
        integration = BlueskyIntegration()

        assert integration.is_available() is False
        assert integration.name == "Bluesky"

    def test_construction_touches_no_disk_under_fresh_cwd(self, tmp_path: Path) -> None:
        assert list(tmp_path.iterdir()) == []

        BlueskyIntegration()

        # Construction alone must create nothing under the fresh CWD --
        # not even a config/ directory, matching the Google walkthrough's
        # own "nothing was written anywhere under the fresh directory"
        # assertion for its own construction-time defect.
        assert list(tmp_path.iterdir()) == []

    def test_registered_entry_point_construct_and_call_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        """Walks the exact path RULING-409 s3 used to reproduce the
        original defect: importing the REGISTERED entry point
        (pyproject.toml, `social.bluesky`) and constructing it, from a
        fresh directory."""
        from zeo_core.integrations.social.bluesky import create_integration

        integration = create_integration()

        assert integration.is_available() is False


class TestFreshDirectoryFullWalkthrough:
    """The companion proof: not just "construction doesn't raise" but the
    full authenticate-and-save path works correctly from a fresh directory,
    with the credential landing at the platformdirs location -- never CWD
    -- at mode 0600."""

    def test_authorize_from_fresh_directory_lands_credential_in_platformdirs_0600(
        self, tmp_path: Path, platformdirs_home: Path
    ) -> None:
        assert list(tmp_path.iterdir()) == []

        integration = BlueskyIntegration()

        fake_session_client = MagicMock()
        fake_session_client.create_session.return_value = {
            "accessJwt": "lucys-access-token",
            "refreshJwt": "lucys-refresh-token",
            "did": "did:plc:lucy123",
            "handle": "lucy.bsky.social",
        }

        with patch(
            "zeo_core.integrations.social.bluesky.client.BlueskyClient",
            return_value=fake_session_client,
        ):
            with patch.dict(
                "os.environ",
                {
                    "BLUESKY_IDENTIFIER": "lucy.bsky.social",
                    "BLUESKY_APP_PASSWORD": "lucys-app-password",
                },
                clear=True,
            ):
                result = integration.initialize()

        assert result.success is True, result.error

        # The defect class this test exists to close: NOTHING was written
        # anywhere under the fresh CWD Lucy was standing in.
        assert list(tmp_path.iterdir()) == [], (
            "a live credential was written under the fresh CWD instead of "
            "the platformdirs location"
        )

        written = platformdirs_home / "bluesky" / "bluesky_credentials.json"
        assert written.exists()

        mode = stat.S_IMODE(written.stat().st_mode)
        assert mode == 0o600, f"expected 0600, got {oct(mode)}"

        on_disk = json.loads(written.read_text())
        assert on_disk["identifier"] == "lucy.bsky.social"
        assert on_disk["app_password"] == "lucys-app-password"  # noqa: S105
        assert on_disk["did"] == "did:plc:lucy123"

    def test_post_after_fresh_directory_init_uses_the_saved_session(
        self, tmp_path: Path, platformdirs_home: Path
    ) -> None:
        integration = BlueskyIntegration()

        fake_session_client = MagicMock()
        fake_session_client.create_session.return_value = {
            "accessJwt": "tok",
            "refreshJwt": "rtok",
            "did": "did:plc:lucy123",
            "handle": "lucy.bsky.social",
        }
        fake_session_client.create_post_record.return_value = {
            "uri": "at://did:plc:lucy123/app.bsky.feed.post/abc",
            "cid": "bafylucy",
        }

        with patch(
            "zeo_core.integrations.social.bluesky.client.BlueskyClient",
            return_value=fake_session_client,
        ):
            with patch.dict(
                "os.environ",
                {
                    "BLUESKY_IDENTIFIER": "lucy.bsky.social",
                    "BLUESKY_APP_PASSWORD": "pw",
                },
                clear=True,
            ):
                init_result = integration.initialize()
                assert init_result.success is True

                post_result = integration.post("hello from a fresh directory")

        assert post_result.success is True
        assert post_result.content is not None
        assert post_result.content["uri"] == (
            "at://did:plc:lucy123/app.bsky.feed.post/abc"
        )
