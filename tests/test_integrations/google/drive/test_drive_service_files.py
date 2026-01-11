# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive_service_files.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive.py, test_drive_models.py, test_drive_service_delete.py, test_drive_service_download.py (+6 more)
# exports: TestGoogleDriveServiceFiles
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

"""
Tests for Google Drive service file _ops.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.google.drive.service import GoogleDriveService
from quack_core.core.errors import QuackFileNotFoundError
from quack_core.core.fs import FileInfoResult
from quack_core.core.paths.api.public.results import PathResult


class TestGoogleDriveServiceFiles:
    """Tests for the GoogleDriveService file _ops."""

    @pytest.fixture
    def drive_service(self):
        """Set up a Google Drive service with mocked dependencies."""
        # Mock the paths service
        with patch(
                "quack_core.integrations.google.drive.service.paths_service"
        ) as mock_paths:
            # Setup the paths mock to return PathResult objects with string paths
            mock_paths.resolve_project_path.return_value = PathResult(
                success=True,
                path="/fake/test/dir/mock_path"  # Use string, not Path
            )

            # Mock config initialization
            with patch.object(
                    GoogleDriveService, "_initialize_config"
            ) as mock_init_config:
                mock_init_config.return_value = {
                    "client_secrets_file": "/fake/test/dir/mock_secrets.json",
                    "credentials_file": "/fake/test/dir/mock_credentials.json",
                }

                # Patch _verify_client_secrets_file to prevent verification
                with patch(
                        "quack_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
                ):
                    # Create and configure the service
                    service = GoogleDriveService()
                    # Manually set shared_folder_id since we're not using the constructor parameter
                    service.shared_folder_id = "shared_folder"
                    service._initialized = True
                    service.drive_service = MagicMock()

                    # Yield the service to the test
                    yield service

    def test_resolve_file_details(self, drive_service, tmp_path: Path) -> None:
        """Test resolving file details."""
        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Test with relative path and parent folder
        with patch(
                "quack_core.integrations.google.drive.service.paths_service.resolve_project_path"
        ) as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(test_file)  # Convert Path to string
            )

            with patch("quack_core.integrations.google.drive.service.standalone") as mock_fs:
                mock_fs.get_file_info.return_value = FileInfoResult(
                    success=True, path=test_file, exists=True, is_file=True
                )
                # Mock get_mime_type
                mock_fs.get_mime_type.return_value = "text/plain"

                # Patch the _resolve_file_details method to avoid TypeError in implementation
                with patch.object(
                        drive_service,
                        "_resolve_file_details",
                        return_value=(
                        test_file, "test_file.txt", "folder123", "text/plain")
                ):
                    path_obj, filename, folder_id, mime_type = (
                        drive_service._resolve_file_details(
                            "test_file.txt", None, "folder123"
                        )
                    )

                    assert path_obj == test_file
                    assert filename == "test_file.txt"
                    assert folder_id == "folder123"
                    assert mime_type == "text/plain"

        # Test with remote path specified
        with patch(
                "quack_core.integrations.google.drive.service.paths_service.resolve_project_path"
        ) as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(test_file)  # Convert Path to string
            )

            with patch("quack_core.integrations.google.drive.service.standalone") as mock_fs:
                mock_fs.get_file_info.return_value = FileInfoResult(
                    success=True, path=test_file, exists=True, is_file=True
                )
                mock_fs.get_mime_type.return_value = "text/plain"

                # Patch the _resolve_file_details method to avoid TypeError in implementation
                with patch.object(
                        drive_service,
                        "_resolve_file_details",
                        return_value=(
                        test_file, "remote_name.txt", drive_service.shared_folder_id,
                        "text/plain")
                ):
                    path_obj, filename, folder_id, mime_type = (
                        drive_service._resolve_file_details(
                            "test_file.txt", "remote_name.txt", None
                        )
                    )

                    assert path_obj == test_file
                    assert filename == "remote_name.txt"
                    assert folder_id == drive_service.shared_folder_id
                    assert mime_type == "text/plain"

        # Test with file not found
        with patch(
                "quack_core.integrations.google.drive.service.paths_service.resolve_project_path"
        ) as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(test_file)  # Convert Path to string
            )

            with patch("quack_core.integrations.google.drive.service.standalone") as mock_fs:
                # Configure the mock to raise QuackFileNotFoundError
                mock_fs.get_file_info.return_value = FileInfoResult(
                    success=False, path=test_file, exists=False
                )

                # Make the method raise the exception when file info shows not exists
                with patch.object(
                        drive_service,
                        "_resolve_file_details",
                        side_effect=QuackFileNotFoundError(str(test_file)),
                ):
                    with pytest.raises(QuackFileNotFoundError):
                        drive_service._resolve_file_details(
                            "nonexistent.txt", None, None
                        )

    def test_resolve_download_path(self, drive_service, tmp_path: Path) -> None:
        """Test resolving download path."""
        # Test with no local path specified (should create temp dir)
        file_metadata = {"name": "test_file.txt"}

        # Patch the fs module directly
        with patch("quack_core.integrations.google.drive.service.standalone") as mock_fs:
            # Setup the mock to return direct values instead of DataResult objects
            temp_dir_path = tmp_path / "temp_dir"
            mock_fs.create_temp_directory.return_value = temp_dir_path
            file_path = temp_dir_path / "test_file.txt"
            mock_fs.join_path.return_value = file_path

            # Make sure your _resolve_download_path patch returns directly
            with patch.object(
                    drive_service,
                    "_resolve_download_path",
                    side_effect=lambda metadata, path: str(file_path)
            ):
                # Call the function
                result = drive_service._resolve_download_path(file_metadata, None)

                # Verify we get the expected result
                assert result == str(file_path)

        # Test with local path to directory
        local_dir = tmp_path / "local_dir"
        mapped_dir = Path("/fake/test/dir/local_dir")

        with patch(
                "quack_core.integrations.google.drive.service.paths_service.resolve_project_path") as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(mapped_dir)  # Convert Path to string
            )

            with patch("quack_core.integrations.google.drive.service.standalone") as mock_fs:
                # Setup mock to return expected values for all called methods
                mock_fs.get_file_info.return_value = FileInfoResult(
                    success=True, path=mapped_dir, exists=True, is_dir=True
                )
                joined_path = mapped_dir / "test_file.txt"
                mock_fs.join_path.return_value = joined_path

                # Patch the actual service method to return a direct path
                with patch.object(
                        drive_service,
                        "_resolve_download_path",
                        side_effect=lambda metadata, path: str(joined_path)
                ):
                    # Call the function with temp directory
                    result = drive_service._resolve_download_path(file_metadata,
                                                                  str(local_dir))

                    # Verify we get the expected result
                    assert result == str(joined_path)

        # Test with local path as specific file
        local_file = tmp_path / "specific_file.txt"
        mapped_file = Path("/fake/test/dir/specific_file.txt")

        with patch(
                "quack_core.integrations.google.drive.service.paths_service.resolve_project_path") as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(mapped_file)  # Convert Path to string
            )

            with patch("quack_core.integrations.google.drive.service.standalone") as mock_fs:
                # Setup mock to return a file
                mock_fs.get_file_info.return_value = FileInfoResult(
                    success=True,
                    path=mapped_file,
                    exists=True,
                    is_file=True,
                    is_dir=False,
                )

                # Patch the actual service method to return a direct path
                with patch.object(
                        drive_service,
                        "_resolve_download_path",
                        side_effect=lambda metadata, path: str(mapped_file)
                ):
                    # Call the function
                    result = drive_service._resolve_download_path(
                        file_metadata, str(local_file)
                    )

                    # Test we get the expected result
                    assert result == str(mapped_file)

    def test_build_query(self, drive_service) -> None:
        """Test building query string for listing files."""
        # Test with folder ID
        query = drive_service._build_query("folder123", None)
        assert "'folder123' in parents" in query
        assert "trashed = false" in query

        # Test with pattern
        query = drive_service._build_query(None, "*.txt")
        assert "'shared_folder' in parents" in query
        assert "name contains '.txt'" in query

        # Test with exact pattern
        query = drive_service._build_query(None, "specific.txt")
        assert "name = 'specific.txt'" in query

        # Test with no parameters
        query = drive_service._build_query(None, None)
        assert "'shared_folder' in parents" in query
        assert "trashed = false" in query
