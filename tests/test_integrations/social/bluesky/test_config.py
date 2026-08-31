"""Tests for BlueskyConfigProvider."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from zeo_core.integrations.social.bluesky.config import (
    DEFAULT_SERVICE_URL,
    BlueskyConfigProvider,
)


class TestBlueskyConfigProvider:
    def test_name_property(self) -> None:
        assert BlueskyConfigProvider().name == "Bluesky"

    def test_get_default_config_reads_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "BLUESKY_IDENTIFIER": "alice.bsky.social",
                "BLUESKY_APP_PASSWORD": "app-pw-123",
                "BLUESKY_SERVICE_URL": "https://custom.pds.example",
            },
            clear=True,
        ):
            config = BlueskyConfigProvider().get_default_config()

        assert config["identifier"] == "alice.bsky.social"
        assert config["app_password"] == "app-pw-123"  # noqa: S105
        assert config["service_url"] == "https://custom.pds.example"
        assert "credentials_file" in config

    def test_get_default_config_no_env_defaults_empty_and_default_service(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = BlueskyConfigProvider().get_default_config()

        assert config["identifier"] == ""
        assert config["app_password"] == ""
        assert config["service_url"] == DEFAULT_SERVICE_URL

    def test_get_default_config_credentials_file_is_platformdirs_path(self) -> None:
        config = BlueskyConfigProvider().get_default_config()
        # Never CWD-relative: the whole point of RULING-407/408's fix,
        # avoided here by construction rather than migration.
        assert os.path.isabs(config["credentials_file"])
        assert "bluesky" in config["credentials_file"]

    def test_validate_config_rejects_empty_service_url(self) -> None:
        provider = BlueskyConfigProvider()
        assert provider.validate_config({"service_url": ""}) is False
        assert provider.validate_config({"service_url": "   "}) is False
        assert provider.validate_config({}) is False

    def test_validate_config_accepts_service_url_without_requiring_credentials(
        self,
    ) -> None:
        provider = BlueskyConfigProvider()
        # identifier/app_password are NOT required at config-validation time
        # -- they may arrive later, exactly like NotionConfigProvider.
        assert provider.validate_config({"service_url": "https://bsky.social"}) is True


class TestBlueskyConfigProviderLoadConfigFreshDirectoryFallback:
    """The defect this SOW's fresh-directory acceptance criterion actually
    needs fixed: `BaseConfigProvider.load_config()` raises
    `ZeoConfigurationError` uncaught when no YAML file exists anywhere in
    the default search locations -- true of any genuinely fresh directory.
    `BlueskyConfigProvider.load_config` must fall back to
    `get_default_config()` instead of letting that propagate, mirroring
    `NotionConfigProvider.load_config`'s own identical fallback."""

    def test_load_config_no_file_anywhere_falls_back_to_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert list(tmp_path.iterdir()) == []

        with patch.dict(os.environ, {}, clear=True):
            result = BlueskyConfigProvider().load_config()

        assert result.success is True
        assert result.content is not None
        assert result.content["service_url"] == DEFAULT_SERVICE_URL
        assert list(tmp_path.iterdir()) == [], (
            "load_config must not create any file/directory as a side "
            "effect of falling back to defaults"
        )

    def test_load_config_merges_defaults_under_partial_file_content(self) -> None:
        from zeo_core.integrations.core import BaseConfigProvider, ConfigResult

        provider = BlueskyConfigProvider()
        with patch.object(BaseConfigProvider, "load_config") as mock_super:
            mock_super.return_value = ConfigResult.success_result(
                content={"service_url": "https://custom.pds.example"},
                config_path="some/config.yaml",
            )
            result = provider.load_config("some/config.yaml")

        assert result.success is True
        assert result.content is not None
        assert result.content["service_url"] == "https://custom.pds.example"
        # Keys the file omitted still come from get_default_config()'s own
        # env-var resolution rather than vanishing.
        assert "identifier" in result.content
        assert "credentials_file" in result.content

    def test_load_config_super_returns_failure_falls_back_to_defaults(self) -> None:
        from zeo_core.integrations.core import BaseConfigProvider, ConfigResult

        provider = BlueskyConfigProvider()
        with patch.object(BaseConfigProvider, "load_config") as mock_super:
            mock_super.return_value = ConfigResult.error_result("validation failed")
            result = provider.load_config()

        assert result.success is True
        assert result.content is not None
        assert result.content["service_url"] == DEFAULT_SERVICE_URL
