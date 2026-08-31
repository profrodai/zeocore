"""
The Lucy walkthrough (RULING-407/408, adopted per Sparring's steer): a fresh
directory, no repo, no config, authorize -- and confirm the token lands in
the platformdirs location with an explicit notice, rather than in cwd.

This is the acceptance test the charter names as the one that would have
caught the ORIGINAL defect. RULING-407's own reproduction was:

    cd /tmp/lucytest-master          # no repo, no config, nothing
    GoogleConfigProvider('drive').get_default_config()
    -> credentials_file: 'config/google_credentials.json'
    -> resolves to:      /private/tmp/lucytest-master/config/google_credentials.json

This test walks that exact same path -- GoogleConfigProvider('drive').
get_default_config() feeding a real GoogleAuthProvider -- rather than through
GoogleDriveService()'s zero-arg constructor. That constructor was
investigated as the more realistic-looking entry point and found to hit an
UNRELATED pre-existing defect first: GoogleConfigProvider.load_config() (not
touched by this migration) raises ZeoConfigurationError uncaught whenever no
YAML config file exists anywhere in the default search locations -- true
before this migration too (confirmed against origin/main@fb436db8's
identical code), so a truly fresh directory with zero config files makes
GoogleDriveService() raise regardless of the credential-location fix. That
is a real, separate defect (reported in this stream's own SOW as a
contradiction found, not fixed here -- out of this charter's three-item
scope) -- not something to paper over by adding a YAML file this walkthrough
is supposed to prove works WITHOUT one. Testing through
GoogleConfigProvider.get_default_config() + GoogleAuthProvider directly
stays faithful to "no repo, no config, nothing" while exercising the real,
unmocked migration and credential-save code paths this charter owns.

The only mocking here is at the true external boundary: the browser-based
OAuth flow itself (InstalledAppFlow/run_local_server), which cannot run
headless in a test -- and the client-secrets-file existence check, since a
real Google Cloud Console client secret is not something a test can have.
Every filesystem assertion below is against REAL paths on REAL disk (a
tmp_path standing in for "a fresh directory" and a second tmp_path standing
in for "the real machine's per-user config directory," via a
platformdirs.user_config_dir patch -- so this test never touches the actual
developer machine's real config directory).
"""

import json
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.google import credential_paths as cp
from zeo_core.integrations.google.auth import GoogleAuthProvider
from zeo_core.integrations.google.config import GoogleConfigProvider


def _real_shaped_credentials(token: str) -> MagicMock:
    """A MagicMock shaped like a real google.oauth2.credentials.Credentials
    object, specifically for serialize_credentials() (auth.py's REAL,
    unmocked save path -- the whole point of this walkthrough) rather than
    mocks.mock_credentials()'s own `expiry` field, which is a bare MagicMock
    with only `.timestamp` stubbed. serialize_credentials calls
    `credentials.expiry.isoformat()` directly, which mock_credentials never
    exercises because every OTHER test in this suite mocks
    _save_credentials_to_file itself rather than letting serialization run
    for real."""
    creds = MagicMock()
    creds.token = token
    creds.refresh_token = "rtok"  # noqa: S105 -- fake test value
    creds.client_id = "cid"
    creds.client_secret = "csecret"  # noqa: S105 -- fake test value
    creds.token_uri = "https://oauth2.googleapis.com/token"  # noqa: S105 -- real OAuth token endpoint URL, not a secret
    creds.scopes = ["https://www.googleapis.com/auth/drive"]
    creds.expiry = datetime(2099, 1, 1, tzinfo=UTC)
    return creds


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
    """Stands in for the real machine's per-user config directory, so this
    test's assertions about "the platformdirs location" are checkable
    without ever touching the real developer machine's actual home
    directory."""
    d = tmp_path.parent / f"{tmp_path.name}-platformdirs-home"
    d.mkdir(exist_ok=True)
    with patch.object(cp.platformdirs, "user_config_dir", return_value=str(d)):
        yield d


