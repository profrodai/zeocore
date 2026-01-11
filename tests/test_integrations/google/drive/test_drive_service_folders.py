# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive_service_folders.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive.py, test_drive_models.py, test_drive_service_delete.py, test_drive_service_download.py (+6 more)
# exports: TestGoogleDriveServiceFolders
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Tests for Google Drive service folder _ops.
"""

from unittest.mock import MagicMock, patch

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.service import GoogleDriveService
from quack_core.core.errors import QuackApiError


class TestGoogleDriveServiceFolders:
    """Tests for the GoogleDriveService folder _ops."""

    @patch(
        "quack_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch.object(GoogleDriveService, "_initialize_config")
    def test_create_folder(self, mock_init_config, mock_verify) -> None:
        """Test creating a folder."""
        # Bypass verification
        mock_verify.return_value = None

        # Set up mock config
        mock_init_config.return_value = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
            "shared_folder_id": "shared_folder",
        }

        # Create service with mocked dependencies
        service = GoogleDriveService(shared_folder_id="shared_folder")
        service._initialized = True
        service.drive_service = MagicMock()

        # Mock API response
        mock_create = MagicMock()
        service.drive_service.files().create.return_value = mock_create
        mock_create.execute.return_value = {
            "id": "new_folder",
            "webViewLink": "https://drive.google.com/drive/folders/new_folder",
        }

        # Test successful folder creation
        with patch.object(service, "set_file_permissions") as mock_permissions:
            mock_permissions.return_value = IntegrationResult(success=True)

            result = service.create_folder("New Folder", "parent_folder")

            assert result.success is True
            assert result.content == "new_folder"
            service.drive_service.files().create.assert_called_once_with(
                body={
                    "name": "New Folder",
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": ["parent_folder"],
                },
                fields="id, webViewLink",
            )
            mock_permissions.assert_called_once_with("new_folder")

        # Test with default parent folder
        service.drive_service.files().create.reset_mock()
        result = service.create_folder("New Folder")
        assert result.success is True
        service.drive_service.files().create.assert_called_once_with(
            body={
                "name": "New Folder",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": ["shared_folder"],
            },
            fields="id, webViewLink",
        )

        # Test API error
        service.drive_service.files().create.side_effect = QuackApiError(
            "API error", service="drive"
        )
        result = service.create_folder("Error Folder")
        assert result.success is False
        assert "API error" in result.error

    @patch(
        "quack_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch.object(GoogleDriveService, "_initialize_config")
    def test_delete_file(self, mock_init_config, mock_verify) -> None:
        """Test deleting a file or folder."""
        # Bypass verification
        mock_verify.return_value = None

        # Set up mock config
        mock_init_config.return_value = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
            "shared_folder_id": "shared_folder",
        }

        # Create service with mocked dependencies
        service = GoogleDriveService()
        service._initialized = True
        service.drive_service = MagicMock()

        # Mock API response for delete
        mock_delete = MagicMock()
        service.drive_service.files().delete.return_value = mock_delete
        mock_delete.execute.return_value = None

        # Mock API response for update (move to trash)
        mock_update = MagicMock()
        service.drive_service.files().update.return_value = mock_update
        mock_update.execute.return_value = None

        # Test permanent deletion
        result = service.delete_file("fileId", permanent=True)
        assert result.success is True
        service.drive_service.files().delete.assert_called_once_with(fileId="fileId")

        # Test move to trash
        service.drive_service.files().update.reset_mock()
        result = service.delete_file("fileId", permanent=False)
        assert result.success is True
        service.drive_service.files().update.assert_called_once_with(
            fileId="fileId", body={"trashed": True}
        )

        # Test API error
        service.drive_service.files().update.side_effect = QuackApiError(
            "API error", service="drive"
        )
        result = service.delete_file("error_fileId")
        assert result.success is False
        assert "API error" in result.error
