# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/github/test_config.py
# role: tests
# neighbors: __init__.py, conftest.py, test_api.py, test_auth.py, test_client.py, test_github_init.py (+5 more)
# exports: TestGitHubConfigProvider, config_provider
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""Tests for GitHub configuration provider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from quack_core.integrations.github.config import GitHubConfigProvider


@pytest.fixture
def config_provider():
    """Create a GitHubConfigProvider instance for testing."""
    return GitHubConfigProvider()


class TestGitHubConfigProvider:
    """Tests for GitHubConfigProvider."""

    def test_name_property(self, config_provider):
        """Test the name property."""
        assert config_provider.name == "GitHub"

    def test_get_default_config(self, config_provider):
        """Test getting default configuration."""
        default_config = config_provider.get_default_config()

        assert isinstance(default_config, dict)
        assert "token" in default_config
        assert "api_url" in default_config
        assert default_config["api_url"] == "https://api.github.com"
        assert "timeout_seconds" in default_config
        assert "max_retries" in default_config
        assert "retry_delay" in default_config
        assert "quackster" in default_config

        # Check quackster config
        teaching_config = default_config["quackster"]
        assert "assignment_branch_prefix" in teaching_config
        assert "default_base_branch" in teaching_config
        assert "pr_title_template" in teaching_config
        assert "pr_body_template" in teaching_config

    def test_validate_config_with_token(self, config_provider):
        """Test validating config with token."""
        config = {"token": "test_token", "api_url": "https://api.github.com"}
        assert config_provider.validate_config(config) is True

    def test_validate_config_with_env_var(self, config_provider):
        """Test validating config with environment variable."""
        config = {"api_url": "https://api.github.com"}

        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
            assert config_provider.validate_config(config) is True

    def test_validate_config_no_token(self, config_provider):
        """Test validating config with no token."""
        config = {"api_url": "https://api.github.com"}

        with patch.dict(os.environ, {}, clear=True):
            assert config_provider.validate_config(config) is False

    def test_validate_config_invalid_url(self, config_provider):
        """Test validating config with invalid URL."""
        # Test with invalid URL
        config = {"token": "test_token", "api_url": "invalid-url"}
        assert config_provider.validate_config(config) is False

    def test_extract_config_direct_key(self, config_provider):
        """Test extracting config from direct key."""
        test_configs = [
            # Test with 'github' key
            {"github": {"token": "test_token"}},
            # Test with 'GitHub' key
            {"GitHub": {"token": "test_token"}},
        ]

        for config_data in test_configs:
            result = config_provider._extract_config(config_data)
            assert result == config_data[list(config_data.keys())[0]]

    def test_extract_config_dotted_path(self, config_provider):
        """Test extracting config from dotted path."""
        # Test with 'integrations.github' path
        config_data = {"integrations": {"github": {"token": "test_token"}}}
        result = config_provider._extract_config(config_data)
        assert result == config_data["integrations"]["github"]

    def test_extract_config_integrations_section(self, config_provider):
        """Test extracting config from integrations section."""
        # Test with 'integrations' section
        config_data = {"integrations": {"github": {"token": "test_token"}}}
        result = config_provider._extract_config(config_data)
        assert result == config_data["integrations"]["github"]

    def test_extract_config_env_var(self, config_provider):
        """Test extracting config from environment variable."""
        # Test with environment variable
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
            result = config_provider._extract_config({})
            assert result["token"] == "env_token"
            # Should match default config with token added
            default_config = config_provider.get_default_config()
            default_config["token"] = "env_token"
            for key in default_config:
                if key != "token":  # We already checked token
                    assert result[key] == default_config[key]

    def test_extract_config_fallback(self, config_provider):
        """Test extract_config falling back to base implementation."""
        # Mock super()._extract_config
        with patch(
            "quack_core.integrations.core.BaseConfigProvider._extract_config"
        ) as mock_super:
            mock_super.return_value = {"token": "fallback_token"}

            # Empty config with no environment variable
            with patch.dict(os.environ, {}, clear=True):
                result = config_provider._extract_config({})

                # Should call parent implementation
                mock_super.assert_called_once_with({})
                assert result == {"token": "fallback_token"}

    def test_load_config_with_env_token(self, config_provider):
        """Test loading config and getting token from environment."""
        # Mock super().load_config
        with patch(
            "quack_core.integrations.core.BaseConfigProvider.load_config"
        ) as mock_super:
            mock_super.return_value = MagicMock(
                success=True, content={"token": "", "api_url": "https://api.github.com"}
            )

            # Set environment variable
            with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
                result = config_provider.load_config()

                assert result.success is True
                assert result.content["token"] == "env_token"

    def test_load_config_existing_token(self, config_provider):
        """Test loading config with existing token."""
        # Mock super().load_config
        with patch(
            "quack_core.integrations.core.BaseConfigProvider.load_config"
        ) as mock_super:
            mock_super.return_value = MagicMock(
                success=True,
                content={"token": "config_token", "api_url": "https://api.github.com"},
            )

            # Set environment variable
            with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
                result = config_provider.load_config()

                assert result.success is True
                # Should keep existing token, not override with env var
                assert result.content["token"] == "config_token"
