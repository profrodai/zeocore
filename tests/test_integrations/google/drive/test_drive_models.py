# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive_models.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive.py, test_drive_service_delete.py, test_drive_service_download.py, test_drive_service_files.py (+6 more)
# exports: TestDriveModels
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===

"""
Tests for Google Drive models.
"""

import pytest
from pydantic import ValidationError

from quack_core.integrations.google.drive.models import DriveFile, DriveFolder


class TestDriveModels:
    """Tests for Google Drive models."""

    def test_drive_file_model(self) -> None:
        """Test the DriveFile model."""
        # Test minimal file
        file = DriveFile(id="file1", name="test.txt", mime_type="text/plain")
        assert file.id == "file1"
        assert file.name == "test.txt"
        assert file.mime_type == "text/plain"
        assert file.parents == []
        assert file.web_view_link is None
        assert file.size is None
        assert file.trashed is False

        # Test complete file
        file = DriveFile(
            id="file2",
            name="document.pdf",
            mime_type="application/pdf",
            parents=["folder1"],
            web_view_link="https://drive.google.com/file/d/file2/view",
            web_content_link="https://drive.google.com/uc?id=file2",
            size=12345,
            trashed=True,
        )
        assert file.id == "file2"
        assert file.name == "document.pdf"
        assert file.mime_type == "application/pdf"
        assert file.parents == ["folder1"]
        assert file.web_view_link == "https://drive.google.com/file/d/file2/view"
        assert file.web_content_link == "https://drive.google.com/uc?id=file2"
        assert file.size == 12345
        assert file.trashed is True

    def test_drive_folder_model(self) -> None:
        """Test the DriveFolder model."""
        folder = DriveFolder(
            id="folder1",
            name="My Folder",
            mime_type="application/vnd.google-apps.folder",
            folder_color_rgb="#FF0000",
        )
        assert folder.id == "folder1"
        assert folder.name == "My Folder"
        assert folder.mime_type == "application/vnd.google-apps.folder"
        assert folder.folder_color_rgb == "#FF0000"

        # Ensure inheritance from DriveFile
        assert isinstance(folder, DriveFile)

    def test_from_api_response(self) -> None:
        """Test creating models from API responses."""
        # Test file response
        file_response = {
            "id": "file1",
            "name": "test.txt",
            "mimeType": "text/plain",
            "parents": ["folder1"],
            "webViewLink": "https://drive.google.com/file/d/file1/view",
            "size": "12345",
            "createdTime": "2023-01-01T12:00:00.000Z",
            "modifiedTime": "2023-01-02T12:00:00.000Z",
            "shared": True,
            "trashed": False,
        }

        file = DriveFile.from_api_response(file_response)
        assert file.id == "file1"
        assert file.name == "test.txt"
        assert file.mime_type == "text/plain"
        assert file.parents == ["folder1"]
        assert file.web_view_link == "https://drive.google.com/file/d/file1/view"
        assert file.size == 12345
        assert file.shared is True
        assert file.trashed is False
        assert file.created_time is not None
        assert file.modified_time is not None

        # Test folder response
        folder_response = {
            "id": "folder1",
            "name": "My Folder",
            "mimeType": "application/vnd.google-apps.folder",
            "folderColorRgb": "#FF0000",
        }

        folder = DriveFolder.from_api_response(folder_response)
        assert folder.id == "folder1"
        assert folder.name == "My Folder"
        assert folder.mime_type == "application/vnd.google-apps.folder"
        assert folder.folder_color_rgb == "#FF0000"

        # Test non-folder mime type should still create folder
        not_folder_response = {
            "id": "folder2",
            "name": "Not a Folder",
            "mimeType": "text/plain",
        }

        folder = DriveFolder.from_api_response(not_folder_response)
        assert folder.id == "folder2"
        assert folder.name == "Not a Folder"
        assert folder.mime_type == "application/vnd.google-apps.folder"

    def test_validation(self) -> None:
        """Test model validation."""
        # Missing required fields
        with pytest.raises(ValidationError):
            DriveFile(name="test.txt", mime_type="text/plain")  # Missing id

        with pytest.raises(ValidationError):
            DriveFile(id="file1", mime_type="text/plain")  # Missing name

        with pytest.raises(ValidationError):
            DriveFile(id="file1", name="test.txt")  # Missing mime_type
