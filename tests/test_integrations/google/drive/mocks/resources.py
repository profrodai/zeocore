# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/mocks/resources.py
# role: tests
# neighbors: __init__.py, base.py, credentials.py, download.py, media.py, requests.py (+1 more)
# exports: MockDrivePermissionsResource, MockDriveFilesResource
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Mock resource objects for Google Drive testing.
"""

from typing import Any, TypeVar, cast

from quack_core.integrations.google.drive.protocols import (
    DriveFilesResource,
    DrivePermissionsResource,
    DriveRequest,
)

from .requests import (
    MockDriveRequest,
)

T = TypeVar("T")  # Generic type for content
R = TypeVar("R")  # Generic type for return values


class MockDrivePermissionsResource(DrivePermissionsResource):
    """Mock permissions resource with configurable behavior."""

    def __init__(self, permission_id: str = "perm123", error: Exception | None = None):
        """
        Initialize mock permissions resource.

        Args:
            permission_id: ID to return for created permissions
            error: Exception to raise on API calls, if any
        """
        self.permission_id = permission_id
        self.error = error

        # Tracking attributes for assertions
        self.last_file_id: str | None = None
        self.last_permission_body: dict[str, object] | None = None
        self.last_fields: str | None = None
        self.create_call_count = 0

    def create(
        self,
        fileId: str = None,
        body: dict[str, object] = None,
        fields: str = None,
    ) -> DriveRequest[dict[str, object]]:
        """
        Mock create method for creating a permission.

        Args:
            fileId: ID of the file (implementation parameter)
            body: Permission data
            fields: Fields to include in the response

        Returns:
            A mock request that will return the permission data
        """
        # Handle parameter name differences

        self.create_call_count += 1
        self.last_file_id = fileId
        self.last_permission_body = body
        self.last_fields = fields

        request = MockDriveRequest({"id": self.permission_id}, self.error)
        request._body = body
        return request


class MockDriveFilesResource(DriveFilesResource):
    """Mock files resource with configurable behavior."""

    def __init__(
        self,
        fileId: str = "file123",
        file_metadata: dict[str, Any] | None = None,
        file_list: list[dict[str, Any]] | None = None,
        permissions_resource: DrivePermissionsResource | None = None,
        create_error: Exception | None = None,
        get_error: Exception | None = None,
        get_media_error: Exception | None = None,
        list_error: Exception | None = None,
        update_error: Exception | None = None,
        delete_error: Exception | None = None,
    ):
        """
        Initialize mock files resource.

        Args:
            fileId: ID to return for created files
            file_metadata: Metadata to return for file _operations
            file_list: List of files to return in list operation
            permissions_resource: Mock permissions resource to use
            create_error: Exception to raise on create operation, if any
            get_error: Exception to raise on get operation, if any
            get_media_error: Exception to raise on get_media operation, if any
            list_error: Exception to raise on list operation, if any
            update_error: Exception to raise on update operation, if any
            delete_error: Exception to raise on delete operation, if any
        """
        self._permissions = permissions_resource or MockDrivePermissionsResource()
        self.fileId = fileId
        self.file_metadata = file_metadata or {
            "id": self.fileId,
            "name": "test_file.txt",
            "mimeType": "text/plain",
            "webViewLink": f"https://drive.google.com/file/d/{self.fileId}/view",
            "webContentLink": f"https://drive.google.com/uc?id={self.fileId}",
        }
        self.file_list = file_list or [
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

        # Store error configurations
        self.create_error = create_error
        self.get_error = get_error
        self.get_media_error = get_media_error
        self.list_error = list_error
        self.update_error = update_error
        self.delete_error = delete_error

        # Tracking attributes for assertions
        self.create_call_count = 0
        self.get_call_count = 0
        self.get_media_call_count = 0
        self.list_call_count = 0
        self.update_call_count = 0
        self.delete_call_count = 0

        self.last_create_body: dict[str, object] | None = None
        self.last_create_media_body: Any = None
        self.last_create_fields: str | None = None

        self.last_get_file_id: str | None = None
        self.last_get_fields: str | None = None

        self.last_get_media_file_id: str | None = None

        self.last_list_query: str | None = None
        self.last_list_fields: str | None = None
        self.last_list_page_size: int | None = None

        self.last_update_file_id: str | None = None
        self.last_update_body: dict[str, object] | None = None
        self.last_update_fields: str | None = None

        self.last_delete_file_id: str | None = None

    def create(
        self,
        body: dict[str, object],
        media_body: object | None = None,
        fields: str | None = None,
    ) -> DriveRequest[dict[str, object]]:
        """
        Mock create method for creating a file.

        Args:
            body: File metadata
            media_body: File content
            fields: Fields to include in the response

        Returns:
            A mock request that will return the file data
        """
        self.create_call_count += 1
        self.last_create_body = body
        self.last_create_media_body = media_body
        self.last_create_fields = fields

        request = MockDriveRequest(self.file_metadata, self.create_error)
        request._body = body
        return request

    def get(
        self, fileId: str = None, fields: str | None = None
    ) -> DriveRequest[dict[str, object]]:
        """
        Mock get method for retrieving a file's metadata.

        Args:
            fileId: ID of the file (implementation parameter)
            fields: Fields to include in the response

        Returns:
            A mock request that will return the file metadata
        """
        # Handle parameter name differences

        self.get_call_count += 1
        self.last_get_file_id = fileId
        self.last_get_fields = fields

        return MockDriveRequest(self.file_metadata, self.get_error)

    def get_media(self, fileId: str = None) -> DriveRequest[bytes]:
        """
        Mock get_media method for downloading a file's content.

        Args:
            fileId: ID of the file (implementation parameter)

        Returns:
            A mock request that will return the file content
        """
        # Handle parameter name differences

        self.get_media_call_count += 1
        self.last_get_media_file_id = fileId

        # Default file content as bytes
        file_content = b"Test file content"

        # Directly create a mock request with additional attributes expected during download
        mock_request = MockDriveRequest(file_content, self.get_media_error)

        # Add additional attributes that might be checked during download
        mock_request.mock.fileId = fileId
        mock_request.mock.mime_type = "text/plain"

        return cast(DriveRequest[bytes], mock_request)

    def list(
        self,
        q: str | None = None,
        fields: str | None = None,
        page_size: int | None = None,
    ) -> DriveRequest[dict[str, object]]:
        """
        Mock list method for listing files.

        Args:
            q: Query string
            fields: Fields to include in the response
            page_size: Maximum number of files to return

        Returns:
            A mock request that will return the files list
        """
        self.list_call_count += 1
        self.last_list_query = q
        self.last_list_fields = fields
        self.last_list_page_size = page_size

        # Customize response based on query
        response = {"files": self.file_list}

        return MockDriveRequest(response, self.list_error)

    def update(
        self,
        fileId: str = None,
        body: dict[str, object] = None,
        fields: str | None = None,
    ) -> DriveRequest[dict[str, object]]:
        """
        Mock update method for updating a file's metadata.

        Args:
            fileId: ID of the file (implementation parameter)
            body: Updated metadata
            fields: Fields to include in the response

        Returns:
            A mock request that will return the updated file metadata
        """

        self.update_call_count += 1
        self.last_update_file_id = fileId
        self.last_update_body = body
        self.last_update_fields = fields

        # Merge the update with existing metadata for the response
        updated_metadata = self.file_metadata.copy()
        updated_metadata.update(body or {})  # type: ignore

        request = MockDriveRequest(updated_metadata, self.update_error)
        request._body = body
        return request

    def delete(self, fileId: str = None) -> DriveRequest[None]:
        """
        Mock delete method for deleting a file.

        Args:
            fileId: ID of the file (implementation parameter)

        Returns:
            A mock request for the delete operation
        """
        # Handle parameter name differences

        self.delete_call_count += 1
        self.last_delete_file_id = fileId

        return cast(DriveRequest[None], MockDriveRequest(None, self.delete_error))

    def permissions(self) -> DrivePermissionsResource:
        """
        Get the permissions resource.

        Returns:
            DrivePermissionsResource: The permissions resource.
        """
        return self._permissions
