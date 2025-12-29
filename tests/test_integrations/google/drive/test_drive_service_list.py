# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive_service_list.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive.py, test_drive_models.py, test_drive_service_delete.py, test_drive_service_download.py (+6 more)
# exports: TestGoogleDriveServiceList
# git_branch: refactor/toolkitWorkflow
# git_commit: 21647d6
# === QV-LLM:END ===

"""
Tests for Google Drive service listing _operations.
"""

from unittest.mock import MagicMock, patch

from quack_core.integrations.google.drive.service import GoogleDriveService
from quack_core.lib.errors import QuackApiError


class TestGoogleDriveServiceList:
    """Tests for the GoogleDriveService listing _operations."""

    @patch(
        "quack_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch.object(GoogleDriveService, "_initialize_config")
    def test_list_files(self, mock_init_config, mock_verify) -> None:
        """Test listing files."""
        # Bypass verification
        mock_verify.return_value = None

        # Mock configuration
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
        mock_list = MagicMock()
        service.drive_service.files().list.return_value = mock_list
        mock_list.execute.return_value = {
            "files": [
                {
                    "id": "file1",
                    "name": "test1.txt",
                    "mimeType": "text/plain",
                },
                {
                    "id": "folder1",
                    "name": "Test Folder",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ]
        }

        # Test successful listing
        with patch.object(service, "_build_query") as mock_query:
            mock_query.return_value = "query"

            result = service.list_files("folder123", "*.txt")

            assert result.success is True
            assert len(result.content) == 2
            assert result.content[0]["id"] == "file1"
            assert result.content[1]["id"] == "folder1"
            service.drive_service.files().list.assert_called_once_with(
                q="query",
                fields="files(id, name, mimeType, webViewLink, webContentLink, "
                "size, createdTime, modifiedTime, parents, shared, trashed)",
                page_size=100,
            )
            mock_query.assert_called_once_with("folder123", "*.txt")

        # Test API error
        service.drive_service.files().list.side_effect = QuackApiError(
            "API error", service="drive"
        )
        result = service.list_files()
        assert result.success is False
        assert "API error" in result.error
