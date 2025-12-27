# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/operations/test_operations_folder.py
# role: operations
# neighbors: __init__.py, test_operations_download.py, test_operations_list_files.py, test_operations_permissions.py, test_operations_upload.py
# exports: TestDriveOperationsFolder
# git_branch: refactor/newHeaders
# git_commit: bd13631
# === QV-LLM:END ===

"""
Tests for Google Drive _operations folder module.
"""

import logging
from unittest.mock import patch

from quack_core.lib.errors import QuackApiError
from quack_core.integrations.google.drive.operations import folder
from tests.test_integrations.google.drive.mocks import (
    MockDriveFilesResource,
    MockDriveService,
    create_error_drive_service,
    create_mock_drive_service,
)


class TestDriveOperationsFolder:
    """Tests for the Google Drive _operations folder functions."""

    def test_create_folder(self) -> None:
        """Test creating a folder in Google Drive."""
        # Create mock drive service with our factory
        mock_drive_service = create_mock_drive_service(
            fileId="folder123",
            file_metadata={
                "id": "folder123",
                "name": "Test Folder",
                "mimeType": "application/vnd.google-apps.folder",
                "webViewLink": "https://drive.google.com/drive/folders/folder123",
            },
        )

        # Mock API request execution - make sure the path matches exactly what's in folder.py
        with patch(
            "quack_core.integrations.google.drive.operations.folder.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {
                "id": "folder123",
                "webViewLink": "https://drive.google.com/drive/folders/folder123",
            }

            # Mock set_file_permissions - make sure the path matches exactly
            with patch(
                "quack_core.integrations.google.drive.operations.folder.set_file_permissions"
            ) as mock_permissions:
                # Set up the mock to return a successful result
                mock_permissions.return_value.success = True

                # Test successful folder creation with a None logger
                result = folder.create_folder(
                    mock_drive_service,
                    "Test Folder",
                    "parent123",
                    make_public=True,
                    logger=None,
                )

                assert result.success is True
                assert result.content == "folder123"

                # Check that execute_api_request was called correctly
                mock_execute.assert_called_once()
                call_args = mock_execute.call_args[0]
                assert call_args[1] == "Failed to create folder in Google Drive"
                assert call_args[2] == "files.create"

                # Check permissions was called with None logger
                mock_permissions.assert_called_once_with(
                    mock_drive_service, "folder123", "reader", "anyone", None
                )

                # Verify that our mock service was used correctly
                mock_service = mock_drive_service
                assert isinstance(mock_service, MockDriveService)
                assert mock_service.files_call_count == 1

                # Check that the files resource methods were called with correct parameters
                files_resource = mock_service.files()
                assert isinstance(files_resource, MockDriveFilesResource)
                assert files_resource.create_call_count == 1
                assert files_resource.last_create_body["name"] == "Test Folder"
                assert (
                    files_resource.last_create_body["mimeType"]
                    == "application/vnd.google-apps.folder"
                )
                assert files_resource.last_create_body["parents"] == ["parent123"]

    def test_create_folder_with_logger(self) -> None:
        """Test creating a folder with an explicit logger."""
        # Create mock drive service
        mock_drive_service = create_mock_drive_service(fileId="folder456")

        # Create a mock logger
        mock_logger = logging.getLogger("test_logger")

        # Mock API request execution
        with patch(
            "quack_core.integrations.google.drive.operations.folder.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {
                "id": "folder456",
                "webViewLink": "https://drive.google.com/drive/folders/folder456",
            }

            # Mock set_file_permissions
            with patch(
                "quack_core.integrations.google.drive.operations.folder.set_file_permissions"
            ) as mock_permissions:
                mock_permissions.return_value.success = True

                # Test with explicit logger
                result = folder.create_folder(
                    mock_drive_service, "Test Folder", logger=mock_logger
                )

                assert result.success is True

                # Verify the mock logger was passed through
                mock_permissions.assert_called_once_with(
                    mock_drive_service, "folder456", "reader", "anyone", mock_logger
                )

    def test_create_folder_error(self) -> None:
        """Test error handling when creating a folder."""
        # Create error-raising mock drive service
        mock_drive_service = create_error_drive_service(
            create_error=QuackApiError(
                "API error", service="Google Drive", api_method="files.create"
            )
        )

        # Mock API error - adjust path to match folder.py
        with patch(
            "quack_core.integrations.google.drive.operations.folder.execute_api_request"
        ) as mock_execute:
            mock_execute.side_effect = QuackApiError(
                "API error", service="Google Drive", api_method="files.create"
            )

            # Test error handling
            result = folder.create_folder(mock_drive_service, "Test Folder")

            assert result.success is False
            assert "API error" in result.error

    def test_delete_file_permanent(self) -> None:
        """Test permanently deleting a file."""
        # Create mock drive service
        mock_drive_service = create_mock_drive_service(fileId="file123")

        # Mock API request execution - adjust path to match folder.py
        with patch(
            "quack_core.integrations.google.drive.operations.folder.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = None

            # Test successful permanent deletion
            result = folder.delete_file(mock_drive_service, "file123", permanent=True)

            assert result.success is True
            assert result.content is True

            # Check that execute_api_request was called correctly
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0]
            assert call_args[1] == "Failed to delete file from Google Drive"
            assert call_args[2] == "files.delete"

            # Verify mock service was used correctly
            mock_service = mock_drive_service
            assert isinstance(mock_service, MockDriveService)
            files_resource = mock_service.files()
            assert isinstance(files_resource, MockDriveFilesResource)
            assert files_resource.delete_call_count == 1
            assert files_resource.last_delete_file_id == "file123"

    def test_delete_file_trash(self) -> None:
        """Test moving a file to trash."""
        # Create mock drive service
        mock_drive_service = create_mock_drive_service(fileId="file123")

        # Mock API request execution - adjust path to match folder.py
        with patch(
            "quack_core.integrations.google.drive.operations.folder.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {"id": "file123", "trashed": True}

            # Test successful move to trash
            result = folder.delete_file(mock_drive_service, "file123", permanent=False)

            assert result.success is True
            assert result.content is True

            # Check that execute_api_request was called correctly
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0]
            assert call_args[1] == "Failed to trash file in Google Drive"
            assert call_args[2] == "files.update"

            # Verify mock service was used correctly
            mock_service = mock_drive_service
            assert isinstance(mock_service, MockDriveService)
            files_resource = mock_service.files()
            assert isinstance(files_resource, MockDriveFilesResource)
            assert files_resource.update_call_count == 1
            assert files_resource.last_update_file_id == "file123"
            assert files_resource.last_update_body == {"trashed": True}

    def test_delete_file_error(self) -> None:
        """Test error handling when deleting a file."""
        # Create error-raising mock drive service
        mock_drive_service = create_error_drive_service(
            delete_error=QuackApiError(
                "API error", service="Google Drive", api_method="files.delete"
            )
        )

        # Mock API error - adjust path to match folder.py
        with patch(
            "quack_core.integrations.google.drive.operations.folder.execute_api_request"
        ) as mock_execute:
            mock_execute.side_effect = QuackApiError(
                "API error", service="Google Drive", api_method="files.delete"
            )

            # Test error handling
            result = folder.delete_file(mock_drive_service, "file123", permanent=True)

            assert result.success is False
            assert "API error" in result.error

    def test_delete_file_with_specific_mock_configuration(self) -> None:
        """Test file deletion with custom mock configuration."""
        # Create a customized mock service directly using the mock classes
        files_resource = MockDriveFilesResource(
            fileId="custom123",
            file_metadata={"id": "custom123", "name": "Custom File"},
        )
        mock_service = MockDriveService(files_resource)

        # Mock API request execution - adjust path to match folder.py
        custom_api_response = {"id": "custom123", "trashed": True}

        with patch(
            "quack_core.integrations.google.drive.operations.folder.execute_api_request",
            return_value=custom_api_response,
        ):
            # Test deletion
            result = folder.delete_file(mock_service, "custom123")

            assert result.success is True
            assert result.content is True

            # Verify custom mock behavior
            assert isinstance(mock_service, MockDriveService)
            assert mock_service.files_call_count == 1

            # Check file resource calls
            files_resource = mock_service.files()
            assert isinstance(files_resource, MockDriveFilesResource)
            assert files_resource.update_call_count == 1  # trash, not permanent delete
            assert files_resource.last_update_file_id == "custom123"
