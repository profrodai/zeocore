# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/operations/test_operations_permissions.py
# role: tests
# neighbors: __init__.py, test_operations_download.py, test_operations_folder.py, test_operations_list_files.py, test_operations_upload.py
# exports: TestDriveOperationsPermissions
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""
Tests for Google Drive _ops permissions module.
"""

from unittest.mock import patch

from quack_core.integrations.google.drive.operations import permissions
from quack_core.core.errors import QuackApiError

from tests.test_integrations.google.drive.mocks import (
    MockDriveFilesResource,
    MockDrivePermissionsResource,
    MockDriveService,
    create_error_drive_service,
    create_mock_drive_service,
)


class TestDriveOperationsPermissions:
    """Tests for the Google Drive _ops permissions functions."""

    def test_set_file_permissions(self) -> None:
        """Test setting file permissions."""
        # Create mock drive service
        mock_drive_service = create_mock_drive_service()

        # Mock execute_api_request - make sure to patch the correct module
        # The key is to patch the module's function, which is what's being called in the implementation
        with patch(
            "quack_core.integrations.google.drive.utils.api.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {"id": "perm123"}

            # Test successful permission setting with default parameters
            result = permissions.set_file_permissions(mock_drive_service, "file123")

            assert result.success is True
            assert result.content is True

            # Check that execute_api_request was called correctly
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0]
            assert call_args[1] == "Failed to set permissions in Google Drive"
            assert call_args[2] == "permissions.create"

            # Check that the permission body was constructed correctly
            request = call_args[0]
            body = request._body
            assert body["type"] == "anyone"
            assert body["role"] == "reader"
            assert body["allowFileDiscovery"] is True

            # Verify our mock service was used correctly
            mock_service = mock_drive_service
            assert isinstance(mock_service, MockDriveService)
            assert mock_service.files_call_count == 1

            # Get the files resource and check its methods
            files_resource = mock_service.files()
            assert isinstance(files_resource, MockDriveFilesResource)

            # Get the permissions resource
            permissions_resource = files_resource.permissions()
            assert isinstance(permissions_resource, MockDrivePermissionsResource)
            assert permissions_resource.create_call_count == 1
            assert permissions_resource.last_file_id == "file123"
            assert permissions_resource.last_permission_body["type"] == "anyone"
            assert permissions_resource.last_permission_body["role"] == "reader"

    def test_set_file_permissions_custom(self) -> None:
        """Test setting file permissions with custom parameters."""
        # Create mock drive service
        mock_drive_service = create_mock_drive_service()

        # Mock execute_api_request
        with patch(
            "quack_core.integrations.google.drive.utils.api.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {"id": "perm123"}

            # Test successful permission setting with custom parameters
            result = permissions.set_file_permissions(
                mock_drive_service, "file123", "writer", "user"
            )

            assert result.success is True
            assert result.content is True

            # Check that execute_api_request was called correctly
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0]

            # Check that the permission body was constructed correctly
            request = call_args[0]
            body = request._body
            assert body["type"] == "user"
            assert body["role"] == "writer"
            assert body["allowFileDiscovery"] is True

            # Verify the permission resource received correct parameters
            mock_service = mock_drive_service
            assert isinstance(mock_service, MockDriveService)
            permissions_resource = mock_service.files().permissions()
            assert isinstance(permissions_resource, MockDrivePermissionsResource)
            assert permissions_resource.last_file_id == "file123"
            assert permissions_resource.last_permission_body["type"] == "user"
            assert permissions_resource.last_permission_body["role"] == "writer"

    def test_set_file_permissions_error(self) -> None:
        """Test error handling when setting file permissions."""
        # Create error-raising mock drive service
        mock_drive_service = create_error_drive_service(
            permission_error=QuackApiError(
                "API error", service="Google Drive", api_method="permissions.create"
            )
        )

        # Mock execute_api_request to raise an error
        with patch(
            "quack_core.integrations.google.drive.utils.api.execute_api_request"
        ) as mock_execute:
            mock_execute.side_effect = QuackApiError(
                "API error", service="Google Drive", api_method="permissions.create"
            )

            # Test error handling
            result = permissions.set_file_permissions(mock_drive_service, "file123")

            assert result.success is False
            assert "API error" in result.error

    def test_get_sharing_link(self) -> None:
        """Test getting a sharing link."""
        # Create mock drive service with specific file metadata
        mock_drive_service = create_mock_drive_service(
            file_metadata={
                "id": "file123",
                "name": "Test File",
                "webViewLink": "https://drive.google.com/file/d/file123/view",
                "webContentLink": "https://drive.google.com/uc?id=file123",
            }
        )

        # Mock execute_api_request
        with patch(
            "quack_core.integrations.google.drive.utils.api.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {
                "webViewLink": "https://drive.google.com/file/d/file123/view",
                "webContentLink": "https://drive.google.com/uc?id=file123",
            }

            # Test successful link retrieval
            result = permissions.get_sharing_link(mock_drive_service, "file123")

            assert result.success is True
            assert result.content == "https://drive.google.com/file/d/file123/view"

            # Check that execute_api_request was called correctly
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0]
            assert call_args[1] == "Failed to get file metadata from Google Drive"
            assert call_args[2] == "files.get"

            # Verify our mock was used correctly
            mock_service = mock_drive_service
            assert isinstance(mock_service, MockDriveService)
            assert mock_service.files_call_count == 1

            files_resource = mock_service.files()
            assert isinstance(files_resource, MockDriveFilesResource)
            assert files_resource.get_call_count == 1
            assert files_resource.last_get_file_id == "file123"
            assert files_resource.last_get_fields == "webViewLink, webContentLink"

    def test_get_sharing_link_content_only(self) -> None:
        """Test getting a sharing link when only content link is available."""
        # Create mock drive service with only content link
        mock_drive_service = create_mock_drive_service(
            file_metadata={
                "id": "file123",
                "name": "Test File",
                "webContentLink": "https://drive.google.com/uc?id=file123",
            }
        )

        # Mock execute_api_request
        with patch(
            "quack_core.integrations.google.drive.utils.api.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {
                "webContentLink": "https://drive.google.com/uc?id=file123"
            }

            # Test successful content link retrieval
            result = permissions.get_sharing_link(mock_drive_service, "file123")

            assert result.success is True
            assert result.content == "https://drive.google.com/uc?id=file123"

    def test_get_sharing_link_fallback(self) -> None:
        """Test getting a sharing link with fallback to default URL."""
        # Create mock drive service with no links
        mock_drive_service = create_mock_drive_service(
            file_metadata={"id": "file123", "name": "Test File"}
        )

        # Mock execute_api_request
        with patch(
            "quack_core.integrations.google.drive.utils.api.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {}  # No links in response

            # Test fallback link generation
            result = permissions.get_sharing_link(mock_drive_service, "file123")

            assert result.success is True
            assert result.content == "https://drive.google.com/file/d/file123/view"

    def test_get_sharing_link_error(self) -> None:
        """Test error handling when getting a sharing link."""
        # Create error-raising mock drive service
        mock_drive_service = create_error_drive_service(
            get_error=QuackApiError(
                "API error", service="Google Drive", api_method="files.get"
            )
        )

        # Mock execute_api_request to raise an error
        with patch(
            "quack_core.integrations.google.drive.utils.api.execute_api_request"
        ) as mock_execute:
            mock_execute.side_effect = QuackApiError(
                "API error", service="Google Drive", api_method="files.get"
            )

            # Test error handling
            result = permissions.get_sharing_link(mock_drive_service, "file123")

            assert result.success is False
            assert "API error" in result.error

    def test_custom_permission_handling(self) -> None:
        """Test custom permission scenarios with direct mock configuration."""
        # Create permissions resource with custom behavior
        permissions_resource = MockDrivePermissionsResource(
            permission_id="custom_perm_123"
        )

        # Create files resource with custom permissions
        files_resource = MockDriveFilesResource(
            permissions_resource=permissions_resource
        )

        # Create service with custom resources
        mock_service = MockDriveService(files_resource)

        # Mock execute_api_request
        with patch(
            "quack_core.integrations.google.drive.utils.api.execute_api_request"
        ) as mock_execute:
            mock_execute.return_value = {"id": "custom_perm_123"}

            # Test with a domain-specific permission
            result = permissions.set_file_permissions(
                mock_service,
                "special_file",
                "commenter",
                "domain",
            )

            assert result.success is True

            # Verify custom permissions were set correctly
            assert isinstance(permissions_resource, MockDrivePermissionsResource)
            assert permissions_resource.last_file_id == "special_file"
            assert permissions_resource.last_permission_body["type"] == "domain"
            assert permissions_resource.last_permission_body["role"] == "commenter"
            assert permissions_resource.permission_id == "custom_perm_123"
