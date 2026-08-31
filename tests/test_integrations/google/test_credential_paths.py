"""
Tests for zeo_core.integrations.google.credential_paths -- the RULING-407/408
credential-location migration: platformdirs destination, explicit one-shot
migration, refuse-and-instruct on ambiguity.

Follows tests/test_fs/test_standalone.py's own established isolation pattern
(monkeypatch.chdir(tmp_path) + get_service.cache_clear()) since this module's
whole job is real filesystem behavior across two real directories (the
CWD-anchored legacy location and an out-of-sandbox "new" location) -- mocking
`standalone` here would test the mock, not the migration. The "new" location
is additionally redirected via platformdirs.user_config_dir so no test ever
touches the real machine's actual per-user config directory.
"""

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from zeo_core.integrations.google import credential_paths as cp


@pytest.fixture(autouse=True)
def _isolated_singleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None]:
    """Point the CWD-anchored fs singleton at a fresh tmp_path, and clear
    credential_paths' own scoped-service cache so no test leaks another
    test's directory-scoped FileSystemService instance."""
    from zeo_core.core.fs.service import get_service

    monkeypatch.chdir(tmp_path)
    get_service.cache_clear()
    cp._scoped_service_cache.clear()
    yield
    get_service.cache_clear()
    cp._scoped_service_cache.clear()


@pytest.fixture
def new_location_dir(tmp_path: Path) -> Generator[Path]:
    """A directory OUTSIDE the CWD sandbox (tmp_path's own "cwd" fixture is
    the sandbox root; this is a sibling), standing in for the real
    platformdirs per-user config directory. platformdirs.user_config_dir is
    patched to return it so default_credentials_path()/
    default_client_secret_path() resolve here instead of the real machine's
    home directory."""
    d = tmp_path.parent / f"{tmp_path.name}-platformdirs"
    d.mkdir(exist_ok=True)
    with patch.object(cp.platformdirs, "user_config_dir", return_value=str(d)):
        yield d


class TestPlatformdirsPaths:
    def test_platformdirs_config_dir_uses_appauthor_false(self) -> None:
        with patch.object(
            cp.platformdirs, "user_config_dir", return_value="/x/zeocore"
        ) as mock_udc:
            result = cp.platformdirs_config_dir()
            assert result == "/x/zeocore"
            mock_udc.assert_called_once_with("zeocore", appauthor=False)

    def test_default_paths_are_under_platformdirs_dir(
        self, new_location_dir: Path
    ) -> None:
        assert cp.default_credentials_path() == str(
            new_location_dir / "google_credentials.json"
        )
        assert cp.default_client_secret_path() == str(
            new_location_dir / "google_client_secret.json"
        )


