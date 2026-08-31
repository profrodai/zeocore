"""Tests for Bluesky credential-path resolution and the sandbox-escape
fallback helpers.

The fallback machinery (`_is_sandbox_escape`, `_scoped_service`,
`write_json_with_fallback`, etc.) is a structural port of
`google/credential_paths.py`'s already-proven pattern -- these tests focus
on the parts specific to this module (the default path computation, the
0600 mode threading through the fallback) rather than re-proving the
sandbox mechanism itself, which is core/fs's own contract.
"""

import json
import stat
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from zeo_core.integrations.social.bluesky import credential_paths as cp


@pytest.fixture(autouse=True)
def _clear_scoped_cache() -> Generator[None]:
    cp._scoped_service_cache.clear()
    yield
    cp._scoped_service_cache.clear()


class TestDefaultCredentialsPath:
    def test_default_path_is_absolute_under_platformdirs_bluesky_subdir(self) -> None:
        fake_home = "/fake/platformdirs/zeocore"
        with patch.object(cp.platformdirs, "user_config_dir", return_value=fake_home):
            path = cp.default_credentials_path()

        assert path == str(Path(fake_home) / "bluesky" / cp.CREDENTIALS_FILENAME)
        assert Path(path).is_absolute()

    def test_platformdirs_config_dir_uses_zeocore_appname(self) -> None:
        with patch.object(cp.platformdirs, "user_config_dir") as mock_dir:
            mock_dir.return_value = "/whatever"
            cp.platformdirs_config_dir()

        mock_dir.assert_called_once_with("zeocore", appauthor=False)


class TestWriteJsonWithFallbackMode0600:
    def test_write_outside_sandbox_falls_back_and_sets_mode(
        self, tmp_path: Path
    ) -> None:
        # A genuinely out-of-sandbox absolute path (a sibling of tmp_path,
        # standing in for the platformdirs location, which is always
        # outside the CWD-anchored sandbox from a normal working directory).
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-sandbox"
        outside_dir.mkdir(exist_ok=True)
        target = outside_dir / "bluesky_credentials.json"

        result = cp.write_json_with_fallback(
            str(target), {"identifier": "alice", "app_password": "pw"}, mode=0o600
        )

        assert result.ok is True
        assert target.exists()
        on_disk = json.loads(target.read_text())
        assert on_disk == {"identifier": "alice", "app_password": "pw"}

        mode = stat.S_IMODE(target.stat().st_mode)
        assert mode == 0o600

    def test_read_json_with_fallback_round_trips(self, tmp_path: Path) -> None:
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-sandbox-2"
        outside_dir.mkdir(exist_ok=True)
        target = outside_dir / "bluesky_credentials.json"
        target.write_text(json.dumps({"identifier": "bob"}))

        info = cp.get_file_info_with_fallback(str(target))
        assert info.ok is True
        assert info.exists is True

        result = cp.read_json_with_fallback(str(target))
        assert result.ok is True
        assert result.data == {"identifier": "bob"}

    def test_create_directory_with_fallback_creates_nested_dir(
        self, tmp_path: Path
    ) -> None:
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-sandbox-3"
        nested = outside_dir / "bluesky"

        result = cp.create_directory_with_fallback(str(nested), exist_ok=True)

        assert result.ok is True
        assert nested.is_dir()

    def test_scoped_service_is_cached_per_parent_dir(self, tmp_path: Path) -> None:
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-sandbox-4"
        outside_dir.mkdir(exist_ok=True)

        svc1 = cp._scoped_service(str(outside_dir))
        svc2 = cp._scoped_service(str(outside_dir))

        assert svc1 is svc2
