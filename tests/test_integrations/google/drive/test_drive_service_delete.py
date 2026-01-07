# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive_service_delete.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive.py, test_drive_models.py, test_drive_service_download.py, test_drive_service_files.py (+6 more)
# exports: TestGoogleDriveServiceDelete
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

"""
Tests for Google Drive service deletion _operations.
"""

from unittest.mock import MagicMock

from quack_core.integrations.google.drive.service import GoogleDriveService
from quack_core.lib.errors import QuackApiError


class TestGoogleDriveServiceDelete:
    """Tests for the GoogleDriveService deletion _operations."""

    def test_delete_file(self) -> None:
        """Test deleting a file."""
        # Create a service manually without initialization
        service = GoogleDriveService.__new__(GoogleDriveService)

        # Set up required attributes manually
        service._initialized = True
        service.drive_service = MagicMock()
        service.logger = MagicMock()

        # Mock API responses
        mock_delete = MagicMock()
        service.drive_service.files().delete.return_value = mock_delete
        mock_delete.execute.return_value = None

        mock_update = MagicMock()
        service.drive_service.files().update.return_value = mock_update
        mock_update.execute.return_value = {"id": "file123"}

        # Test permanent deletion
        result = service.delete_file("file123", permanent=True)

        assert result.success is True
        assert result.content is True
        service.drive_service.files().delete.assert_called_once_with(fileId="file123")
        service.drive_service.files().update.assert_not_called()

        # Test moving to trash (default)
        service.drive_service.files().delete.reset_mock()
        service.drive_service.files().update.reset_mock()

        result = service.delete_file("file123")

        assert result.success is True
        assert result.content is True
        service.drive_service.files().delete.assert_not_called()
        service.drive_service.files().update.assert_called_once_with(
            fileId="file123", body={"trashed": True}
        )

        # Test API error (delete)
        service.drive_service.files().delete.side_effect = QuackApiError(
            "API error", service="drive"
        )
        result = service.delete_file("file123", permanent=True)
        assert result.success is False
        assert "API error" in result.error

        # Test API error (update)
        service.drive_service.files().update.side_effect = QuackApiError(
            "API error", service="drive"
        )
        result = service.delete_file("file123")
        assert result.success is False
        assert "API error" in result.error