class TestSandboxFallbackHelpers:
    """The six *_with_fallback / parent_directory_with_fallback helpers:
    each must behave IDENTICALLY to the bare standalone.* call for a path
    the CWD sandbox accepts (the common case), and transparently fall back
    to a directory-scoped service only when the path is a genuine
    out-of-sandbox escape."""

    def test_get_file_info_inside_cwd_sandbox_unchanged(self, tmp_path: Path) -> None:
        target = tmp_path / "inside.json"
        target.write_text("{}")
        result = cp.get_file_info_with_fallback(str(target))
        assert result.success is True
        assert result.exists is True

    def test_get_file_info_outside_cwd_sandbox_falls_back(
        self, new_location_dir: Path
    ) -> None:
        target = new_location_dir / "outside.json"
        target.write_text("{}")
        result = cp.get_file_info_with_fallback(str(target))
        assert result.success is True
        assert result.exists is True

    def test_get_file_info_outside_sandbox_nonexistent_file(
        self, new_location_dir: Path
    ) -> None:
        target = new_location_dir / "nope.json"
        result = cp.get_file_info_with_fallback(str(target))
        assert result.success is True
        assert result.exists is False

    def test_read_json_outside_sandbox_falls_back(self, new_location_dir: Path) -> None:
        target = new_location_dir / "creds.json"
        target.write_text(json.dumps({"token": "abc"}))
        result = cp.read_json_with_fallback(str(target))
        assert result.success is True
        assert result.data == {"token": "abc"}

    def test_write_json_outside_sandbox_falls_back(
        self, new_location_dir: Path
    ) -> None:
        target = new_location_dir / "creds.json"
        result = cp.write_json_with_fallback(str(target), {"token": "xyz"}, mode=0o600)
        assert result.success is True
        assert target.exists()
        assert json.loads(target.read_text()) == {"token": "xyz"}

    def test_create_directory_outside_sandbox_falls_back(
        self, new_location_dir: Path
    ) -> None:
        target_dir = new_location_dir / "nested"
        result = cp.create_directory_with_fallback(str(target_dir), exist_ok=True)
        assert result.success is True
        assert target_dir.is_dir()

    def test_parent_directory_inside_sandbox_uses_split_path(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "sub" / "credentials.json"
        result = cp.parent_directory_with_fallback(str(target))
        assert result is not None
        assert Path(result) == tmp_path / "sub"

    def test_parent_directory_outside_sandbox_falls_back_to_pathlib(
        self, new_location_dir: Path
    ) -> None:
        target = new_location_dir / "credentials.json"
        result = cp.parent_directory_with_fallback(str(target))
        assert result == str(new_location_dir)

    def test_parent_directory_genuine_split_path_failure_returns_none(
        self, tmp_path: Path
    ) -> None:
        """A split_path failure that is NOT a sandbox escape (some other
        real error) must still surface as None -- only the specific
        path_outside_base_dir case gets the pathlib fallback."""
        with patch(
            "zeo_core.integrations.google.credential_paths.standalone.split_path"
        ) as mock_split:
            mock_split.return_value.success = False
            mock_split.return_value.data = None
            mock_split.return_value.error_info = None

            result = cp.parent_directory_with_fallback(str(tmp_path / "x.json"))

            assert result is None

    def test_scoped_service_is_cached_per_parent_dir(
        self, new_location_dir: Path
    ) -> None:
        svc1 = cp._scoped_service(str(new_location_dir))
        svc2 = cp._scoped_service(str(new_location_dir))
        assert svc1 is svc2


class TestMigrateOneShot:
    def test_nothing_to_migrate_when_legacy_absent(
        self, tmp_path: Path, new_location_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        legacy = str(tmp_path / "config" / "google_credentials.json")
        new = str(new_location_dir / "google_credentials.json")

        result = cp.migrate_one_shot(legacy, new, label="test cred")

        assert result == new
        assert not Path(new).exists()
        assert capsys.readouterr().out == ""

    def test_migrates_legacy_to_new_with_explicit_notice(
        self, tmp_path: Path, new_location_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_credentials.json"
        legacy.write_text(json.dumps({"token": "legacy_tok"}))
        new = str(new_location_dir / "google_credentials.json")

        result = cp.migrate_one_shot(str(legacy), new, label="Google OAuth credentials")

        assert result == new
        assert json.loads(Path(new).read_text()) == {"token": "legacy_tok"}
        # Old file is NOT deleted -- RULING-408's one-shot default is "move
        # by writing the new copy," not "delete the only copy on a
        # best-effort migration."
        assert legacy.exists()
        # RULING-407: silence IS the defect. The migration must print an
        # explicit notice, never move a live credential quietly.
        captured = capsys.readouterr().out
        assert "Migrated" in captured
        assert "Google OAuth credentials" in captured
        assert str(legacy) in captured
        assert new in captured

    def test_migration_notice_can_be_suppressed(
        self, tmp_path: Path, new_location_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_credentials.json"
        legacy.write_text(json.dumps({"token": "legacy_tok"}))
        new = str(new_location_dir / "google_credentials.json")

        cp.migrate_one_shot(str(legacy), new, label="test cred", notice=False)

        assert capsys.readouterr().out == ""

    def test_already_migrated_identical_contents_is_a_noop(
        self, tmp_path: Path, new_location_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_credentials.json"
        legacy.write_text(json.dumps({"token": "same"}))
        new = new_location_dir / "google_credentials.json"
        new.write_text(json.dumps({"token": "same"}))

        result = cp.migrate_one_shot(str(legacy), str(new), label="test cred")

        assert result == str(new)
        # No notice printed -- nothing was actually migrated this call.
        assert capsys.readouterr().out == ""

    def test_ambiguous_differing_contents_refuses_and_instructs(
        self, tmp_path: Path, new_location_dir: Path
    ) -> None:
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_credentials.json"
        legacy.write_text(json.dumps({"token": "legacy_tok"}))
        new = new_location_dir / "google_credentials.json"
        new.write_text(json.dumps({"token": "different_new_tok"}))

        with pytest.raises(cp.CredentialMigrationAmbiguousError) as exc_info:
            cp.migrate_one_shot(str(legacy), str(new), label="test cred")

        # Never guesses, never merges, never picks the newer file -- RULING-
        # 408's exact wording. The exception carries both paths so the
        # caller (a human, per "refuse-and-instruct") can resolve it by hand.
        assert exc_info.value.legacy_path == str(legacy)
        assert exc_info.value.new_path == str(new)
        assert str(legacy) in str(exc_info.value)
        assert str(new) in str(exc_info.value)

    def test_legacy_exists_but_unreadable_treated_as_absent(
        self, tmp_path: Path, new_location_dir: Path
    ) -> None:
        """_read_json_if_present's read.success==False branch: a legacy file
        that exists but fails to parse (or fails to read) is treated the
        same as "nothing to migrate" -- never raises, never half-migrates a
        corrupt file."""
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_credentials.json"
        legacy.write_text("not valid json{{{")
        new = str(new_location_dir / "google_credentials.json")

        result = cp.migrate_one_shot(str(legacy), new, label="test cred")

        assert result == new
        assert not Path(new).exists()

    def test_mkdir_failure_returns_legacy_path_and_does_not_write(
        self, tmp_path: Path, new_location_dir: Path
    ) -> None:
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_credentials.json"
        legacy.write_text(json.dumps({"token": "legacy_tok"}))
        new = str(new_location_dir / "sub" / "google_credentials.json")

        with patch(
            "zeo_core.integrations.google.credential_paths.create_directory_with_fallback"
        ) as mock_mkdir:
            mock_mkdir.return_value.success = False
            mock_mkdir.return_value.error = "disk full"

            result = cp.migrate_one_shot(str(legacy), new, label="test cred")

            assert result == str(legacy)
            assert not Path(new).exists()

    def test_write_failure_returns_legacy_path(
        self, tmp_path: Path, new_location_dir: Path
    ) -> None:
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_credentials.json"
        legacy.write_text(json.dumps({"token": "legacy_tok"}))
        new = str(new_location_dir / "google_credentials.json")

        with patch(
            "zeo_core.integrations.google.credential_paths.write_json_with_fallback"
        ) as mock_write:
            mock_write.return_value.success = False
            mock_write.return_value.error = "disk full"

            result = cp.migrate_one_shot(str(legacy), new, label="test cred")

            assert result == str(legacy)
            assert not Path(new).exists()


class TestResolveEntryPoints:
    def test_resolve_credentials_path_explicit_bypasses_migration(
        self, tmp_path: Path
    ) -> None:
        explicit = str(tmp_path / "custom" / "creds.json")
        # No legacy/new files exist anywhere -- an explicit path must never
        # trigger migration logic at all (only the DEFAULT is migrated).
        assert cp.resolve_credentials_path(explicit) == explicit

    def test_resolve_client_secret_path_explicit_bypasses_migration(
        self, tmp_path: Path
    ) -> None:
        explicit = str(tmp_path / "custom" / "secret.json")
        assert cp.resolve_client_secret_path(explicit) == explicit

    def test_resolve_credentials_path_default_runs_migration(
        self, tmp_path: Path, new_location_dir: Path
    ) -> None:
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_credentials.json"
        legacy.write_text(json.dumps({"token": "legacy_tok"}))

        result = cp.resolve_credentials_path(None)

        assert result == str(new_location_dir / "google_credentials.json")
        assert json.loads(
            (new_location_dir / "google_credentials.json").read_text()
        ) == {"token": "legacy_tok"}

    def test_resolve_client_secret_path_default_runs_migration(
        self, tmp_path: Path, new_location_dir: Path
    ) -> None:
        legacy_dir = tmp_path / "config"
        legacy_dir.mkdir()
        legacy = legacy_dir / "google_client_secret.json"
        legacy.write_text(json.dumps({"installed": {"client_id": "x"}}))

        result = cp.resolve_client_secret_path(None)

        assert result == str(new_location_dir / "google_client_secret.json")
        assert json.loads(
            (new_location_dir / "google_client_secret.json").read_text()
        ) == {"installed": {"client_id": "x"}}

    def test_resolve_credentials_path_default_no_legacy_no_migration(
        self, tmp_path: Path, new_location_dir: Path
    ) -> None:
        result = cp.resolve_credentials_path(None)
        assert result == str(new_location_dir / "google_credentials.json")
        assert not (new_location_dir / "google_credentials.json").exists()
