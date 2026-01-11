# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive_service_upload.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive.py, test_drive_models.py, test_drive_service_delete.py, test_drive_service_download.py (+6 more)
# exports: TestGoogleDriveServiceUpload
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""
Tests for Google Drive service upload _ops.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.service import GoogleDriveService
from quack_core.core.errors import QuackApiError


class TestGoogleDriveServiceUpload:
    """Tests for the GoogleDriveService upload _ops."""

    @patch(
        "quack_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch.object(GoogleDriveService, "_initialize_config")
    def test_upload_file(
        self, mock_init_config: MagicMock, mock_verify: MagicMock, tmp_path: Path
    ) -> None:
        """Test uploading a file."""
        # Bypass verification
        mock_verify.return_value = None

        # Mock configuration
        mock_init_config.return_value = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
            "shared_folder_id": "shared_folder",
        }

        service = GoogleDriveService(shared_folder_id="shared_folder")
        service._initialized = True

        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Mock file info
        file_info_result = MagicMock()
        file_info_result.success = True
        file_info_result.exists = True

        # Mock file content
        file_content_result = MagicMock()
        file_content_result.success = True
        file_content_result.content = b"test content"

        # Test successful upload
        with patch.object(GoogleDriveService, "_resolve_file_details") as mock_resolve:
            mock_resolve.return_value = (
                Path(test_file),  # Return Path object, not string
                "test_file.txt",
                "shared_folder",
                "text/plain",
            )

            # Create a fresh mock for each test case to avoid shared state
            mock_fs_service = MagicMock()
            mock_fs_service.read_binary.return_value = file_content_result

            # Mock the execute_upload method
            mock_execute_upload = MagicMock()
            mock_execute_upload.return_value = {
                "id": "file123",
                "webViewLink": "https://drive.google.com/file/d/file123/view",
            }

            with patch(
                "quack_core.integrations.google.drive.service.standalone", mock_fs_service
            ):
                with patch.object(service, "_execute_upload", mock_execute_upload):
                    with patch.object(
                        service, "set_file_permissions"
                    ) as mock_permissions:
                        mock_permissions.return_value = IntegrationResult(success=True)

                        result = service.upload_file(str(test_file))

                        assert result.success is True
                        assert (
                            result.content
                            == "https://drive.google.com/file/d/file123/view"
                        )
                        mock_execute_upload.assert_called_once()
                        mock_permissions.assert_called_once_with("file123")
                        mock_fs_service.read_binary.assert_called_once_with(
                            Path(test_file)  # Use Path object, not string
                        )

        # Test with file read error
        with patch.object(GoogleDriveService, "_resolve_file_details") as mock_resolve:
            mock_resolve.return_value = (
                Path(test_file),  # Use Path object, not string
                "test_file.txt",
                "shared_folder",
                "text/plain",
            )

            # Create a new mock with error response
            mock_fs_service = MagicMock()
            mock_fs_service.read_binary.return_value.success = False
            mock_fs_service.read_binary.return_value.error = "Read error"

            with patch(
                "quack_core.integrations.google.drive.service.standalone", mock_fs_service
            ):
                result = service.upload_file(str(test_file))

                assert result.success is False
                assert "Read error" in result.error
                mock_fs_service.read_binary.assert_called_once_with(Path(test_file))

        # Test with upload error
        with patch.object(GoogleDriveService, "_resolve_file_details") as mock_resolve:
            mock_resolve.return_value = (
                Path(test_file),  # Use Path object, not string
                "test_file.txt",
                "shared_folder",
                "text/plain",
            )

            # Create new mocks for this test case
            mock_fs_service = MagicMock()
            mock_fs_service.read_binary.return_value = file_content_result

            mock_execute_upload = MagicMock()
            mock_execute_upload.side_effect = QuackApiError(
                "API error", service="drive"
            )

            with patch(
                "quack_core.integrations.google.drive.service.standalone", mock_fs_service
            ):
                with patch.object(service, "_execute_upload", mock_execute_upload):
                    result = service.upload_file(str(test_file))

                    assert result.success is False
                    assert "API error" in result.error
                    mock_resolve.assert_called_once_with(str(test_file), None, None)
                    mock_execute_upload.assert_called_once()

        # Test not initialized
        service._initialized = False
        with patch.object(service, "_ensure_initialized") as mock_ensure:
            mock_ensure.return_value = IntegrationResult(
                success=False,
                error="Not initialized",
            )

            result = service.upload_file(str(test_file))

            assert result.success is False
            assert "Not initialized" in result.error
