"""Tests for Notion configuration provider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.notion.config import NotionConfig, NotionConfigProvider


@pytest.fixture
def config_provider() -> NotionConfigProvider:
    """Create a NotionConfigProvider instance for testing."""
    return NotionConfigProvider()


class TestNotionConfig:
    """Tests for the NotionConfig compatibility model."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = NotionConfig()
        assert config.api_key is None
        assert config.database_ids == {}

    def test_with_values(self) -> None:
        """Test construction with explicit values."""
        config = NotionConfig(api_key="secret", database_ids={"tasks": "db-1"})  # noqa: S106 -- test fixture, fake credential value
        assert config.api_key == "secret"  # noqa: S105 -- test fixture, fake credential value
        assert config.database_ids == {"tasks": "db-1"}


class TestNotionConfigProvider:
    """Tests for NotionConfigProvider."""

    def test_name_property(self, config_provider: NotionConfigProvider) -> None:
        """Test the name property."""
        assert config_provider.name == "Notion"

    def test_get_default_config(self, config_provider: NotionConfigProvider) -> None:
        """Test getting default configuration."""
        default_config = config_provider.get_default_config()

        assert isinstance(default_config, dict)
        assert "token" in default_config
        assert default_config["token"] == ""
        assert "timeout_ms" in default_config
        assert "max_retries" in default_config
        assert "database_ids" in default_config

    def test_validate_config_with_token(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test validating config with token."""
        config = {"token": "test_token"}
        assert config_provider.validate_config(config) is True

    def test_validate_config_with_env_var(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test validating config with environment variable."""
        config: dict[str, object] = {}

        with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
            assert config_provider.validate_config(config) is True

    def test_validate_config_no_token(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test validating config with no token."""
        config: dict[str, object] = {}

        with patch.dict(os.environ, {}, clear=True):
            assert config_provider.validate_config(config) is False

    def test_extract_config_direct_key(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test extracting config from direct key."""
        test_configs = [
            {"notion": {"token": "test_token"}},
            {"Notion": {"token": "test_token"}},
        ]

        for config_data in test_configs:
            result = config_provider._extract_config(config_data)
            assert result == config_data[next(iter(config_data.keys()))]

    def test_extract_config_dotted_path(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test extracting config from dotted path."""
        config_data = {"integrations": {"notion": {"token": "test_token"}}}
        result = config_provider._extract_config(config_data)
        assert result == config_data["integrations"]["notion"]

    def test_extract_config_integrations_section(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test extracting config from integrations section."""
        config_data = {"integrations": {"notion": {"token": "test_token"}}}
        result = config_provider._extract_config(config_data)
        assert result == config_data["integrations"]["notion"]

    def test_extract_config_env_var(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test extracting config from environment variable."""
        with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
            result = config_provider._extract_config({})
            assert result["token"] == "env_token"  # noqa: S105 -- test fixture
            default_config = config_provider.get_default_config()
            default_config["token"] = "env_token"  # noqa: S105 -- test fixture
            for key in default_config:
                if key != "token":
                    assert result[key] == default_config[key]

    def test_extract_config_fallback(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test extract_config falling back to base implementation."""
        with patch(
            "zeo_core.integrations.core.BaseConfigProvider._extract_config"
        ) as mock_super:
            mock_super.return_value = {"token": "fallback_token"}

            with patch.dict(os.environ, {}, clear=True):
                result = config_provider._extract_config({})

                mock_super.assert_called_once_with({})
                assert result == {"token": "fallback_token"}

    def test_load_config_with_env_token(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test loading config and getting token from environment."""
        with patch(
            "zeo_core.integrations.core.BaseConfigProvider.load_config"
        ) as mock_super:
            mock_super.return_value = MagicMock(success=True, content={"token": ""})

            with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
                result = config_provider.load_config()

                assert result.success is True
                assert result.content is not None
                assert result.content["token"] == "env_token"  # noqa: S105

    def test_load_config_existing_token(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test loading config with existing token."""
        with patch(
            "zeo_core.integrations.core.BaseConfigProvider.load_config"
        ) as mock_super:
            mock_super.return_value = MagicMock(
                success=True, content={"token": "config_token"}
            )

            with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
                result = config_provider.load_config()

                assert result.success is True
                assert result.content is not None
                assert result.content["token"] == "config_token"  # noqa: S105

    def test_load_config_no_file_uses_defaults(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Test loading config when the file load fails falls back to defaults."""
        with patch(
            "zeo_core.integrations.core.BaseConfigProvider.load_config"
        ) as mock_super:
            mock_super.return_value = MagicMock(
                success=False, content=None, error="not found"
            )

            with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
                result = config_provider.load_config("missing.yaml")

                assert result.success is True
                assert result.content is not None
                assert result.content["token"] == "env_token"  # noqa: S105

    def test_load_config_content_missing_token_key_uses_env(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """Loaded content with no "token" key at all (the elif branch) still
        picks up NOTION_TOKEN from the environment."""
        with patch(
            "zeo_core.integrations.core.BaseConfigProvider.load_config"
        ) as mock_super:
            mock_super.return_value = MagicMock(
                success=True, content={"database_ids": {"tasks": "db-1"}}
            )

            with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
                result = config_provider.load_config()

                assert result.success is True
                assert result.content is not None
                assert result.content["token"] == "env_token"  # noqa: S105

    def test_extract_config_none_config_data(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """config_data=None returns defaults, with an env token folded in."""
        with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
            result = config_provider._extract_config(None)  # type: ignore[arg-type]

            assert result["token"] == "env_token"  # noqa: S105

        with patch.dict(os.environ, {}, clear=True):
            result = config_provider._extract_config(None)  # type: ignore[arg-type]

            assert result["token"] == ""

    def test_extract_config_integrations_section_via_dotted_path(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """config_data["integrations"]["Notion"] (capital-N key) is found --
        NOTE: this is caught by the dotted-path candidate
        "integrations.Notion" in _find_notion_config_section's FIRST loop,
        not the separate integrations-section-scan loop below it (lines
        113-124): that second loop checks the identical two keys
        ("notion"/"Notion") the first loop's dotted candidates already
        cover, so it is structurally unreachable dead code -- confirmed
        identical in GitHubConfigProvider._find_github_config_section
        (github/config.py lines 107-127, same shape, same gap; that file's
        own test suite has an identical uncovered range). Ported
        byte-for-byte per CLAUDE.md s7 Chesterton's fence, not fixed here
        since fixing dead code in a faithfully-ported base class is outside
        this integration's own scope."""
        config_data = {"integrations": {"Notion": {"token": "cap_n_token"}}}
        result = config_provider._extract_config(config_data)
        assert result == {"token": "cap_n_token"}  # noqa: S106 -- test fixture

    def test_extract_config_found_no_token_uses_env(
        self, config_provider: NotionConfigProvider
    ) -> None:
        """A found config section with no/empty token still picks up
        NOTION_TOKEN from the environment before being returned."""
        config_data: dict[str, object] = {"notion": {"database_ids": {}}}

        with patch.dict(os.environ, {"NOTION_TOKEN": "env_token"}):
            result = config_provider._extract_config(config_data)

            assert result["token"] == "env_token"  # noqa: S105
