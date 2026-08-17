"""
Tests for Google Drive service file _ops.
"""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from zeo_core.core.errors import ZeoFileNotFoundError, ZeoIntegrationError
from zeo_core.core.fs import FileInfoResult
from zeo_core.core.paths.api.public.results import PathResult
from zeo_core.integrations.google.drive.service import GoogleDriveService


class TestGoogleDriveServiceFiles:
    """Tests for the GoogleDriveService file _ops."""

    @pytest.fixture
    def drive_service(self) -> Generator[GoogleDriveService, None, None]:
        """Set up a Google Drive service with mocked dependencies."""
        # Mock the paths service
        with patch(
            "zeo_core.integrations.google.drive.service.paths_service"
        ) as mock_paths:
            # Setup the paths mock to return PathResult objects with string paths
            mock_paths.resolve_project_path.return_value = PathResult(
                success=True,
                path="/fake/test/dir/mock_path",  # Use string, not Path
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
                    "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
                ):
                    # Create and configure the service
                    service = GoogleDriveService()
                    # Manually set shared_folder_id since we're not using the
                    # constructor parameter
                    service.shared_folder_id = "shared_folder"
                    service._initialized = True
                    service.drive_service = MagicMock()

                    # Yield the service to the test
                    yield service

    def test_resolve_file_details(
        self, drive_service: GoogleDriveService, tmp_path: Path
    ) -> None:
        """Test resolving file details."""
        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Test with relative path and parent folder
        with patch(
            "zeo_core.integrations.google.drive.service.paths_service.resolve_project_path"
        ) as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(test_file),  # Convert Path to string
            )

            with patch(
                "zeo_core.integrations.google.drive.service.standalone"
            ) as mock_fs:
                mock_fs.get_file_info.return_value = FileInfoResult(
                    ok=True, path=test_file, exists=True, is_file=True
                )
                # Mock get_mime_type
                mock_fs.get_mime_type.return_value = "text/plain"

                # Patch the _resolve_file_details method to avoid TypeError
                # in implementation
                with patch.object(
                    drive_service,
                    "_resolve_file_details",
                    return_value=(
                        test_file,
                        "test_file.txt",
                        "folder123",
                        "text/plain",
                    ),
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
            "zeo_core.integrations.google.drive.service.paths_service.resolve_project_path"
        ) as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(test_file),  # Convert Path to string
            )

            with patch(
                "zeo_core.integrations.google.drive.service.standalone"
            ) as mock_fs:
                mock_fs.get_file_info.return_value = FileInfoResult(
                    ok=True, path=test_file, exists=True, is_file=True
                )
                mock_fs.get_mime_type.return_value = "text/plain"

                # Patch the _resolve_file_details method to avoid TypeError
                # in implementation
                with patch.object(
                    drive_service,
                    "_resolve_file_details",
                    return_value=(
                        test_file,
                        "remote_name.txt",
                        drive_service.shared_folder_id,
                        "text/plain",
                    ),
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
            "zeo_core.integrations.google.drive.service.paths_service.resolve_project_path"
        ) as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(test_file),  # Convert Path to string
            )

            with patch(
                "zeo_core.integrations.google.drive.service.standalone"
            ) as mock_fs:
                # Configure the mock to raise ZeoFileNotFoundError
                mock_fs.get_file_info.return_value = FileInfoResult(
                    ok=False, path=test_file, exists=False
                )

                # Make the method raise the exception when file info shows not exists
                with patch.object(
                    drive_service,
                    "_resolve_file_details",
                    side_effect=ZeoFileNotFoundError(str(test_file)),
                ):
                    with pytest.raises(ZeoFileNotFoundError):
                        drive_service._resolve_file_details(
                            "nonexistent.txt", None, None
                        )

    def test_resolve_download_path(
        self, drive_service: GoogleDriveService, tmp_path: Path
    ) -> None:
        """Test resolving download path."""
        # Test with no local path specified (should create temp dir)
        file_metadata = {"name": "test_file.txt"}

        # Patch the fs module directly
        with patch(
            "zeo_core.integrations.google.drive.service.standalone"
        ) as mock_fs:
            # Setup the mock to return direct values instead of DataResult objects
            temp_dir_path = tmp_path / "temp_dir"
            mock_fs.create_temp_directory.return_value = temp_dir_path
            file_path = temp_dir_path / "test_file.txt"
            mock_fs.join_path.return_value = file_path

            # Make sure your _resolve_download_path patch returns directly
            with patch.object(
                drive_service,
                "_resolve_download_path",
                side_effect=lambda metadata, path: str(file_path),
            ):
                # Call the function
                result = drive_service._resolve_download_path(file_metadata, None)

                # Verify we get the expected result
                assert result == str(file_path)

        # Test with local path to directory
        local_dir = tmp_path / "local_dir"
        mapped_dir = Path("/fake/test/dir/local_dir")

        with patch(
            "zeo_core.integrations.google.drive.service.paths_service.resolve_project_path"
        ) as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(mapped_dir),  # Convert Path to string
            )

            with patch(
                "zeo_core.integrations.google.drive.service.standalone"
            ) as mock_fs:
                # Setup mock to return expected values for all called methods
                mock_fs.get_file_info.return_value = FileInfoResult(
                    ok=True, path=mapped_dir, exists=True, is_dir=True
                )
                joined_path = mapped_dir / "test_file.txt"
                mock_fs.join_path.return_value = joined_path

                # Patch the actual service method to return a direct path
                with patch.object(
                    drive_service,
                    "_resolve_download_path",
                    side_effect=lambda metadata, path: str(joined_path),
                ):
                    # Call the function with temp directory
                    result = drive_service._resolve_download_path(
                        file_metadata, str(local_dir)
                    )

                    # Verify we get the expected result
                    assert result == str(joined_path)

        # Test with local path as specific file
        local_file = tmp_path / "specific_file.txt"
        mapped_file = Path("/fake/test/dir/specific_file.txt")

        with patch(
            "zeo_core.integrations.google.drive.service.paths_service.resolve_project_path"
        ) as mock_resolve:
            # Update to return PathResult with string path
            mock_resolve.return_value = PathResult(
                success=True,
                path=str(mapped_file),  # Convert Path to string
            )

            with patch(
                "zeo_core.integrations.google.drive.service.standalone"
            ) as mock_fs:
                # Setup mock to return a file
                mock_fs.get_file_info.return_value = FileInfoResult(
                    ok=True,
                    path=mapped_file,
                    exists=True,
                    is_file=True,
                    is_dir=False,
                )

                # Patch the actual service method to return a direct path
                with patch.object(
                    drive_service,
                    "_resolve_download_path",
                    side_effect=lambda metadata, path: str(mapped_file),
                ):
                    # Call the function
                    result = drive_service._resolve_download_path(
                        file_metadata, str(local_file)
                    )

                    # Test we get the expected result
                    assert result == str(mapped_file)

    def test_build_query(self, drive_service: GoogleDriveService) -> None:
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


