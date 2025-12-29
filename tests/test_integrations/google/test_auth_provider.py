# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/test_auth_provider.py
# role: tests
# neighbors: __init__.py, mocks.py, test_config_provider.py, test_serialization.py
# exports: TestGoogleAuthProvider
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""
Tests for Google authentication provider.

This module tests the GoogleAuthProvider class, including authentication flow,
token management, and credential handling.
"""

from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackIntegrationError
from quack_core.integrations.core.results import AuthResult
from quack_core.integrations.google.auth import GoogleAuthProvider

from .mocks import mock_credentials


class TestGoogleAuthProvider:
    """Tests for the GoogleAuthProvider class."""

    def test_init(self) -> None:
        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True

            provider = GoogleAuthProvider(client_secrets_file="/path/to/secrets.json")
            assert provider.name == "GoogleAuth"
            assert provider.scopes == []

    def test_verify_client_secrets_file(self) -> None:
        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            GoogleAuthProvider(client_secrets_file="/path/to/secrets.json")

        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = False
            with pytest.raises(QuackIntegrationError):
                GoogleAuthProvider(client_secrets_file="/nonexistent/secrets.json")

    def test_authenticate_new_flow(self) -> None:
        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        with (
            patch("google.oauth2.credentials.Credentials") as mock_creds_class,
            patch("quack_core.integrations.google.auth.standalone.read_json") as mock_read,
            patch(
                "quack_core.integrations.google.auth.InstalledAppFlow"
            ) as mock_flow_class,
        ):
            mock_read.return_value.success = True
            mock_read.return_value.data = {}

            expired_creds = mock_credentials(valid=False)
            mock_creds_class.from_authorized_user_info.return_value = expired_creds

            flow_instance = MagicMock()
            new_creds = mock_credentials(token="new_token", expiry_timestamp=1234567890)
            flow_instance.run_local_server.return_value = new_creds
            mock_flow_class.from_client_secrets_file.return_value = flow_instance

            with patch.object(provider, "_save_credentials_to_file") as mock_save:
                mock_save.return_value = True
                result = provider.authenticate()

                assert result.success
                assert result.token == "new_token"
                assert provider.authenticated
                assert provider.auth == new_creds

    def test_authenticate_with_expired_credentials(self) -> None:
        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        refreshed_creds = mock_credentials(
            token="refreshed_token",
            expired=True,
            refresh_token="refresh_token",
            expiry_timestamp=1234567890,
        )

        with (
            patch("quack_core.integrations.google.auth.standalone.read_json") as mock_read,
            patch("google.oauth2.credentials.Credentials") as mock_creds_class,
            patch("quack_core.integrations.google.auth.Request"),
            patch.object(provider, "_save_credentials_to_file") as mock_save,
            patch(
                "quack_core.integrations.google.auth.InstalledAppFlow"
            ) as mock_flow_class,
        ):
            mock_read.return_value.success = True
            mock_read.return_value.data = {}

            mock_creds_class.from_authorized_user_info.return_value = refreshed_creds

            mock_flow = MagicMock()
            mock_flow.run_local_server.return_value = refreshed_creds
            mock_flow_class.from_client_secrets_file.return_value = mock_flow

            mock_save.return_value = True

            result = provider.authenticate()

            assert result.success
            assert result.token == "refreshed_token"
            assert provider.auth == refreshed_creds

    def test_refresh_credentials(self) -> None:
        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        result = provider.refresh_credentials()
        assert not result.success

        provider.auth = mock_credentials(
            token="valid_token", expired=False, expiry_timestamp=1234567890
        )
        provider.authenticated = True

        result = provider.refresh_credentials()
        assert result.success
        assert result.message == "Credentials are valid, no refresh needed"
        assert result.token == "valid_token"

        provider.auth = mock_credentials(
            token="refreshed",
            expired=True,
            refresh_token="yes",
            expiry_timestamp=1234567890,
        )

        with patch.object(provider, "_save_credentials_to_file") as mock_save:
            mock_save.return_value = True
            result = provider.refresh_credentials()
            assert result.success
            assert result.message == "Successfully refreshed credentials"
            assert result.token == "refreshed"

        broken_creds = mock_credentials(expired=True, refresh_token="yes")
        broken_creds.refresh.side_effect = Exception("refresh error")
        provider.auth = broken_creds

        result = provider.refresh_credentials()
        assert not result.success
        assert "Failed to refresh" in result.error

    def test_get_credentials(self) -> None:
        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        with patch.object(provider, "authenticate") as mock_auth:
            mock_auth.return_value = AuthResult(success=False, error="fail")
            with pytest.raises(QuackIntegrationError):
                provider.get_credentials()

        valid_creds = mock_credentials(token="X")
        provider.auth = valid_creds
        provider.authenticated = True
        assert provider.get_credentials() == valid_creds

        provider.auth = None
        provider.authenticated = False

        with patch.object(provider, "authenticate") as mock_auth:
            new_creds = mock_credentials(token="new")
            provider.auth = new_creds
            provider.authenticated = True
            mock_auth.return_value = AuthResult(success=True, token="new")
            assert provider.get_credentials() == new_creds

    def test_save_credentials(self) -> None:
        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        provider.auth = None
        assert not provider.save_credentials()

        provider.auth = mock_credentials(token="x")
        with patch.object(provider, "_save_credentials_to_file") as mock_save:
            mock_save.return_value = True
            assert provider.save_credentials()

    def test_save_credentials_to_file(self) -> None:
        with patch("quack_core.integrations.google.auth.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        provider.credentials_file = None
        assert not provider._save_credentials_to_file(mock_credentials())

        provider.credentials_file = "/path/to/credentials.json"
        with (
            patch("quack_core.integrations.google.auth.standalone.split_path") as mock_split,
            patch("quack_core.integrations.google.auth.standalone.join_path") as mock_join,
            patch("quack_core.integrations.google.auth.standalone.create_directory") as mock_mkdir,
        ):
            split_result = MagicMock()
            split_result.success = True
            split_result.data = ["path", "to", "credentials.json"]
            mock_split.return_value = split_result

            join_result = MagicMock()
            join_result.success = True
            join_result.data = "/path/to"
            mock_join.return_value = join_result

            mock_mkdir.return_value.success = False
            assert not provider._save_credentials_to_file(mock_credentials())

        creds = mock_credentials(token="test_token", expiry_timestamp=1234567890)
        with (
            patch("quack_core.integrations.google.auth.standalone.split_path") as mock_split,
            patch("quack_core.integrations.google.auth.standalone.join_path") as mock_join,
            patch("quack_core.integrations.google.auth.standalone.create_directory") as mock_mkdir,
            patch("quack_core.integrations.google.auth.standalone.write_json") as mock_write_json,
        ):
            split_result = MagicMock()
            split_result.success = True
            split_result.data = ["path", "to", "credentials.json"]
            mock_split.return_value = split_result

            join_result = MagicMock()
            join_result.success = True
            join_result.data = "/path/to"
            mock_join.return_value = join_result

            mock_mkdir.return_value.success = True
            mock_write_json.return_value.success = True

            assert provider._save_credentials_to_file(creds)
            mock_write_json.assert_called_once()
