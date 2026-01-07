# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/operations/test_operations_upload.py
# role: operations
# neighbors: __init__.py, test_operations_download.py, test_operations_folder.py, test_operations_list_files.py, test_operations_permissions.py
# exports: TestDriveOperationsUpload
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Tests for Google Drive _operations upload module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.operations import upload
from quack_core.core.errors import QuackApiError, QuackIntegrationError
from quack_core.core.paths.api.public.results import PathResult

from tests.test_integrations.google.drive.mocks import (
    MockDriveFilesResource,
    MockDriveService,
    create_credentials,
    create_mock_drive_service,
)


class TestDriveOperationsUpload:
    """Tests for the Google Drive _operations upload functions."""

    def test_initialize_drive_service(self) -> None:
        """Test initializing the Drive service."""
        # Create mock credentials using our factory
        mock_credentials = create_credentials()

        # Create the mock service we expect to be returned
        mock_drive_service = create_mock_drive_service()

        # Patch the build function where it's imported in upload.py
        with patch(
            "quack_core.integrations.google.drive.operations.upload.build"
        ) as mock_build:
            # Configure the mock to return our mock service
            mock_build.return_value = mock_drive_service

            # Test successful initialization
            result = upload.initialize_drive_service(mock_credentials)

            # Assertions
            assert result == mock_drive_service
            mock_build.assert_called_once_with(
                "drive", "v3", credentials=mock_credentials
            )

    def test_initialize_drive_service_error(self) -> None:
        """Test error handling during Drive service initialization."""
        # Create mock credentials using our factory
        mock_credentials = create_credentials()

        # Patch the build function where it's imported in upload.py
        with patch(
            "quack_core.integrations.google.drive.operations.upload.build"
        ) as mock_build:
            # Configure the mock to raise an exception
            mock_build.side_effect = Exception("API error")

            # Test error handling
            with pytest.raises(QuackApiError) as excinfo:
                upload.initialize_drive_service(mock_credentials)

            assert "Failed to initialize Google Drive API" in str(excinfo.value)
            assert excinfo.value.service == "Google Drive"
            assert excinfo.value.api_method == "build"

    def test_resolve_file_details(self, tmp_path: Path) -> None:
        """Test resolving file details for upload."""
        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Mock resolver
        with patch("quack_core.integrations.google.drive.operations.upload.paths_service") as mock_paths_service:
            mock_paths_service.resolve_project_path.return_value = PathResult(
                success=True,
                path=str(test_file)  # Use string, not Path
            )

            # Mock file info
            with patch("quack_core.core.fs.service.standalone.get_file_info") as mock_info:
                mock_info.return_value.success = True
                mock_info.return_value.exists = True

                # Mock get_mime_type
                with patch("quack_core.core.fs.service.standalone.get_mime_type") as mock_mime:
                    mock_mime.return_value = "text/plain"

                    # Test with default parameters
                    path_obj, filename, folder_id, mime_type = (
                        upload.resolve_file_details(str(test_file), None, None)
                    )

                    assert path_obj == str(test_file)
                    assert filename == "test_file.txt"
                    assert folder_id is None
                    assert mime_type == "text/plain"

                    # Test with custom parameters
                    path_obj, filename, folder_id, mime_type = (
                        upload.resolve_file_details(
                            str(test_file), "remote_name.txt", "folder123"
                        )
                    )

                    assert path_obj == str(test_file)
                    assert filename == "remote_name.txt"
                    assert folder_id == "folder123"
                    assert mime_type == "text/plain"

    def test_resolve_file_details_not_found(self, tmp_path: Path) -> None:
        """Test error handling when file is not found."""
        # Create a non-existent file path
        test_file = tmp_path / "nonexistent.txt"

        # Mock resolver
        with patch("quack_core.integrations.google.drive.operations.upload.paths_service") as mock_paths_service:
            mock_paths_service.resolve_project_path.return_value = PathResult(
                success=True,
                path=str(test_file)  # Use string, not Path
            )

            # Mock file info to show file doesn't exist
            with patch("quack_core.core.fs.service.standalone.get_file_info") as mock_info:
                mock_info.return_value.success = True
                mock_info.return_value.exists = False

                # Test error handling
                with pytest.raises(QuackIntegrationError) as excinfo:
                    upload.resolve_file_details(str(test_file), None, None)

                assert "File not found" in str(excinfo.value)

    def test_upload_file_simple(self, tmp_path: Path) -> None:
        """Test uploading a file to Google Drive with simplified approach."""
        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Create mock drive service
        mock_drive_service = create_mock_drive_service()

        # Get the MockDriveFilesResource from our mock service
        files_resource = mock_drive_service.files()
        # Configure the create method to return a specific result
        create_method = MagicMock()
        create_method.return_value = MagicMock()
        files_resource.create = create_method

        # Mock file resolution - bypassing internal function calls
        with patch.object(upload, "resolve_file_details") as mock_resolve:
            mock_resolve.return_value = (
                str(test_file),
                "test_file.txt",
                "folder123",
                "text/plain",
            )

            # Mock standalone operations
            with patch(
                "quack_core.integrations.google.drive.operations.upload.standalone"
            ) as mock_fs:
                mock_fs.read_binary.return_value.success = True
                mock_fs.read_binary.return_value.content = b"test content"

                # Mock the MediaInMemoryUpload
                with patch(
                    "quack_core.integrations.google.drive.operations.upload.MediaInMemoryUpload"
                ) as mock_media:
                    mock_media.return_value = MagicMock()

                    # Mock the execute_api_request to avoid API calls
                    with patch(
                        "quack_core.integrations.google.drive.operations.upload.execute_api_request"
                    ) as mock_execute:
                        # Set up our mock to return expected data
                        mock_execute.return_value = {
                            "id": "file123",
                            "webViewLink": "https://drive.google.com/file/d/file123/view",
                        }

                        # Mock permissions to avoid that call
                        with patch(
                            "quack_core.integrations.google.drive.operations.permissions.set_file_permissions"
                        ) as mock_perm:
                            mock_perm.return_value = IntegrationResult(success=True)

                            # Call the function
                            result = upload.upload_file(
                                mock_drive_service,
                                str(test_file),
                                description="Test file",
                                parent_folder_id="folder123",
                            )

                            # Verify the result
                            assert result.success is True
                            assert (
                                result.content
                                == "https://drive.google.com/file/d/file123/view"
                            )

                            # Verify mock calls
                            mock_execute.assert_called_once()
                            mock_perm.assert_called_once()

    def test_upload_file_read_error(self, tmp_path: Path) -> None:
        """Test error handling when reading file fails."""
        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Create mock drive service
        mock_drive_service = create_mock_drive_service()

        # Mock resolve_file_details
        with patch.object(upload, "resolve_file_details") as mock_resolve:
            mock_resolve.return_value = (
                str(test_file),
                "test_file.txt",
                "folder123",
                "text/plain",
            )

            # Mock read_binary to fail using the correct import path
            with patch(
                    "quack_core.integrations.google.drive.operations.upload.standalone"
            ) as mock_fs:
                mock_fs.read_binary.return_value.success = False
                mock_fs.read_binary.return_value.error = "Read error"

                # Test error handling
                result = upload.upload_file(mock_drive_service, str(test_file))

                assert result.success is False
                assert "Failed to read file: Read error" in result.error

    def test_upload_file_api_error(self, tmp_path: Path) -> None:
        """Test error handling when API call fails."""
        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Create mock drive service
        mock_drive_service = create_mock_drive_service()

        # Mock resolve_file_details
        with patch.object(upload, "resolve_file_details") as mock_resolve:
            mock_resolve.return_value = (
                str(test_file),
                "test_file.txt",
                "folder123",
                "text/plain",
            )

            # Mock read_binary
            with patch(
                    "quack_core.integrations.google.drive.operations.upload.standalone"
            ) as mock_fs:
                mock_fs.read_binary.return_value.success = True
                mock_fs.read_binary.return_value.content = b"test content"

                # Use MagicMock for MediaInMemoryUpload
                media_mock = MagicMock()

                # Patch MediaInMemoryUpload with our mock
                with patch(
                        "quack_core.integrations.google.drive.operations.upload.MediaInMemoryUpload",
                        return_value=media_mock,
                ):
                    # Mock execute_api_request to raise an error
                    with patch(
                            "quack_core.integrations.google.drive.operations.upload.execute_api_request"
                    ) as mock_execute:
                        mock_execute.side_effect = QuackApiError(
                            "API error",
                            service="Google Drive",
                            api_method="files.create",
                        )

                        # Test error handling
                        result = upload.upload_file(mock_drive_service, str(test_file))

                        assert result.success is False
                        assert "API error" in result.error

    def test_upload_file_with_specific_metadata(self, tmp_path: Path) -> None:
        """Test uploading a file with specific metadata configuration."""
        # Create a test file
        test_file = tmp_path / "document.pdf"
        test_file.write_text("PDF content")

        # Create a custom mock service with specific file metadata
        mock_drive_service = create_mock_drive_service(
            fileId="doc123",
            file_metadata={
                "id": "doc123",
                "name": "document.pdf",
                "mimeType": "application/pdf",
                "webViewLink": "https://drive.google.com/file/d/doc123/view",
                "description": "Important document",
            },
        )

        # Mock resolve_file_details
        with patch.object(upload, "resolve_file_details") as mock_resolve:
            mock_resolve.return_value = (
                str(test_file),
                "document.pdf",
                "folder456",
                "application/pdf",
            )

            # Mock read_binary
            with patch(
                    "quack_core.integrations.google.drive.operations.upload.standalone"
            ) as mock_fs:
                mock_fs.read_binary.return_value.success = True
                mock_fs.read_binary.return_value.content = b"PDF content"

                # Use MagicMock for MediaInMemoryUpload
                media_mock = MagicMock()

                # Patch MediaInMemoryUpload with our mock
                with patch(
                        "quack_core.integrations.google.drive.operations.upload.MediaInMemoryUpload",
                        return_value=media_mock,
                ):
                    # Mock execute_api_request
                    with patch(
                            "quack_core.integrations.google.drive.operations.upload.execute_api_request"
                    ) as mock_execute:
                        mock_execute.return_value = {
                            "id": "doc123",
                            "name": "document.pdf",
                            "mimeType": "application/pdf",
                            "webViewLink": "https://drive.google.com/file/d/doc123/view",
                            "description": "Important document",
                        }

                        # Mock permissions but disable public sharing
                        with patch(
                                "quack_core.integrations.google.drive.operations.permissions.set_file_permissions"
                        ):
                            # Test upload with specific metadata
                            result = upload.upload_file(
                                mock_drive_service,
                                str(test_file),
                                description="Important document",
                                parent_folder_id="folder456",
                                make_public=False,  # Don't make it public
                            )

                            assert result.success is True
                            assert (
                                    result.content
                                    == "https://drive.google.com/file/d/doc123/view"
                            )

                            # Verify the file metadata was constructed correctly
                            mock_service = mock_drive_service
                            assert isinstance(mock_service, MockDriveService)
                            files_resource = mock_service.files()
                            assert isinstance(files_resource, MockDriveFilesResource)

                            # Check the body passed to create
                            assert files_resource.create_call_count == 1
                            assert (
                                    files_resource.last_create_body["name"]
                                    == "document.pdf"
                            )
                            assert (
                                    files_resource.last_create_body["mimeType"]
                                    == "application/pdf"
                            )
                            assert (
                                    files_resource.last_create_body["description"]
                                    == "Important document"
                            )
                            assert files_resource.last_create_body["parents"] == [
                                "folder456"
                            ]
