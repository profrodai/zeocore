# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_protocols.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive.py, test_drive_models.py, test_drive_service_delete.py, test_drive_service_download.py (+6 more)
# exports: TestDriveProtocols
# git_branch: refactor/toolkitWorkflow
# git_commit: 21a4e25
# === QV-LLM:END ===

"""
Tests for Google Drive protocols module.
"""

from unittest.mock import MagicMock

from quack_core.integrations.google.drive.protocols import (
    DriveFilesResource,
    DrivePermissionsResource,
    DriveRequest,
    DriveService,
    GoogleCredentials,
)
from tests.test_integrations.google.drive.mocks import (
    MockDriveFilesResource,
    MockDrivePermissionsResource,
    MockDriveRequest,
    MockDriveService,
    MockGoogleCredentials,
    create_credentials,
    create_mock_drive_service,
)


class TestDriveProtocols:
    """Tests for Google Drive protocol classes."""

    def test_drive_request_protocol(self) -> None:
        """Test DriveRequest protocol implementation."""
        # Create our MockDriveRequest that implements the DriveRequest protocol
        mock_request = MockDriveRequest({"id": "file123"})

        # Check if it matches the protocol
        assert isinstance(mock_request, DriveRequest)

        # Test using the protocol method
        result = mock_request.execute()
        assert result == {"id": "file123"}
        assert mock_request.call_count == 1

        # Test with an object missing required methods
        incomplete_mock = MagicMock()
        # MagicMock has an execute method by default, so we need to remove it
        delattr(incomplete_mock, "execute")
        assert not isinstance(incomplete_mock, DriveRequest)

    def test_drive_permissions_resource_protocol(self) -> None:
        """Test DrivePermissionsResource protocol implementation."""
        # Create our MockDrivePermissionsResource that implements the protocol
        mock_permissions = MockDrivePermissionsResource(permission_id="perm123")

        # Check if it matches the protocol
        assert isinstance(mock_permissions, DrivePermissionsResource)

        # Test using the protocol method
        result = mock_permissions.create(
            fileId="file123", body={"type": "anyone", "role": "reader"}, fields="id"
        )

        # Verify the result is a DriveRequest
        assert isinstance(result, DriveRequest)

        # Verify that our mock captured the correct parameters
        assert mock_permissions.last_file_id == "file123"
        assert mock_permissions.last_permission_body["type"] == "anyone"
        assert mock_permissions.last_permission_body["role"] == "reader"
        assert mock_permissions.last_fields == "id"
        assert mock_permissions.create_call_count == 1

        # Test with an object missing required methods
        incomplete_mock = MagicMock()
        delattr(incomplete_mock, "create")
        assert not isinstance(incomplete_mock, DrivePermissionsResource)

    def test_drive_files_resource_protocol(self) -> None:
        """Test DriveFilesResource protocol implementation."""
        # Create our MockDriveFilesResource that implements the protocol
        mock_files = MockDriveFilesResource(
            fileId="file123", file_metadata={"id": "file123", "name": "test.txt"}
        )

        # Check if it matches the protocol
        assert isinstance(mock_files, DriveFilesResource)

        # Test using the protocol methods
        # Test create
        result = mock_files.create(
            body={"name": "test.txt"}, media_body=MagicMock(), fields="id,webViewLink"
        )
        assert isinstance(result, DriveRequest)
        assert mock_files.create_call_count == 1
        assert mock_files.last_create_body["name"] == "test.txt"
        assert mock_files.last_create_fields == "id,webViewLink"

        # Test get
        result = mock_files.get(fileId="file123", fields="name,mimeType")
        assert isinstance(result, DriveRequest)
        assert mock_files.get_call_count == 1
        assert mock_files.last_get_file_id == "file123"
        assert mock_files.last_get_fields == "name,mimeType"

        # Test get_media
        result = mock_files.get_media(fileId="file123")
        assert isinstance(result, DriveRequest)
        assert mock_files.get_media_call_count == 1
        assert mock_files.last_get_media_file_id == "file123"

        # Test list
        result = mock_files.list(q="query", fields="files", page_size=100)
        assert isinstance(result, DriveRequest)
        assert mock_files.list_call_count == 1
        assert mock_files.last_list_query == "query"
        assert mock_files.last_list_fields == "files"
        assert mock_files.last_list_page_size == 100

        # Test update
        result = mock_files.update(fileId="file123", body={"trashed": True})
        assert isinstance(result, DriveRequest)
        assert mock_files.update_call_count == 1
        assert mock_files.last_update_file_id == "file123"
        assert mock_files.last_update_body["trashed"] is True

        # Test delete
        result = mock_files.delete(fileId="file123")
        assert isinstance(result, DriveRequest)
        assert mock_files.delete_call_count == 1
        assert mock_files.last_delete_file_id == "file123"

        # Test permissions
        result = mock_files.permissions()
        assert isinstance(result, DrivePermissionsResource)

        # Test with an object missing required methods
        incomplete_mock = MagicMock()
        delattr(incomplete_mock, "create")
        assert not isinstance(incomplete_mock, DriveFilesResource)

    def test_drive_service_protocol(self) -> None:
        """Test DriveService protocol implementation."""
        # Create our MockDriveService that implements the protocol
        mock_service = create_mock_drive_service()

        # Check if it matches the protocol
        assert isinstance(mock_service, DriveService)

        # Test using the protocol method
        result = mock_service.files()
        assert isinstance(result, DriveFilesResource)

        # Cast to our mock type to access tracking attributes
        typed_mock_service = mock_service
        assert isinstance(typed_mock_service, MockDriveService)
        assert typed_mock_service.files_call_count == 1

        # Test with an object missing required methods
        incomplete_mock = MagicMock()
        delattr(incomplete_mock, "files")
        assert not isinstance(incomplete_mock, DriveService)

    def test_google_credentials_protocol(self) -> None:
        """Test GoogleCredentials protocol implementation."""
        # Create our MockGoogleCredentials that implements the protocol
        mock_credentials = create_credentials()

        # Check if it matches the protocol
        assert isinstance(mock_credentials, GoogleCredentials)

        # Verify attributes
        assert mock_credentials.token == "test_token"
        assert mock_credentials.refresh_token == "refresh_token"
        assert mock_credentials.token_uri == "https://oauth2.googleapis.com/token"
        assert mock_credentials.client_id == "client_id"
        assert mock_credentials.client_secret == "client_secret"
        assert mock_credentials.scopes == ["https://www.googleapis.com/auth/drive.file"]

        # Test with an object missing required attributes
        incomplete_mock = MagicMock()
        incomplete_mock.token = "token123"
        # Missing other required attributes
        assert not isinstance(incomplete_mock, GoogleCredentials)

    def test_custom_mock_vs_protocol(self) -> None:
        """Test that our mock classes fully satisfy their respective protocols."""
        # Create instances and test them against the protocols
        assert isinstance(MockDriveRequest({}), DriveRequest)
        assert isinstance(MockDrivePermissionsResource(), DrivePermissionsResource)
        assert isinstance(MockDriveFilesResource(), DriveFilesResource)
        assert isinstance(MockDriveService(), DriveService)
        assert isinstance(MockGoogleCredentials(), GoogleCredentials)

        # Test various instantiations with different parameters
        assert isinstance(MockDriveRequest({"id": "test"}, error=None), DriveRequest)
        assert isinstance(
            MockDrivePermissionsResource(permission_id="custom"),
            DrivePermissionsResource,
        )
        assert isinstance(
            MockDriveFilesResource(fileId="custom", file_metadata={"id": "custom"}),
            DriveFilesResource,
        )