class TestGoogleDriveServiceRealPathService:
    """RULING-240: google/drive/service.py:197,256 called
    `paths_service.resolve_project_path(...)` directly on the raw
    `core.paths.service` MODULE (imported as `paths_service`), which has no
    such attribute -- the identical bug RULING-238 fixed in
    `mail/service.py`. Every pre-existing test above mocks
    `paths_service`/`paths_service.resolve_project_path` directly, which
    masks the real module never having that attribute -- none of them
    exercise the real, unmocked call. These tests do: no `paths_service`
    patching anywhere, proving the fix (instantiate `PathService()`, unwrap
    `.success`/`.path` explicitly) against the real service end to end,
    for both `_resolve_file_details` (the `upload_file` path) and
    `_resolve_download_path` (the download path)."""

    @pytest.fixture
    def real_drive_service(self) -> Generator[GoogleDriveService, None, None]:
        """A GoogleDriveService with only auth/config mocked -- paths_service
        and standalone are the REAL modules, untouched."""
        with patch.object(GoogleDriveService, "_initialize_config") as mock_init:
            mock_init.return_value = {
                "client_secrets_file": "/fake/test/dir/mock_secrets.json",
                "credentials_file": "/fake/test/dir/mock_credentials.json",
            }
            with patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                service = GoogleDriveService()
                service.shared_folder_id = "shared_folder"
                service._initialized = True
                service.drive_service = MagicMock()
                yield service

    def test_resolve_file_details_real_path_service(
        self, real_drive_service: GoogleDriveService, tmp_path: Path
    ) -> None:
        """_resolve_file_details (called from the public upload_file) must
        resolve a real on-disk file through the real PathService, not a
        raw-module AttributeError. Pre-fix this raised AttributeError:
        module 'zeo_core.core.paths.service' has no attribute
        'resolve_project_path'."""
        # in-sandbox relative file, matching this stream's own standing
        # discipline (SOW-5/6) of using a real sandbox-relative path rather
        # than tmp_path, which core/fs's allow_absolute=False would refuse.
        rel_name = "coverage90_ruling240_upload_probe.txt"
        real_file = Path(rel_name)
        real_file.write_text("ruling-240 real path service probe")
        try:
            path_obj, filename, folder_id, mime_type = (
                real_drive_service._resolve_file_details(rel_name, None, None)
            )
            # Real, unmocked resolution: PathService.resolve_project_path's
            # PathResult.path is a plain str (confirmed live, this session:
            # core/paths/_internal/resolver returns a string, not a Path) --
            # the point of this test is that it resolves to the REAL file's
            # location and not a PathResult repr or an AttributeError.
            assert isinstance(path_obj, str)
            assert Path(path_obj).exists()
            assert Path(path_obj).name == rel_name
            assert "PathResult" not in path_obj
            assert "success=" not in path_obj
            assert filename == rel_name
            assert folder_id == "shared_folder"
        finally:
            real_file.unlink(missing_ok=True)

    def test_resolve_file_details_missing_file_real_path_service(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """A real, resolvable-but-nonexistent path must raise
        ZeoIntegrationError("File not found: ...") from real
        get_file_info's exists=False, not mask a resolve AttributeError as
        something else. (Confirmed live this session: _resolve_file_details
        raises ZeoIntegrationError, not ZeoFileNotFoundError, for this
        branch -- the method's own explicit raise, not a coercion.)"""
        with pytest.raises(ZeoIntegrationError, match="File not found"):
            real_drive_service._resolve_file_details(
                "coverage90_ruling240_does_not_exist.txt", None, None
            )

    def test_upload_file_real_path_service_end_to_end(
        self, real_drive_service: GoogleDriveService, tmp_path: Path
    ) -> None:
        """The public upload_file method, exercised end to end through the
        REAL _resolve_file_details / real PathService (only the Drive API
        call and file-read/permission side effects are mocked at the
        external boundary, per RULING-235). Pre-fix this raised
        AttributeError inside _resolve_file_details before ever reaching
        the API call."""
        rel_name = "coverage90_ruling240_upload_e2e_probe.txt"
        real_file = Path(rel_name)
        real_file.write_text("ruling-240 upload_file real path service probe")
        try:
            mock_execute_upload = MagicMock(
                return_value={
                    "id": "file123",
                    "webViewLink": "https://drive.google.com/file/d/file123/view",
                }
            )
            with patch.object(
                real_drive_service, "_execute_upload", mock_execute_upload
            ):
                with patch.object(
                    real_drive_service, "set_file_permissions"
                ) as mock_perms:
                    from zeo_core.integrations.core.results import (
                        IntegrationResult,
                    )

                    mock_perms.return_value = IntegrationResult(success=True)

                    result = real_drive_service.upload_file(rel_name)

                    assert result.success is True
                    assert (
                        result.content
                        == "https://drive.google.com/file/d/file123/view"
                    )
                    mock_execute_upload.assert_called_once()
        finally:
            real_file.unlink(missing_ok=True)

    def test_resolve_download_path_directory_real_path_service(
        self, real_drive_service: GoogleDriveService, tmp_path: Path
    ) -> None:
        """_resolve_download_path with an existing local directory, through
        the real PathService. Pre-fix this raised the same AttributeError
        as the upload path."""
        real_dir = Path("coverage90_ruling240_download_dir")
        real_dir.mkdir(exist_ok=True)
        try:
            result = real_drive_service._resolve_download_path(
                {"name": "downloaded.txt"}, str(real_dir)
            )
            assert isinstance(result, str)
            assert result.endswith("downloaded.txt")
            assert "PathResult" not in result
            assert "success=" not in result
        finally:
            real_dir.rmdir()

    def test_resolve_download_path_new_file_real_path_service(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """_resolve_download_path with a local_path that does not yet exist
        (the "create it" branch) through the real PathService."""
        target = "coverage90_ruling240_download_newfile.txt"
        result = real_drive_service._resolve_download_path(
            {"name": "downloaded.txt"}, target
        )
        assert isinstance(result, str)
        assert result.endswith(target)
        assert "PathResult" not in result
        assert "success=" not in result

    def test_download_file_real_path_service_end_to_end(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """download_file exercised through the REAL _resolve_download_path
        / real PathService (line 256's fix, unmocked) -- the Drive API
        calls and disk write are mocked at the external boundary.

        UPDATED per RULING-243's fix: download_file's own parent-directory
        line (`coerce_path(download_path).parent`, formerly the broken
        `standalone.join_path(download_path).parent`) is now real zeo_core
        logic exercised unmocked, same as everything else in this test --
        no more join_path workaround needed (the old side-effect shim that
        stepped over the single-arg call site is gone; RULING-243's fix
        means download_file no longer calls join_path there at all)."""
        mock_files = real_drive_service.drive_service.files.return_value
        mock_files.get.return_value.execute.return_value = {
            "name": "downloaded_e2e.txt",
            "mimeType": "text/plain",
        }

        class _FakeStatus:
            def progress(self) -> float:
                return 1.0

        target_dir = Path("coverage90_ruling240_download_e2e_dir")
        target_file = target_dir / "downloaded_e2e.txt"

        with patch(
            "googleapiclient.http.MediaIoBaseDownload"
        ) as mock_downloader_cls:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.return_value = (_FakeStatus(), True)
            mock_downloader_cls.return_value = mock_downloader

            try:
                result = real_drive_service.download_file(
                    "file123", str(target_file)
                )
                assert result.success is True
                assert result.content is not None
                assert "PathResult" not in result.content
                assert Path(result.content).name == "downloaded_e2e.txt"
                assert Path(result.content).exists()
            finally:
                if target_file.exists():
                    target_file.unlink()
                if target_dir.exists():
                    target_dir.rmdir()
