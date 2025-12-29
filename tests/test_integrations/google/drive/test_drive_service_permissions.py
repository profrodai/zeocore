# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive_service_permissions.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive.py, test_drive_models.py, test_drive_service_delete.py, test_drive_service_download.py (+6 more)
# exports: TestGoogleDriveServicePermissions
# git_branch: refactor/toolkitWorkflow
# git_commit: 0f9247b
# === QV-LLM:END ===

"""
Tests for Google Drive service permissions _operations.
"""

from unittest.mock import MagicMock, patch

from quack_core.lib.errors import QuackApiError
from quack_core.integrations.google.drive.service import GoogleDriveService


class TestGoogleDriveServicePermissions:
    """Tests for the GoogleDriveService permissions _operations."""

    @patch(
        "quack_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch.object(GoogleDriveService, "_initialize_config")
    def test_set_file_permissions(self, mock_init_config, mock_verify) -> None:
        """Test setting file permissions."""
        # Bypass verification
        mock_verify.return_value = None

        # Mock configuration
        mock_init_config.return_value = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
            "default_share_access": "commenter",
        }

        # Create service with mocked dependencies
        service = GoogleDriveService()
        service._initialized = True
        service.drive_service = MagicMock()

        # Mock API response
        mock_create = MagicMock()
        service.drive_service.permissions().create.return_value = mock_create
        mock_create.execute.return_value = {"id": "perm1"}

        # Test successful permission setting with custom parameters
        result = service.set_file_permissions("file123", "writer", "user")

        assert result.success is True
        assert result.content is True
        service.drive_service.permissions().create.assert_called_once_with(
            fileId="file123",
            body={"type": "user", "role": "writer", "allowFileDiscovery": True},
            fields="id",
        )

        # Test with default parameters
        service.drive_service.permissions().create.reset_mock()

        result = service.set_file_permissions("file123")

        assert result.success is True
        service.drive_service.permissions().create.assert_called_once_with(
            fileId="file123",
            body={"type": "anyone", "role": "commenter", "allowFileDiscovery": True},
            fields="id",
        )

        # Test API error
        service.drive_service.permissions().create.side_effect = QuackApiError(
            "API error", service="drive"
        )
        result = service.set_file_permissions("file123")
        assert result.success is False
        assert "API error" in result.error

    @patch(
        "quack_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch.object(GoogleDriveService, "_initialize_config")
    def test_get_sharing_link(self, mock_init_config, mock_verify) -> None:
        """Test getting a sharing link."""
        # Bypass verification
        mock_verify.return_value = None

        # Mock configuration
        mock_init_config.return_value = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
        }

        # Create service with mocked dependencies
        service = GoogleDriveService()
        service._initialized = True
        service.drive_service = MagicMock()

        # Mock API response
        mock_get = MagicMock()
        service.drive_service.files().get.return_value = mock_get
        mock_get.execute.return_value = {
            "webViewLink": "https://drive.google.com/file/d/file123/view",
        }

        # Test successful link retrieval
        result = service.get_sharing_link("file123")

        assert result.success is True
        assert result.content == "https://drive.google.com/file/d/file123/view"
        service.drive_service.files().get.assert_called_once_with(
            fileId="file123", fields="webViewLink, webContentLink"
        )

        # Test with only content link
        service.drive_service.files().get.reset_mock()
        mock_get.execute.return_value = {
            "webContentLink": "https://drive.google.com/uc?id=file123",
        }

        result = service.get_sharing_link("file123")

        assert result.success is True
        assert result.content == "https://drive.google.com/uc?id=file123"

        # Test with no links (should generate default)
        service.drive_service.files().get.reset_mock()
        mock_get.execute.return_value = {}

        result = service.get_sharing_link("file123")

        assert result.success is True
        assert result.content == "https://drive.google.com/file/d/file123/view"

        # Test API error
        service.drive_service.files().get.side_effect = QuackApiError(
            "API error", service="drive"
        )
        result = service.get_sharing_link("file123")
        assert result.success is False
        assert "API error" in result.error
