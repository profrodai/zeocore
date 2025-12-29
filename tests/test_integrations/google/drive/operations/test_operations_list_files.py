# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/operations/test_operations_list_files.py
# role: operations
# neighbors: __init__.py, test_operations_download.py, test_operations_folder.py, test_operations_permissions.py, test_operations_upload.py
# exports: TestDriveOperationsListFiles
# git_branch: refactor/toolkitWorkflow
# git_commit: 7e3e554
# === QV-LLM:END ===

"""
Tests for Google Drive _operations list_files module.
"""

from unittest.mock import patch

from quack_core.integrations.google.drive.models import DriveFile, DriveFolder
from quack_core.integrations.google.drive.operations import list_files
from quack_core.lib.errors import QuackApiError

from tests.test_integrations.google.drive.mocks import (
    MockDriveFilesResource,
    MockDriveService,
    create_error_drive_service,
    create_mock_drive_service,
)


class TestDriveOperationsListFiles:
    """Tests for the Google Drive _operations list_files functions."""

    def test_list_files(self) -> None:
        """Test listing files from Google Drive."""
        # Create mock file list for the service
        mock_file_list = [
            {
                "id": "file1",
                "name": "test.txt",
                "mimeType": "text/plain",
                "webViewLink": "https://drive.google.com/file/d/file1/view",
                "size": "12345",
                "shared": True,
                "trashed": False,
            },
            {
                "id": "folder1",
                "name": "Test Folder",
                "mimeType": "application/vnd.google-apps.folder",
                "webViewLink": "https://drive.google.com/drive/folders/folder1",
            },
        ]

        # Create mock drive service with our factory
        mock_drive_service = create_mock_drive_service(file_list=mock_file_list)

        # Setup mock execute_api_request - correct the import path
        with patch(
            "quack_core.integrations.google.drive.operations.list_files.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {"files": mock_file_list}

            # Setup mock build_query - correct the import path
            with patch(
                "quack_core.integrations.google.drive.operations.list_files.build_query"
            ) as mock_query:
                mock_query.return_value = "query"

                # Test successful listing
                result = list_files.list_files(mock_drive_service, "folder123", "*.txt")

                # Verify result
                assert result.success is True
                assert len(result.content) == 2

                # Check that the first item is a file
                assert result.content[0]["id"] == "file1"
                assert result.content[0]["name"] == "test.txt"
                assert result.content[0]["mime_type"] == "text/plain"

                # Check that the second item is a folder
                assert result.content[1]["id"] == "folder1"
                assert result.content[1]["name"] == "Test Folder"
                assert (
                    result.content[1]["mime_type"]
                    == "application/vnd.google-apps.folder"
                )

                # Check that execute_api_request was called correctly
                mock_execute.assert_called_once()
                call_args = mock_execute.call_args[0]
                assert call_args[1] == "Failed to list files from Google Drive"
                assert call_args[2] == "files.list"

                # Check that query was built correctly
                mock_query.assert_called_once_with("folder123", "*.txt")

                # Verify that our mock service was used correctly
                mock_service = mock_drive_service
                assert isinstance(mock_service, MockDriveService)
                assert mock_service.files_call_count == 1

                # Check that the files resource methods were called with correct parameters
                files_resource = mock_service.files()
                assert isinstance(files_resource, MockDriveFilesResource)
                assert files_resource.list_call_count == 1
                assert files_resource.last_list_query == "query"

    def test_list_files_empty_response(self) -> None:
        """Test listing files with empty response."""
        # Create mock drive service with empty file list
        mock_drive_service = create_mock_drive_service(file_list=[])

        # Mock empty response
        mock_response = {}

        # Setup mock execute_api_request with correct path
        with patch(
            "quack_core.integrations.google.drive.operations.list_files.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = mock_response

            # Setup mock build_query with correct path
            with patch(
                "quack_core.integrations.google.drive.operations.list_files.build_query"
            ) as mock_query:
                mock_query.return_value = "query"

                # Test empty response handling
                result = list_files.list_files(mock_drive_service)

                # Verify result
                assert result.success is True
                assert len(result.content) == 0
                assert "Listed 0 files" in result.message

                # Verify mock service usage
                mock_service = mock_drive_service
                assert isinstance(mock_service, MockDriveService)
                files_resource = mock_service.files()
                assert isinstance(files_resource, MockDriveFilesResource)
                assert files_resource.list_call_count == 1

    def test_list_files_error(self) -> None:
        """Test error handling when listing files."""
        # Create error-raising mock drive service
        mock_drive_service = create_error_drive_service(
            list_error=QuackApiError(
                "API error", service="Google Drive", api_method="files.list"
            )
        )

        # Setup mock execute_api_request to raise an error
        with patch(
            "quack_core.integrations.google.drive.operations.list_files.execute_api_request"
        ) as mock_execute:
            mock_execute.side_effect = QuackApiError(
                "API error", service="Google Drive", api_method="files.list"
            )

            # Setup mock build_query
            with patch(
                "quack_core.integrations.google.drive.operations.list_files.build_query"
            ) as mock_query:
                mock_query.return_value = "query"

                # Test error handling
                result = list_files.list_files(mock_drive_service)

                # Verify result
                assert result.success is False
                assert "API error" in result.error

    def test_list_files_invalid_response(self) -> None:
        """Test handling invalid response data when listing files."""
        # Create mock drive service
        mock_drive_service = create_mock_drive_service()

        # Mock invalid response data
        mock_response = {
            "files": "not a list"  # Invalid files value
        }

        # Setup mock execute_api_request
        with patch(
            "quack_core.integrations.google.drive.operations.list_files.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = mock_response

            # Setup mock build_query
            with patch(
                "quack_core.integrations.google.drive.operations.list_files.build_query"
            ) as mock_query:
                mock_query.return_value = "query"

                # Test invalid response handling
                result = list_files.list_files(mock_drive_service)

                # Verify result
                assert result.success is True
                assert len(result.content) == 0  # Should handle gracefully

    def test_list_files_with_model_conversion(self) -> None:
        """Test that list_files correctly converts API responses to DriveFile and DriveFolder models."""
        # Create a customized mock service with detailed file list
        file_list = [
            {
                "id": "file1",
                "name": "document.pdf",
                "mimeType": "application/pdf",
                "webViewLink": "https://drive.google.com/file/d/file1/view",
                "size": "5000000",
                "createdTime": "2023-01-01T10:00:00.000Z",
                "modifiedTime": "2023-01-02T14:30:00.000Z",
                "parents": ["folder1"],
                "shared": True,
                "trashed": False,
            },
            {
                "id": "folder1",
                "name": "Projects",
                "mimeType": "application/vnd.google-apps.folder",
                "folderColorRgb": "#4285F4",
            },
        ]

        mock_drive_service = create_mock_drive_service(file_list=file_list)

        # Create model instances for comparison
        expected_file = DriveFile.from_api_response(file_list[0])
        expected_folder = DriveFolder.from_api_response(file_list[1])

        # Mock API responses
        with patch(
            "quack_core.integrations.google.drive.operations.list_files.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {"files": file_list}

            with patch(
                "quack_core.integrations.google.drive.operations.list_files.build_query"
            ):
                # Call the function
                result = list_files.list_files(mock_drive_service)

                # Verify model conversion
                assert result.success is True
                assert len(result.content) == 2

                # Check file properties
                file_result = result.content[0]
                assert file_result["id"] == "file1"
                assert file_result["mime_type"] == "application/pdf"
                assert file_result["size"] == 5000000  # Converted from string to int
                assert file_result["parents"] == ["folder1"]
                assert file_result["shared"] is True

                # Check folder properties
                folder_result = result.content[1]
                assert folder_result["id"] == "folder1"
                assert folder_result["name"] == "Projects"
                assert (
                    folder_result["mime_type"] == "application/vnd.google-apps.folder"
                )
                assert folder_result["folder_color_rgb"] == "#4285F4"