class TestFreshDirectoryLucyWalkthrough:
    def test_authorize_from_fresh_directory_lands_token_in_platformdirs_not_cwd(
        self,
        tmp_path: Path,
        platformdirs_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # "no repo, no config, nothing": tmp_path is genuinely empty. No
        # config/ directory, no zeo_config.yaml, no pre-existing credential
        # anywhere -- the exact directory state RULING-407's own repro used.
        assert list(tmp_path.iterdir()) == []

        default_config = GoogleConfigProvider("drive").get_default_config()

        # The defect RULING-407 reproduced, checked first: the resolved
        # default must NOT be the old CWD-relative string, and must be the
        # platformdirs location instead.
        assert default_config["credentials_file"] == str(
            platformdirs_home / "google_credentials.json"
        )
        assert default_config["client_secrets_file"] == str(
            platformdirs_home / "google_client_secret.json"
        )
        assert not (tmp_path / "config").exists(), (
            "no config/ directory should have been created under the fresh "
            "CWD merely by resolving defaults"
        )

        # The one thing a fresh machine genuinely cannot have is a real
        # Google Cloud Console client secret -- stand in for "Lucy already
        # downloaded hers and it's sitting at the (now migrated) default
        # location" so the walkthrough can proceed past GoogleAuthProvider's
        # own file-existence gate. Patched on the METHOD, not on the shared
        # `standalone` module: standalone.get_file_info is also the exact
        # call other, unrelated lookups in this same fresh directory use,
        # and patching the shared module object would make those falsely
        # report "exists" too (confirmed live while authoring this test).
        with patch.object(GoogleAuthProvider, "_verify_client_secrets_file"):
            auth_provider = GoogleAuthProvider(
                client_secrets_file=default_config["client_secrets_file"],
                credentials_file=default_config["credentials_file"],
                scopes=["https://www.googleapis.com/auth/drive"],
            )

        # Now authorize. The real OAuth dance (browser + local server) is
        # the one external boundary mocked here -- everything downstream
        # (save-to-disk) is the real, unmocked GoogleAuthProvider code path.
        new_creds = _real_shaped_credentials("lucys_live_token")
        with patch(
            "zeo_core.integrations.google.auth.InstalledAppFlow"
        ) as mock_flow_class:
            flow_instance = MagicMock()
            flow_instance.run_local_server.return_value = new_creds
            mock_flow_class.from_client_secrets_file.return_value = flow_instance

            auth_result = auth_provider.authenticate()

        assert auth_result.success is True

        # The defect this whole migration exists to close: NOTHING was
        # written anywhere under the fresh directory Lucy was standing in.
        assert list(tmp_path.iterdir()) == [], (
            "a live OAuth token was written under the fresh CWD -- this is "
            "the exact RULING-407 defect the migration exists to close"
        )

        # The token IS live, on real disk, at the platformdirs location.
        written = platformdirs_home / "google_credentials.json"
        assert written.exists()
        on_disk = json.loads(written.read_text())
        assert on_disk["token"] == "lucys_live_token"  # noqa: S105 -- fake test value

        # RULING-407: silence IS the defect, so a first-time write to a
        # NEW default is not itself required to print (nothing was
        # migrated -- there was no legacy file to move). This walkthrough's
        # own migration-notice proof is the companion test below, which
        # starts from a pre-existing legacy credential.
        _ = capsys.readouterr()

    def test_walkthrough_with_pre_existing_legacy_token_prints_explicit_notice(
        self,
        tmp_path: Path,
        platformdirs_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """The other half of the same walkthrough: Lucy is not fresh -- she
        already has a live token at the OLD `config/google_credentials.json`
        default from before this migration shipped. Resolving the default
        must migrate it EXPLICITLY (RULING-407: silence IS the defect)
        rather than silently start using the new location or silently leave
        the old token stranded and unused."""
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        (legacy_dir / "google_credentials.json").write_text(
            json.dumps({"token": "lucys_pre_migration_token"})
        )

        default_config = GoogleConfigProvider("drive").get_default_config()

        captured = capsys.readouterr().out
        assert "Migrated" in captured
        # The legacy side of the notice names the relative constant
        # (config/google_credentials.json) as passed to migrate_one_shot --
        # not re-resolved to an absolute path -- so the message matches
        # what a user actually sees printed by their own shell/cwd.
        assert "config/google_credentials.json" in captured
        assert str(platformdirs_home / "google_credentials.json") in captured

        assert default_config["credentials_file"] == str(
            platformdirs_home / "google_credentials.json"
        )
        migrated = platformdirs_home / "google_credentials.json"
        assert migrated.exists()
        assert json.loads(migrated.read_text()) == {
            "token": "lucys_pre_migration_token"
        }
        # The old copy is left in place (RULING-408's one-shot default),
        # not deleted.
        assert (legacy_dir / "google_credentials.json").exists()
