# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/mocks/services.py
# role: tests
# neighbors: __init__.py, base.py, credentials.py, download.py, media.py, requests.py (+1 more)
# exports: MockDriveService, create_mock_drive_service, create_error_drive_service
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Mock service objects for Google Drive testing.
"""

import logging
from typing import Any

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.protocols import (
    DriveFilesResource,
    DriveService,
)

from .resources import (
    MockDriveFilesResource,
    MockDrivePermissionsResource,
)


class MockDriveService(DriveService):
    """Mock Drive service for testing."""

    def __init__(self, files_resource: DriveFilesResource | None = None):
        """
        Initialize mock Drive service.

        Args:
            files_resource: Mock files resource to use
        """
        self._files = files_resource or MockDriveFilesResource()
        self.files_call_count = 0
        self._initialized = True  # Default to initialized for testing
        self.logger = logging.getLogger("mock_drive_service")

    def files(self) -> DriveFilesResource:
        """
        Get the files resource.

        Returns:
            DriveFilesResource: The files resource.
        """
        self.files_call_count += 1
        return self._files

    def _ensure_initialized(self) -> IntegrationResult | None:
        """
        Check if the service is initialized.

        Returns:
            IntegrationResult: Error result if not initialized, None otherwise.
        """
        if not self._initialized:
            return IntegrationResult.error_result("Service not initialized")
        return None

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Mock implementation of download_file to match the real service.

        Args:
            remote_id: ID of the file to download.
            local_path: Optional local path to save the file.

        Returns:
            IntegrationResult with the local file path.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            # Get metadata using the mock files resource
            try:
                file_metadata = self.files().get(fileId=remote_id).execute()
            except Exception as api_error:
                return IntegrationResult.error_result(
                    f"Failed to get file metadata: {api_error}"
                )

            # Set default download path if not provided
            if not local_path:
                local_path = f"/tmp/{file_metadata.get('name', 'downloaded_file')}"

            # For mock implementation, just return success with the path
            return IntegrationResult.success_result(
                content=local_path,
                message=f"File downloaded successfully to {local_path}",
            )
        except Exception as e:
            return IntegrationResult.error_result(f"Failed to download file: {e}")

    def _resolve_download_path(
        self, file_metadata: dict[str, Any], local_path: str | None
    ) -> str:
        """
        Mock implementation of _resolve_download_path to match the real service.

        Args:
            file_metadata: File metadata from Google Drive.
            local_path: Optional local path to save the file.

        Returns:
            str: The resolved download path.
        """
        file_name = file_metadata.get("name", "downloaded_file")

        if not local_path:
            # Create a fake temp directory path
            return f"/tmp/{file_name}"

        # Simple path resolution for testing
        return f"{local_path}/{file_name}" if "/" in local_path else local_path


def create_mock_drive_service(
    fileId: str = "file123",
    file_metadata: dict[str, Any] | None = None,
    file_list: list[dict[str, Any]] | None = None,
) -> DriveService:
    """
    Create and return a configurable mock Drive service.

    Args:
        fileId: ID to use for created files
        file_metadata: Metadata to return for file _ops
        file_list: List of files to return in list operation

    Returns:
        A mock Drive service object that implements the DriveService protocol
    """
    files_resource = MockDriveFilesResource(
        fileId=fileId,
        file_metadata=file_metadata
        or {
            "id": fileId,
            "name": "test_file.txt",
            "mimeType": "text/plain",
            "webViewLink": f"https://drive.google.com/file/d/{fileId}/view",
            "webContentLink": f"https://drive.google.com/uc?id={fileId}",
        },
        file_list=file_list,
    )
    return MockDriveService(files_resource)


def create_error_drive_service(
    create_error: Exception | None = None,
    get_error: Exception | None = None,
    get_media_error: Exception | None = None,
    list_error: Exception | None = None,
    update_error: Exception | None = None,
    delete_error: Exception | None = None,
    permission_error: Exception | None = None,
) -> DriveService:
    """
    Create a Drive service mock that raises configurable exceptions.

    Args:
        create_error: Exception to raise on create operation
        get_error: Exception to raise on get operation
        get_media_error: Exception to raise on get_media operation
        list_error: Exception to raise on list operation
        update_error: Exception to raise on update operation
        delete_error: Exception to raise on delete operation
        permission_error: Exception to raise on permission _ops

    Returns:
        A mock Drive service object that will raise the specified exceptions
    """
    # Use default errors if not provided
    if create_error is None:
        create_error = Exception("API Error: Failed to create file")
    if get_error is None:
        get_error = Exception("API Error: Failed to get file metadata")
    if get_media_error is None:
        get_media_error = Exception("API Error: Failed to download file")
    if list_error is None:
        list_error = Exception("API Error: Failed to list files")
    if update_error is None:
        update_error = Exception("API Error: Failed to update file")
    if delete_error is None:
        delete_error = Exception("API Error: Failed to delete file")
    if permission_error is None:
        permission_error = Exception("API Error: Failed to set permissions")

    # Create permissions resource with error
    permissions_resource = MockDrivePermissionsResource(error=permission_error)

    # Create files resource with all errors configured
    files_resource = MockDriveFilesResource(
        permissions_resource=permissions_resource,
        create_error=create_error,
        get_error=get_error,
        get_media_error=get_media_error,
        list_error=list_error,
        update_error=update_error,
        delete_error=delete_error,
    )

    return MockDriveService(files_resource)
