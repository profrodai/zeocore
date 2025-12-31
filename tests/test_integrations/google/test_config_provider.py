# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/test_config_provider.py
# role: tests
# neighbors: __init__.py, mocks.py, test_auth_provider.py, test_serialization.py
# exports: TestGoogleConfigProvider
# git_branch: refactor/toolkitWorkflow
# git_commit: 9e6703a
# === QV-LLM:END ===

"""
Tests for Google configuration provider.

This module tests the GoogleConfigProvider class, including configuration loading,
validation, and format handling.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError
from quack_core.integrations.google.config import (
    GoogleConfigProvider,
    GoogleDriveConfig,
    GoogleMailConfig,
)


class TestGoogleConfigProvider:
    """Tests for the GoogleConfigProvider class."""

    def test_init(self) -> None:
        """Test initializing the config provider."""
        # Test with default parameters
        provider = GoogleConfigProvider()
        assert provider.name == "GoogleDrive"
        assert provider.service == "drive"

        # Test with mail service
        provider = GoogleConfigProvider("mail")
        assert provider.name == "GoogleMail"
        assert provider.service == "mail"

        # Test with custom service
        provider = GoogleConfigProvider("calendar")
        assert provider.name == "GoogleCalendar"
        assert provider.service == "calendar"

    def test_extract_config(self) -> None:
        """Test extracting Google service configuration."""
        provider = GoogleConfigProvider("drive")

        # Test with google_drive section
        config_data = {
            "google_drive": {
                "client_secrets_file": "/path/to/secrets.json",
                "credentials_file": "/path/to/credentials.json",
                "shared_folder_id": "folder123",
            }
        }

        config = provider._extract_config(config_data)
        assert config["client_secrets_file"] == "/path/to/secrets.json"
        assert config["credentials_file"] == "/path/to/credentials.json"
        assert config["shared_folder_id"] == "folder123"

        # Test with google section and drive subsection
        config_data = {
            "google": {
                "client_secrets_file": "/path/to/secrets.json",
                "credentials_file": "/path/to/credentials.json",
                "drive": {
                    "shared_folder_id": "folder123",
                    "team_drive_id": "team456",
                },
            }
        }

        config = provider._extract_config(config_data)
        assert config["client_secrets_file"] == "/path/to/secrets.json"
        assert config["credentials_file"] == "/path/to/credentials.json"
        assert config["shared_folder_id"] == "folder123"
        assert config["team_drive_id"] == "team456"

        # Test with google section but no drive subsection
        config_data = {
            "google": {
                "client_secrets_file": "/path/to/secrets.json",
                "credentials_file": "/path/to/credentials.json",
            }
        }

        config = provider._extract_config(config_data)
        assert config["client_secrets_file"] == "/path/to/secrets.json"
        assert config["credentials_file"] == "/path/to/credentials.json"

        # Test with mailservice
        provider = GoogleConfigProvider("mail")

        config_data = {
            "google": {
                "client_secrets_file": "/path/to/secrets.json",
                "credentials_file": "/path/to/credentials.json",
                "mail": {
                    "gmail_labels": ["INBOX", "IMPORTANT"],
                    "gmail_days_back": 14,
                },
            }
        }

        config = provider._extract_config(config_data)
        assert config["client_secrets_file"] == "/path/to/secrets.json"
        assert config["credentials_file"] == "/path/to/credentials.json"
        assert config["gmail_labels"] == ["INBOX", "IMPORTANT"]
        assert config["gmail_days_back"] == 14

        # Test with no matching section
        config_data = {
            "other_section": {
                "some_key": "some_value",
            }
        }

        config = provider._extract_config(config_data)
        assert config == {}

    def test_validate_config(self) -> None:
        """Test validating Google service configuration."""
        # Test drive config validation
        provider = GoogleConfigProvider("drive")

        # Valid config
        valid_config = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
            "shared_folder_id": "folder123",
        }

        assert provider.validate_config(valid_config) is True

        # Invalid config - missing required fields
        invalid_config = {
            "client_secrets_file": "/path/to/secrets.json",
            # missing credentials_file
        }

        assert provider.validate_config(invalid_config) is False

        # Test mail config validation
        provider = GoogleConfigProvider("mail")

        # Valid config
        valid_config = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
            "gmail_labels": ["INBOX"],
        }

        assert provider.validate_config(valid_config) is True

        # Test validation error
        with patch(
            "quack_core.integrations.google.config.GoogleDriveConfig"
        ) as mock_config:
            from pydantic import ValidationError

            # Simple approach - create an actual validation error to use as a mock
            try:
                # Create a validation error by triggering one
                from quack_core.integrations.google.config import GoogleBaseConfig

                GoogleBaseConfig(client_secrets_file="", credentials_file="test")
            except ValidationError as e:
                # Use the actual error as the side effect
                mock_config.side_effect = e

            provider = GoogleConfigProvider("drive")
            assert provider.validate_config(valid_config) is False

        # Test other error
        with patch(
            "quack_core.integrations.google.config.GoogleDriveConfig"
        ) as mock_config:
            mock_config.side_effect = Exception("Unexpected error")

            provider = GoogleConfigProvider("drive")
            assert provider.validate_config(valid_config) is False

    def test_get_default_config(self) -> None:
        """Test getting default configuration."""
        # Test drive defaults
        provider = GoogleConfigProvider("drive")
        defaults = provider.get_default_config()

        assert defaults["client_secrets_file"] == "config/google_client_secret.json"
        assert defaults["credentials_file"] == "config/google_credentials.json"
        assert defaults["shared_folder_id"] is None
        assert defaults["team_drive_id"] is None
        assert defaults["default_share_access"] == "reader"
        assert defaults["public_sharing"] is True

        # Test mail defaults
        provider = GoogleConfigProvider("mail")
        defaults = provider.get_default_config()

        assert defaults["client_secrets_file"] == "config/google_client_secret.json"
        assert defaults["credentials_file"] == "config/google_credentials.json"
        assert defaults["gmail_labels"] == []
        assert defaults["gmail_days_back"] == 7
        assert defaults["gmail_user_id"] == "me"

        # Test other service defaults
        provider = GoogleConfigProvider("other")
        defaults = provider.get_default_config()

        assert defaults["client_secrets_file"] == "config/google_client_secret.json"
        assert defaults["credentials_file"] == "config/google_credentials.json"
        assert len(defaults) == 2  # Only contains the base config

    def test_resolve_config_paths(self) -> None:
        """Test resolving paths in configuration."""
        provider = GoogleConfigProvider()

        # Test with relative paths
        config = {
            "client_secrets_file": "config/secrets.json",
            "credentials_file": "config/credentials.json",
            "shared_folder_id": "folder123",
        }

        with patch("quack_core.lib.paths.service.PathService.resolve_project_path") as mock_resolve:
            mock_resolve.side_effect = [
                "/project/config/secrets.json",
                "/project/config/credentials.json",
            ]

            resolved = provider.resolve_config_paths(config)

            assert resolved["client_secrets_file"] == "/project/config/secrets.json"
            assert resolved["credentials_file"] == "/project/config/credentials.json"
            assert resolved["shared_folder_id"] == "folder123"
            assert mock_resolve.call_count == 2

        # Test with absolute paths
        config = {
            "client_secrets_file": "/absolute/path/secrets.json",
            "credentials_file": "/absolute/path/credentials.json",
        }

        with patch("quack_core.lib.paths.service.PathService.resolve_project_path") as mock_resolve:
            mock_resolve.side_effect = [
                "/absolute/path/secrets.json",
                "/absolute/path/credentials.json",
            ]

            resolved = provider.resolve_config_paths(config)

            assert resolved["client_secrets_file"] == "/absolute/path/secrets.json"
            assert resolved["credentials_file"] == "/absolute/path/credentials.json"

        # Test with resolver error
        config = {
            "client_secrets_file": "config/secrets.json",
            "credentials_file": "config/credentials.json",
        }

        with patch("quack_core.lib.paths.service.PathService.resolve_project_path") as mock_resolve:
            mock_resolve.side_effect = Exception("Resolver error")

            resolved = provider.resolve_config_paths(config)

            assert resolved["client_secrets_file"] == "config/secrets.json"
            assert resolved["credentials_file"] == "config/credentials.json"

    def test_google_base_config(self) -> None:
        """Test GoogleBaseConfig validation."""
        # Valid config
        config = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
        }

        # Test should pass with valid values
        from quack_core.integrations.google.config import GoogleBaseConfig

        model = GoogleBaseConfig(**config)
        assert model.client_secrets_file == "/path/to/secrets.json"
        assert model.credentials_file == "/path/to/credentials.json"

        # Test with empty client_secrets_file
        with pytest.raises(ValidationError):
            GoogleBaseConfig(
                client_secrets_file="",
                credentials_file="/path/to/credentials.json",
            )

        # Test with empty credentials_file
        with pytest.raises(ValidationError):
            GoogleBaseConfig(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="",
            )

    def test_google_drive_config(self) -> None:
        """Test GoogleDriveConfig validation."""
        # Valid minimal config
        config = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
        }

        model = GoogleDriveConfig(**config)
        assert model.client_secrets_file == "/path/to/secrets.json"
        assert model.credentials_file == "/path/to/credentials.json"
        assert model.shared_folder_id is None
        assert model.team_drive_id is None
        assert model.default_share_access == "reader"
        assert model.public_sharing is True

        # Valid full config
        config = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
            "shared_folder_id": "folder123",
            "team_drive_id": "team456",
            "default_share_access": "writer",
            "public_sharing": False,
        }

        model = GoogleDriveConfig(**config)
        assert model.shared_folder_id == "folder123"
        assert model.team_drive_id == "team456"
        assert model.default_share_access == "writer"
        assert model.public_sharing is False

        # Invalid config - missing required fields
        with pytest.raises(ValidationError):
            GoogleDriveConfig(
                # missing client_secrets_file and credentials_file
                shared_folder_id="folder123",
            )

    def test_google_mail_config(self) -> None:
        """Test GoogleMailConfig validation."""
        # Valid minimal config
        config = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
        }

        model = GoogleMailConfig(**config)
        assert model.client_secrets_file == "/path/to/secrets.json"
        assert model.credentials_file == "/path/to/credentials.json"
        assert model.gmail_labels == []
        assert model.gmail_days_back == 7
        assert model.gmail_user_id == "me"

        # Valid full config
        config = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
            "gmail_labels": ["INBOX", "IMPORTANT"],
            "gmail_days_back": 14,
            "gmail_user_id": "user@example.com",
        }

        model = GoogleMailConfig(**config)
        assert model.gmail_labels == ["INBOX", "IMPORTANT"]
        assert model.gmail_days_back == 14
        assert model.gmail_user_id == "user@example.com"

        # Invalid config - missing required fields
        with pytest.raises(ValidationError):
            GoogleMailConfig(
                # missing client_secrets_file and credentials_file
                gmail_labels=["INBOX"],
            )
