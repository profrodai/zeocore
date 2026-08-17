"""
Tests for GoogleDriveService error-handling branches that were previously
uncovered: the ``except ZeoApiError`` / ``except ZeoBaseAuthError`` /
generic ``except Exception`` triads at the bottom of nearly every public
method, ``get_file_info``'s error path, ``_execute_upload``'s
exception-wrapping branch, ``_resolve_download_path``'s temp-dir-creation
branch, and the ``_initialize_config``/``initialize`` edge branches around
config_provider/auth_provider narrowing and config validation.

Per RULING-235's boundary-mock rule: only ``self.drive_service`` (the
googleapiclient SDK boundary) is mocked. ``standalone`` fs functions and
``paths_service`` are exercised for real wherever the test touches them,
using real sandbox-relative files/dirs (matching the discipline already
established in test_drive_service_files.py's
TestGoogleDriveServiceRealPathService).

BUG FOUND, PINNED, NOT FIXED (see final report for the full list): seven
``except ZeoBaseAuthError`` handlers in this file --
service.py:202-204 (``initialize``), 519-521 (``list_files``), 582-584
(``create_folder``), 630-632 (``set_file_permissions``), 679-681
(``get_sharing_link``), 728-730 (``delete_file``), and 907-909
(``upload_file``) -- are structurally unreachable dead code. In every one
of these six public methods, the only Google SDK call is wrapped by an
inner ``except Exception as api_error: raise ZeoApiError(...)`` (or, for
``upload_file``, by ``_execute_upload``'s own identical inner wrapper) --
since ``ZeoBaseAuthError`` IS an ``Exception``, that inner handler always
intercepts it first and converts it to ``ZeoApiError`` before the outer
``except ZeoBaseAuthError`` can ever see it. For ``initialize``, the
outer handler is dead for a different but related reason:
``BaseIntegrationService.initialize()`` (base.py:315-354) has its own
unconditional ``except Exception`` and never re-raises to its caller, so
the ``super().initialize()`` call (service.py:158) can never surface a
ZeoBaseAuthError either. Net effect: authentication failures at the
Drive API boundary are always reported to callers as generic "API error:
..." (or worse, are silently absorbed into the wrong message), never as
the more specific and presumably more actionable "Authentication error:
...". Additionally, ``set_file_permissions`` and ``delete_file`` each have
a SECOND dead handler: their outer ``except Exception`` (633-637 and
731-735 respectively) is unreachable too, because the only statement
outside their inner try/except is a ``return
IntegrationResult.success_result(...)`` call that cannot itself raise.
Each affected test below documents the real observed message. Not fixed
per this stream's charter (no unilateral production fixes).
"""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from zeo_core.core.errors import (
    ZeoApiError,
    ZeoBaseAuthError,
    ZeoIntegrationError,
)
from zeo_core.integrations.google.drive.service import GoogleDriveService


@pytest.fixture
def real_drive_service() -> Generator[GoogleDriveService, None, None]:
    """A GoogleDriveService with only auth/config construction mocked --
    paths_service and standalone are the REAL modules, untouched. Matches
    the fixture already established in
    test_drive_service_files.py::TestGoogleDriveServiceRealPathService.
    """
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


class TestListFilesErrorPaths:
    """Cover list_files' generic Exception branch (522-526); the
    ZeoApiError branch is already exercised in test_drive_service_list.py.

    BUG (pinned, not fixed): list_files' `except ZeoBaseAuthError` at
    service.py:519-521 is DEAD CODE -- see module docstring."""

    def test_list_files_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: service.py:519-521's `except ZeoBaseAuthError`
        handler is unreachable dead code. A ZeoBaseAuthError raised by
        the mocked SDK boundary is caught first by the inner `except
        Exception` (line 496) and converted to ZeoApiError, so the
        outer handler at 519 never fires -- the error message says "API
        error", not "Authentication error", even though the underlying
        cause was an auth failure. Not fixed per this stream's charter
        (no unilateral production fixes) -- reported for a ruling."""
        real_drive_service.drive_service.files.side_effect = ZeoBaseAuthError(
            "Auth failed", service="drive"
        )
        result = real_drive_service.list_files()
        assert result.success is False
        # This is the ACTUAL (buggy) behavior, not the intended one.
        assert result.error is not None
        assert "API error" in result.error
        assert result.error is not None
        assert "Authentication error" not in result.error

    def test_list_files_generic_error_from_malformed_response_item(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """The generic `except Exception` at 522-526 IS reachable: it
        guards the response-processing loop (item["mimeType"] /
        DriveFile.from_api_response), which runs *outside* the inner
        try/except that wraps only the SDK call itself. A malformed API
        response item missing "mimeType" raises a plain KeyError there,
        which is a genuine, not-dead, code path (distinct from the
        ZeoBaseAuthError dead-code bug pinned above)."""
        mock_list = MagicMock()
        real_drive_service.drive_service.files.return_value.list.return_value = (
            mock_list
        )
        mock_list.execute.return_value = {"files": [{"id": "file1", "name": "x"}]}

        result = real_drive_service.list_files()

        assert result.success is False
        assert result.error is not None
        assert "Failed to list files from Google Drive" in result.error


class TestCreateFolderErrorPaths:
    """Cover create_folder's generic Exception branch (585-589); the
    ZeoApiError branch and the perm_result.success is False warning
    branch (570) are exercised here too since they were both in the
    missing-lines list.

    BUG (pinned, not fixed): same dead-code shape as list_files --
    create_folder's `except ZeoBaseAuthError` at service.py:582-584 is
    unreachable. The only SDK call in the body is wrapped by an inner
    `except Exception -> raise ZeoApiError` (service.py:559-565), so a
    ZeoBaseAuthError raised at the boundary is always reported as "API
    error", never "Authentication error"."""

    def test_create_folder_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring."""
        real_drive_service.drive_service.files.side_effect = ZeoBaseAuthError(
            "Auth failed", service="drive"
        )
        result = real_drive_service.create_folder("New Folder")
        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error
        assert result.error is not None
        assert "Authentication error" not in result.error

    def test_create_folder_generic_error_from_malformed_response(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """The generic `except Exception` at 585-589 IS reachable:
        `folder["id"]` (service.py:567 and 574-576) runs outside the inner
        try/except that wraps only the SDK create() call itself. An API
        response missing "id" raises a plain KeyError there."""
        mock_create = MagicMock()
        real_drive_service.drive_service.files.return_value.create.return_value = (
            mock_create
        )
        mock_create.execute.return_value = {"webViewLink": "https://example.com"}

        result = real_drive_service.create_folder("New Folder")

        assert result.success is False
        assert result.error is not None
        assert "Failed to create folder in Google Drive" in result.error

    def test_create_folder_permission_failure_logs_warning(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """When public_sharing defaults True but set_file_permissions fails,
        create_folder still succeeds and logs a warning (line 570)."""
        mock_create = MagicMock()
        real_drive_service.drive_service.files.return_value.create.return_value = (
            mock_create
        )
        mock_create.execute.return_value = {
            "id": "new_folder",
            "webViewLink": "https://drive.google.com/drive/folders/new_folder",
        }
        with patch.object(
            real_drive_service, "set_file_permissions"
        ) as mock_permissions:
            from zeo_core.integrations.core.results import IntegrationResult

            mock_permissions.return_value = IntegrationResult.error_result(
                "permission denied"
            )
            result = real_drive_service.create_folder("New Folder")

        assert result.success is True
        assert result.content == "new_folder"
        mock_permissions.assert_called_once_with("new_folder")


class TestSetFilePermissionsErrorPaths:
    """BUG (pinned, not fixed): set_file_permissions has TWO dead exception
    handlers, not just one. Its only SDK call is wrapped by an inner
    `except Exception -> raise ZeoApiError` (service.py:615-621), and the
    only statement outside that inner try is
    `return IntegrationResult.success_result(...)` (line 623-625), which
    cannot itself raise under normal operation. So neither the outer
    `except ZeoBaseAuthError` (630-632) NOR the outer `except Exception`
    (633-637) is reachable through any legitimate call path -- both tests
    below deliberately still hit the (already covered elsewhere) `except
    ZeoApiError` handler at 627-629, documenting that this is where
    every SDK-boundary exception actually lands, contrary to what the
    dead handlers' presence implies."""

    def test_set_file_permissions_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring."""
        real_drive_service.drive_service.permissions.side_effect = (
            ZeoBaseAuthError("Auth failed", service="drive")
        )
        result = real_drive_service.set_file_permissions("file123")
        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error
        assert result.error is not None
        assert "Authentication error" not in result.error

    def test_set_file_permissions_error_is_reported_as_api_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """A generic exception raised at the SDK boundary is, like the
        ZeoBaseAuthError case above, converted to ZeoApiError by the
        inner wrapper and reported as "API error" -- there is no code path
        left in the method body, outside that inner try, capable of
        raising a plain exception the generic `except Exception` at
        633-637 could actually catch."""
        real_drive_service.drive_service.permissions.side_effect = ValueError("boom")
        result = real_drive_service.set_file_permissions("file123")
        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error


class TestGetSharingLinkErrorPaths:
    """Cover get_sharing_link's generic Exception branch (682-686).

    BUG (pinned, not fixed): same dead-code shape -- get_sharing_link's
    `except ZeoBaseAuthError` at service.py:679-681 is unreachable behind
    its own inner `except Exception -> raise ZeoApiError`
    (service.py:659-665)."""

    def test_get_sharing_link_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring. Note the message here is
        prefixed twice: get_sharing_link's inner wrap already says
        "Failed to get file metadata from Google Drive: ..." and the outer
        `except ZeoApiError` handler (not the dead auth handler)
        prefixes "API error: " onto that."""
        real_drive_service.drive_service.files.side_effect = ZeoBaseAuthError(
            "Auth failed", service="drive"
        )
        result = real_drive_service.get_sharing_link("file123")
        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error
        assert result.error is not None
        assert "Authentication error" not in result.error

    def test_get_sharing_link_generic_error_from_malformed_response(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """The generic `except Exception` at 682-686 IS reachable: the
        `link = file_metadata.get(...)` computation (service.py:667-671)
        runs outside the inner try/except that wraps only the SDK get()
        call itself. A response that isn't a dict (e.g. None) raises a
        plain AttributeError there."""
        mock_get = MagicMock()
        real_drive_service.drive_service.files.return_value.get.return_value = (
            mock_get
        )
        mock_get.execute.return_value = None

        result = real_drive_service.get_sharing_link("file123")

        assert result.success is False
        assert result.error is not None
        assert "Failed to get sharing link from Google Drive" in result.error


class TestDeleteFileErrorPaths:
    """BUG (pinned, not fixed): same as set_file_permissions above --
    delete_file has TWO dead exception handlers. Its only SDK calls are
    wrapped by an inner `except Exception -> raise ZeoApiError`
    (service.py:712-719), and the only statement outside that inner try is
    `return IntegrationResult.success_result(...)` (line 721-723), which
    cannot itself raise. So neither the outer `except ZeoBaseAuthError`
    (728-730) NOR the outer `except Exception` (731-735) is reachable --
    both tests below hit the (already covered elsewhere) `except
    ZeoApiError` handler at 725-727 instead."""

    def test_delete_file_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring."""
        real_drive_service.drive_service.files.side_effect = ZeoBaseAuthError(
            "Auth failed", service="drive"
        )
        result = real_drive_service.delete_file("file123")
        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error
        assert result.error is not None
        assert "Authentication error" not in result.error

    def test_delete_file_error_is_reported_as_api_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """A generic exception raised at the SDK boundary is, like the
        ZeoBaseAuthError case above, converted to ZeoApiError by the
        inner wrapper and reported as "API error"."""
        real_drive_service.drive_service.files.side_effect = ValueError("boom")
        result = real_drive_service.delete_file("file123")
        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error


class TestUploadFileErrorPaths:
    """Cover upload_file's generic Exception branch (910-914), using a
    real on-disk file resolved through the real
    _resolve_file_details/PathService.

    BUG (pinned, not fixed): same dead-code shape as the other five
    methods above -- upload_file's `except ZeoBaseAuthError` at
    service.py:907-909 is unreachable. The only SDK call
    (files().create().execute(), reached via _execute_upload) is wrapped
    by _execute_upload's OWN inner `except Exception -> raise
    ZeoApiError` (service.py:374-380), so a ZeoBaseAuthError raised at
    that boundary is always reported as "API error", never "Authentication
    error"."""

    def test_upload_file_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring. Raises ZeoBaseAuthError from
        the real SDK boundary (drive_service.files().create().execute()),
        not by bypassing _execute_upload's own wrapping."""
        rel_name = "coverage90_upload_auth_error_probe.txt"
        real_file = Path(rel_name)
        real_file.write_text("probe content")
        try:
            mock_execute = (
                real_drive_service.drive_service.files.return_value
                .create.return_value.execute
            )
            mock_execute.side_effect = ZeoBaseAuthError(
                "Auth failed", service="drive"
            )
            result = real_drive_service.upload_file(rel_name)
            assert result.success is False
            assert result.error is not None
            assert "API error" in result.error
            assert result.error is not None
            assert "Authentication error" not in result.error
        finally:
            real_file.unlink(missing_ok=True)

    def test_upload_file_generic_error_from_malformed_response(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """The generic `except Exception` at 910-914 IS reachable:
        _apply_public_sharing's `file["id"]` access (service.py:848), and
        the `link = file.get(...)` computation (service.py:894-897), both
        run outside _execute_upload's own inner try/except. A successful
        API response missing "id" raises a plain KeyError there."""
        rel_name = "coverage90_upload_generic_error_probe.txt"
        real_file = Path(rel_name)
        real_file.write_text("probe content")
        try:
            mock_execute = (
                real_drive_service.drive_service.files.return_value
                .create.return_value.execute
            )
            mock_execute.return_value = {
                "webViewLink": "https://example.com"
            }
            result = real_drive_service.upload_file(rel_name)
            assert result.success is False
            assert result.error is not None
            assert "Failed to upload file to Google Drive" in result.error
        finally:
            real_file.unlink(missing_ok=True)


class TestExecuteUploadErrorWrapping:
    """Cover _execute_upload's own except Exception -> ZeoApiError wrap
    (lines 363-375), calling the real method directly against a mocked
    drive_service boundary."""

    def test_execute_upload_wraps_api_exception(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        mock_execute = (
            real_drive_service.drive_service.files.return_value
            .create.return_value.execute
        )
        mock_execute.side_effect = RuntimeError(
            "network exploded"
        )

        with pytest.raises(ZeoApiError, match="Failed to upload file"):
            real_drive_service._execute_upload(
                {"name": "f.txt"}, media=MagicMock()
            )

    def test_execute_upload_success(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        mock_execute = (
            real_drive_service.drive_service.files.return_value
            .create.return_value.execute
        )
        mock_execute.return_value = {
            "id": "abc123",
            "webViewLink": "https://drive.google.com/file/d/abc123/view",
            "webContentLink": "https://drive.google.com/uc?id=abc123",
        }

        file = real_drive_service._execute_upload({"name": "f.txt"}, media=MagicMock())
        assert file["id"] == "abc123"


class TestGetFileInfo:
    """get_file_info's entire body -- including its error path -- was
    uncovered (lines 750-772)."""

    def test_get_file_info_success_default_fields(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        expected_metadata = {
            "id": "file123",
            "name": "test.txt",
            "mimeType": "text/plain",
        }
        mock_execute = (
            real_drive_service.drive_service.files.return_value
            .get.return_value.execute
        )
        mock_execute.return_value = expected_metadata

        result = real_drive_service.get_file_info("file123")

        assert result.success is True
        assert result.content == expected_metadata
        real_drive_service.drive_service.files.return_value.get.assert_called_once_with(
            fileId="file123",
            fields=(
                "id,name,mimeType,parents,webViewLink,webContentLink,"
                "size,createdTime,modifiedTime,shared,trashed"
            ),
        )

    def test_get_file_info_success_custom_fields(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        mock_execute = (
            real_drive_service.drive_service.files.return_value
            .get.return_value.execute
        )
        mock_execute.return_value = {
            "id": "file123"
        }

        result = real_drive_service.get_file_info("file123", fields="id")

        assert result.success is True
        real_drive_service.drive_service.files.return_value.get.assert_called_once_with(
            fileId="file123", fields="id"
        )

    def test_get_file_info_not_initialized(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        real_drive_service._initialized = False
        with patch.object(real_drive_service, "initialize") as mock_init:
            from zeo_core.integrations.core.results import IntegrationResult

            mock_init.return_value = IntegrationResult.error_result(
                "Not initialized"
            )
            result = real_drive_service.get_file_info("file123")
        assert result.success is False
        assert result.error is not None
        assert "Not initialized" in result.error

    def test_get_file_info_error(self, real_drive_service: GoogleDriveService) -> None:
        mock_execute = (
            real_drive_service.drive_service.files.return_value
            .get.return_value.execute
        )
        mock_execute.side_effect = RuntimeError(
            "network exploded"
        )

        result = real_drive_service.get_file_info("file123")

        assert result.success is False
        assert result.error is not None
        assert "Failed to retrieve file metadata" in result.error


class TestResolveDownloadPathTempDir:
    """_resolve_download_path's local_path=None branch (lines 271-281)
    creates a real temp directory via standalone.create_temp_directory and
    joins the file name onto it -- exercised for real, no mocking of
    standalone, per RULING-235."""

    def test_resolve_download_path_creates_temp_dir_when_local_path_none(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        result = real_drive_service._resolve_download_path(
            {"name": "downloaded_probe.txt"}, None
        )

        assert isinstance(result, str)
        assert result.endswith("downloaded_probe.txt")
        assert "PathResult" not in result
        assert "DataResult" not in result
        # The temp dir should be a real, existing directory (created by
        # standalone.create_temp_directory), distinct from the joined file
        # path itself which does not yet exist.
        parent = Path(result).parent
        assert parent.exists()
        assert parent.is_dir()

        # Clean up the real temp dir created by the production code.
        parent.rmdir()

    def test_resolve_download_path_default_file_name(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """file_metadata with no "name" key falls back to
        "downloaded_file" (line 267)."""
        result = real_drive_service._resolve_download_path({}, None)

        assert result.endswith("downloaded_file")
        Path(result).parent.rmdir()

    def test_resolve_download_path_existing_file_returned_as_is(
        self, real_drive_service: GoogleDriveService, tmp_path: Path
    ) -> None:
        """Line 315: when local_path resolves to an EXISTING FILE (not a
        directory), the path is returned as-is rather than having the
        Drive filename joined onto it."""
        rel_name = "coverage90_resolve_download_existing_file_probe.txt"
        real_file = Path(rel_name)
        real_file.write_text("already exists")
        try:
            result = real_drive_service._resolve_download_path(
                {"name": "downloaded.txt"}, rel_name
            )
            assert result == str(Path(rel_name).resolve()) or Path(
                result
            ).name == rel_name
        finally:
            real_file.unlink(missing_ok=True)


class TestInitializeConfigEdgeBranches:
    """_initialize_config's config_provider-is-None narrowing (127),
    default-config-invalid raise (135), and the per-field override lines
    when a config file loads successfully (143, 145, 147)."""

    def test_initialize_config_raises_when_config_provider_none(self) -> None:
        """Line 127: if self.config_provider is None when
        _initialize_config runs (never true in practice for the concrete
        class, but the guard exists and must be exercised), it raises
        ZeoIntegrationError rather than crashing with AttributeError."""
        with patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ):
            service = GoogleDriveService.__new__(GoogleDriveService)
            service.config_provider = None
            service.config_path = None

            with pytest.raises(
                ZeoIntegrationError, match="no config_provider configured"
            ):
                service._initialize_config(None, None, None)

    def test_initialize_config_raises_when_default_config_invalid(self) -> None:
        """Line 135: config load fails AND the default config itself fails
        validate_config -- must raise ZeoIntegrationError rather than
        silently returning an invalid default."""
        with patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load, patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider."
            "validate_config"
        ) as mock_validate:
            from zeo_core.integrations.core.results import ConfigResult

            mock_load.return_value = ConfigResult(success=False, content=None)
            mock_validate.return_value = False

            with patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                with pytest.raises(
                    ZeoIntegrationError,
                    match="default configuration is invalid",
                ):
                    GoogleDriveService()

    def test_initialize_config_overrides_loaded_config_fields(self) -> None:
        """Lines 143/145/147: when a config file loads successfully, each
        of the three explicit override params (client_secrets_file,
        credentials_file, shared_folder_id) individually overrides the
        corresponding loaded-config field. Only shared_folder_id is passed
        alongside the constructor call -- passing BOTH client_secrets_file
        and credentials_file together trips the early-return short-circuit
        at service.py:112-117 (`if client_secrets_file and
        credentials_file: return {...}`), which bypasses load_config
        entirely and would never reach lines 141-147 at all."""
        with patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load:
            from zeo_core.integrations.core.results import ConfigResult

            mock_load.return_value = ConfigResult(
                success=True,
                content={
                    "client_secrets_file": "/loaded/secrets.json",
                    "credentials_file": "/loaded/credentials.json",
                    "shared_folder_id": "loaded_folder",
                },
            )

            with patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                service = GoogleDriveService(
                    shared_folder_id="override_folder",
                    config_path="/path/to/config.yaml",
                )

        # client_secrets_file/credentials_file were NOT passed, so they
        # keep the loaded values (lines 142/144 conditions are False);
        # shared_folder_id WAS passed, so line 147 fires and overrides it.
        assert service.config["client_secrets_file"] == "/loaded/secrets.json"
        assert service.config["credentials_file"] == "/loaded/credentials.json"
        assert service.config["shared_folder_id"] == "override_folder"

    def test_initialize_config_overrides_each_field_independently(self) -> None:
        """Lines 143 and 145 specifically: client_secrets_file and
        credentials_file each override independently when passed one at a
        time (never both, to avoid the early-return short-circuit)."""
        with patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load:
            from zeo_core.integrations.core.results import ConfigResult

            mock_load.return_value = ConfigResult(
                success=True,
                content={
                    "client_secrets_file": "/loaded/secrets.json",
                    "credentials_file": "/loaded/credentials.json",
                },
            )
            with patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                service = GoogleDriveService(
                    client_secrets_file="/override/secrets.json",
                    config_path="/path/to/config.yaml",
                )
        assert service.config["client_secrets_file"] == "/override/secrets.json"
        assert service.config["credentials_file"] == "/loaded/credentials.json"

        with patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load:
            from zeo_core.integrations.core.results import ConfigResult

            mock_load.return_value = ConfigResult(
                success=True,
                content={
                    "client_secrets_file": "/loaded/secrets.json",
                    "credentials_file": "/loaded/credentials.json",
                },
            )
            with patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                service = GoogleDriveService(
                    credentials_file="/override/credentials.json",
                    config_path="/path/to/config.yaml",
                )
        assert service.config["client_secrets_file"] == "/loaded/secrets.json"
        assert service.config["credentials_file"] == "/override/credentials.json"


class TestInitializeEdgeBranches:
    """initialize()'s auth_provider-is-None narrowing (169) and the inner
    get_credentials() ZeoBaseAuthError catch (176-180).

    NOTE on the OUTER `except ZeoBaseAuthError` at service.py:202-204:
    this is DEAD CODE too, same shape as the six sibling bugs pinned
    above, but unreachable for a structurally different reason: it is not
    guarded by an inner `except Exception` wrapper, it is guarded by
    BaseIntegrationService.initialize() (base.py:315-354) itself never
    propagating any exception to its caller -- that method has its own
    unconditional `except Exception` (base.py:350) that catches
    everything and returns an IntegrationResult instead of raising. Since
    `super().initialize()` (service.py:158) is the only statement between
    the outer try and the inner get_credentials() try/except that could
    plausibly raise ZeoBaseAuthError, and it structurally cannot, lines
    202-204 have no legitimate trigger -- forcing them would require
    patching BaseIntegrationService.initialize() itself to behave
    differently than it ever does in production, which is not a real
    scenario and is intentionally NOT done here. Left uncovered rather
    than faked; see this file's module docstring / the final report for
    the bug list."""

    def test_initialize_returns_error_when_auth_provider_none(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ):
            service = GoogleDriveService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            service.auth_provider = None

            result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "no auth_provider configured" in result.error

    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    def test_initialize_get_credentials_auth_error(
        self, mock_get_credentials: MagicMock, mock_authenticate: MagicMock
    ) -> None:
        """Lines 176-180: get_credentials() raising ZeoBaseAuthError IS
        legitimately caught by its own dedicated inner try/except (unlike
        the six dead outer handlers pinned above -- this inner one is not
        itself nested inside a broader `except Exception` that would beat
        it to the exception)."""
        with patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ):
            mock_authenticate.return_value.success = True
            mock_get_credentials.side_effect = ZeoBaseAuthError(
                "Bad credentials", service="drive"
            )

            service = GoogleDriveService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Failed to authenticate with Google Drive" in result.error
        assert result.error is not None
        assert "Bad credentials" in result.error


class TestResolveFileDetailsErrorPaths:
    """_resolve_file_details' filename-fallback branch (line 244), using
    the real PathService/standalone, no mocking of zeo_core internals,
    per RULING-235.

    NOTE: line 231 (`if not path_obj_result.success or ...: raise
    ZeoIntegrationError("Failed to resolve path: ...")`) is not
    exercised here. The real PathService.resolve_project_path is lenient
    -- confirmed live this session -- it successfully resolves even
    directory-traversal-style inputs (`../../../etc/...`) and non-string
    inputs (None, ints, bytes) by joining them onto the project root
    rather than failing, so there is no real input that makes it return
    success=False. Forcing that branch would require mocking
    `paths_service`/`PathService` directly, which RULING-235 forbids as a
    zeo_core internal, not an SDK/network boundary -- so this line is
    left uncovered rather than faked."""

    @pytest.fixture
    def service(self) -> Generator[GoogleDriveService, None, None]:
        with patch.object(GoogleDriveService, "_initialize_config") as mock_init:
            mock_init.return_value = {
                "client_secrets_file": "/fake/test/dir/mock_secrets.json",
                "credentials_file": "/fake/test/dir/mock_credentials.json",
            }
            with patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                svc = GoogleDriveService()
                svc.shared_folder_id = "shared_folder"
                svc._initialized = True
                svc.drive_service = MagicMock()
                yield svc

    def test_resolve_file_details_remote_path_used_as_filename(
        self, service: GoogleDriveService
    ) -> None:
        """Line 244 (the if-branch body: `filename = remote_path`): when
        remote_path is given and does not start with "/", it is used
        directly as the filename rather than falling back to the local
        path's last segment."""
        rel_name = "coverage90_resolve_details_filename_probe.txt"
        real_file = Path(rel_name)
        real_file.write_text("probe")
        try:
            path_obj, filename, folder_id, mime_type = service._resolve_file_details(
                rel_name, "custom_remote_name.txt", None
            )
            assert filename == "custom_remote_name.txt"
        finally:
            real_file.unlink(missing_ok=True)

    def test_resolve_file_details_falls_back_to_local_filename(
        self, service: GoogleDriveService
    ) -> None:
        """The else branch (lines 246-248): when remote_path is None, the
        filename falls back to the last path segment of the resolved local
        path."""
        rel_name = "coverage90_resolve_details_fallback_probe.txt"
        real_file = Path(rel_name)
        real_file.write_text("probe")
        try:
            path_obj, filename, folder_id, mime_type = service._resolve_file_details(
                rel_name, None, None
            )
            assert filename == rel_name
        finally:
            real_file.unlink(missing_ok=True)

    def test_resolve_file_details_mime_type_fallback_on_unrecognized_extension(
        self, service: GoogleDriveService
    ) -> None:
        """RULING-247 disease family, twin call site (this file's own
        _resolve_file_details, not operations/upload.py's already-fixed
        resolve_file_details): get_mime_type returns a DataResult, always
        truthy regardless of its own .success/.data fields, so a bare
        `x or fallback` could never reach the fallback branch. This
        exercises the fixed unwrap-then-fallback logic (lines 261-266) on
        BOTH outcomes reachable from this call site: a real successful
        call returns a real MIME type string (already covered by the two
        sibling tests above, both using a real .txt file), and this test
        forces the genuine-unrecognized-extension path so the literal
        "application/octet-stream" fallback line itself is exercised, not
        just the success path.
        """
        rel_name = "coverage90_resolve_details_mime_fallback_probe.unrecognizedext12345"
        real_file = Path(rel_name)
        real_file.write_text("probe")
        try:
            _path_obj, _filename, _folder_id, mime_type = (
                service._resolve_file_details(rel_name, None, None)
            )
            assert mime_type == "application/octet-stream", (
                f"expected the literal fallback string for an unrecognized "
                f"extension, got {mime_type!r} -- the RULING-247-idiom "
                "unwrap-then-fallback fix at this call site appears broken "
                "or reverted"
            )
        finally:
            real_file.unlink(missing_ok=True)


class TestDownloadFileRealPath:
    """download_file's real body (lines 395-461) was entirely uncovered --
    test_drive_service_download.py's existing tests mock
    `download_file` itself wholesale via
    `patch.object(drive_service, "download_file", autospec=True)`, which
    means none of the method's actual logic (metadata fetch, directory
    creation, chunked download loop, disk write, and every error branch)
    ever runs. These tests exercise the real method body: only
    `self.drive_service` (the SDK boundary) and, per the established
    mocks/media.py helper, `googleapiclient.http.MediaIoBaseDownload`
    (also an SDK-boundary object) are mocked -- standalone fs functions
    write to a REAL tmp_path-backed sandbox file.

    BUG FOUND AND FIXED, per RULING-243: service.py:416 used to read
    `parent_dir = standalone.join_path(download_path).parent`, calling
    `.parent` directly on `standalone.join_path(...)`'s return value.
    `join_path` returns a `DataResult` (confirmed live), not a raw `Path`
    -- `DataResult` has `.path` (a `PosixPath`) and `.data` (a str) but no
    `.parent` attribute. This meant download_file's real body ALWAYS
    raised `AttributeError: 'DataResult' object has no attribute
    'parent'` immediately after fetching metadata, for every single call,
    regardless of what the Drive API or the download itself would have
    done -- directory creation (417), the chunked download loop
    (424-441), and the disk write (448-457) were all unreachable, not
    merely untested. Fixed per RULING-243's authorized shape: `join_path`
    was never the right tool here (it exists to JOIN multiple segments;
    this call site passes exactly one, already-complete path) --
    replaced with `coerce_path(download_path).parent`, matching the
    established precedent at `integrations/core/base.py`'s
    `_ensure_credentials_directory`. This is the exact "Result-wrapping
    return value handled as if it were the raw unwrapped value" disease
    shape this stream's charter calls out (RULING-236 through 245's own
    fixes)."""

    def test_download_file_not_initialized(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """Line 396 (_ensure_initialized guard) -- reachable, runs before
        the join_path(...).parent bug."""
        real_drive_service._initialized = False
        with patch.object(real_drive_service, "initialize") as mock_init:
            from zeo_core.integrations.core.results import IntegrationResult

            mock_init.return_value = IntegrationResult.error_result(
                "Not initialized"
            )
            result = real_drive_service.download_file("file123")
        assert result.success is False
        assert result.error is not None
        assert "Not initialized" in result.error

    def test_download_file_metadata_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """Lines 406-408: get() for metadata raising is caught and
        reported directly -- also reachable, runs before the
        join_path(...).parent bug (metadata fetch happens first)."""
        mock_execute = (
            real_drive_service.drive_service.files.return_value
            .get.return_value.execute
        )
        mock_execute.side_effect = RuntimeError(
            "metadata fetch failed"
        )
        result = real_drive_service.download_file("file123")
        assert result.success is False
        assert result.error is not None
        assert "Failed to get file metadata from Google Drive" in result.error

    def test_download_file_join_path_parent_bug_now_fixed_full_success(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """FLIPPED per RULING-243's fix (was: PINS THE BUG). Metadata fetch
        succeeds, directory creation now actually runs (line 417, via the
        real `coerce_path(download_path).parent` -- no mocking of fs
        itself, only the Drive SDK boundary and MediaIoBaseDownload), the
        mocked chunked-download loop completes, and the file is really
        written to disk inside the sandbox. Proves the full real body of
        download_file end to end, not just that no exception fires."""
        mock_files = real_drive_service.drive_service.files.return_value
        mock_files.get.return_value.execute.return_value = {
            "name": "downloaded.txt",
            "mimeType": "text/plain",
        }

        class _FakeStatus:
            def progress(self) -> float:
                return 1.0

        target_dir = Path("coverage90_ruling243_download_dir")
        target = target_dir / "downloaded.txt"

        with patch(
            "googleapiclient.http.MediaIoBaseDownload"
        ) as mock_downloader_cls:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.return_value = (_FakeStatus(), True)
            mock_downloader_cls.return_value = mock_downloader

            try:
                result = real_drive_service.download_file(
                    "file123", str(target)
                )

                assert result.success is True
                assert result.content is not None
                assert Path(result.content).name == "downloaded.txt"
                assert Path(result.content).exists()
                assert Path(result.content).read_bytes() == b""
                mock_files.get_media.assert_called_once_with(fileId="file123")
            finally:
                if target.exists():
                    target.unlink()
                if target_dir.exists():
                    target_dir.rmdir()

    def test_download_file_directory_creation_failure_now_reachable(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """Line 417's create_directory call is now genuinely reachable
        (RULING-243's fix removed the crash that used to block it). Real,
        unmocked standalone.create_directory rejects a target whose parent
        path collides with a real file, sandboxed to a real in-sandbox
        location (tmp_path is outside core/fs's base_dir=Path.cwd()
        sandbox and would trigger a different, unrelated
        ZeoPathOutsideBaseDirError instead of proving this branch)."""
        mock_files = real_drive_service.drive_service.files.return_value
        mock_files.get.return_value.execute.return_value = {
            "name": "downloaded.txt",
            "mimeType": "text/plain",
        }
        blocking_file = Path("coverage90_ruling243_blocking_file_probe.txt")
        blocking_file.write_text("I am a file, not a directory")
        target = blocking_file / "downloaded.txt"

        try:
            result = real_drive_service.download_file("file123", str(target))

            assert result.success is False
            assert result.error is not None
            assert "Failed to create directory" in result.error
            assert "'DataResult' object has no attribute 'parent'" not in (
                result.error
            )
            mock_files.get_media.assert_not_called()
        finally:
            blocking_file.unlink(missing_ok=True)

    def test_download_file_chunked_download_exception_is_reported(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """The chunked-download loop's own `except Exception as
        download_error` branch (also only reachable since RULING-243's
        fix -- metadata fetch and real directory creation both now
        succeed and run first). MediaIoBaseDownload.next_chunk raising is
        caught and reported without ever reaching the disk write."""
        mock_files = real_drive_service.drive_service.files.return_value
        mock_files.get.return_value.execute.return_value = {
            "name": "downloaded.txt",
            "mimeType": "text/plain",
        }
        target_dir = Path("coverage90_ruling243_download_exc_dir")
        target = target_dir / "downloaded.txt"

        with patch(
            "googleapiclient.http.MediaIoBaseDownload"
        ) as mock_downloader_cls:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.side_effect = RuntimeError(
                "chunk transfer failed"
            )
            mock_downloader_cls.return_value = mock_downloader

            try:
                result = real_drive_service.download_file(
                    "file123", str(target)
                )

                assert result.success is False
                assert result.error is not None
                assert "Failed to download file from Google Drive" in (
                    result.error
                )
                assert "chunk transfer failed" in result.error
                assert not target.exists()
            finally:
                if target_dir.exists():
                    target_dir.rmdir()

    def test_download_file_write_failure_is_reported(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """The `write_result.success is False` branch (also only
        reachable since RULING-243's fix). Real directory creation and a
        mocked-successful chunked download both complete; only the final
        standalone.write_binary call is made to fail, isolating this
        branch from the two upstream ones already covered above."""
        mock_files = real_drive_service.drive_service.files.return_value
        mock_files.get.return_value.execute.return_value = {
            "name": "downloaded.txt",
            "mimeType": "text/plain",
        }

        class _FakeStatus:
            def progress(self) -> float:
                return 1.0

        target_dir = Path("coverage90_ruling243_write_fail_dir")
        target = target_dir / "downloaded.txt"

        with (
            patch(
                "googleapiclient.http.MediaIoBaseDownload"
            ) as mock_downloader_cls,
            patch(
                "zeo_core.integrations.google.drive.service.standalone.write_binary"
            ) as mock_write,
        ):
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.return_value = (_FakeStatus(), True)
            mock_downloader_cls.return_value = mock_downloader
            mock_write.return_value = MagicMock(
                success=False, error="disk quota exceeded"
            )

            try:
                result = real_drive_service.download_file(
                    "file123", str(target)
                )

                assert result.success is False
                assert result.error is not None
                assert "Failed to write file: disk quota exceeded" in (
                    result.error
                )
                assert not target.exists()
            finally:
                if target_dir.exists():
                    target_dir.rmdir()

    def test_download_file_outer_exception_handler_is_reached_on_unexpected_raise(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """The method's OUTER `except Exception as e` (467-471) is
        distinct from the inner download-loop handler (445-449) -- it
        wraps the whole try body, including the final
        standalone.write_binary call and success-result construction, and
        is only reachable for a failure NONE of the inner handlers catch
        (metadata fetch has its own inner try/except; the download loop
        has its own). Forcing write_binary itself to raise (rather than
        return a failed result, which is the OTHER, already-covered
        write-failure branch) lands here specifically."""
        mock_files = real_drive_service.drive_service.files.return_value
        mock_files.get.return_value.execute.return_value = {
            "name": "downloaded.txt",
            "mimeType": "text/plain",
        }

        class _FakeStatus:
            def progress(self) -> float:
                return 1.0

        target_dir = Path("coverage90_ruling243_outer_exc_dir")
        target = target_dir / "downloaded.txt"

        with (
            patch(
                "googleapiclient.http.MediaIoBaseDownload"
            ) as mock_downloader_cls,
            patch(
                "zeo_core.integrations.google.drive.service.standalone.write_binary"
            ) as mock_write,
        ):
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.return_value = (_FakeStatus(), True)
            mock_downloader_cls.return_value = mock_downloader
            mock_write.side_effect = RuntimeError("unexpected disk error")

            try:
                result = real_drive_service.download_file(
                    "file123", str(target)
                )

                assert result.success is False
                assert result.error is not None
                assert "Failed to download file from Google Drive" in (
                    result.error
                )
                assert "unexpected disk error" in result.error
                assert not target.exists()
            finally:
                if target_dir.exists():
                    target_dir.rmdir()


class TestEnsureInitializedGuards:
    """The `if init_error := self._ensure_initialized(): return
    init_error` guard at the top of list_files (479), create_folder (542),
    set_file_permissions (606), get_sharing_link (650), and delete_file
    (702) -- each method's own early-return branch when the service fails
    to auto-initialize."""

    @pytest.fixture
    def uninitialized_service(self) -> Generator[GoogleDriveService, None, None]:
        with patch.object(GoogleDriveService, "_initialize_config") as mock_init:
            mock_init.return_value = {
                "client_secrets_file": "/fake/test/dir/mock_secrets.json",
                "credentials_file": "/fake/test/dir/mock_credentials.json",
            }
            with patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                svc = GoogleDriveService()
                svc._initialized = False
                with patch.object(svc, "initialize") as mock_service_init:
                    from zeo_core.integrations.core.results import (
                        IntegrationResult,
                    )

                    mock_service_init.return_value = IntegrationResult.error_result(
                        "Not initialized"
                    )
                    yield svc

    def test_list_files_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.list_files()
        assert result.success is False
        assert result.error is not None
        assert "Not initialized" in result.error

    def test_create_folder_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.create_folder("New Folder")
        assert result.success is False
        assert result.error is not None
        assert "Not initialized" in result.error

    def test_set_file_permissions_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.set_file_permissions("file123")
        assert result.success is False
        assert result.error is not None
        assert "Not initialized" in result.error

    def test_get_sharing_link_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.get_sharing_link("file123")
        assert result.success is False
        assert result.error is not None
        assert "Not initialized" in result.error

    def test_delete_file_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.delete_file("file123")
        assert result.success is False
        assert result.error is not None
        assert "Not initialized" in result.error


class TestUploadHelperBranches:
    """_build_upload_metadata's description-included branch (802),
    _apply_public_sharing's permission-failure warning (850), and
    upload_file's own ZeoIntegrationError catch when
    _resolve_file_details raises for a real (nonexistent) file (881-882)."""

    def test_build_upload_metadata_includes_description(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        metadata = real_drive_service._build_upload_metadata(
            "file.txt", "text/plain", "a helpful description", "folder123"
        )
        assert metadata["description"] == "a helpful description"

    def test_apply_public_sharing_logs_warning_on_permission_failure(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        with patch.object(
            real_drive_service, "set_file_permissions"
        ) as mock_permissions:
            mock_permissions.return_value = IntegrationResult.error_result(
                "permission denied"
            )
            # public=None falls back to config default (True), so
            # set_file_permissions is invoked and its failure is logged.
            real_drive_service._apply_public_sharing({"id": "file123"}, None)

        mock_permissions.assert_called_once_with("file123")

    def test_upload_file_resolve_file_details_not_found(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """Lines 881-882: _resolve_file_details raising
        ZeoIntegrationError for a real, genuinely nonexistent file is
        caught directly and turned into an error result, without ever
        reaching the SDK boundary."""
        result = real_drive_service.upload_file(
            "coverage90_upload_nonexistent_probe.txt"
        )
        assert result.success is False
        assert result.error is not None
        assert "File not found" in result.error
        real_drive_service.drive_service.files.assert_not_called()

    def test_upload_file_returns_error_when_file_is_none_despite_no_upload_error(
        self, real_drive_service: GoogleDriveService, tmp_path: Path
    ) -> None:
        """RULING-274 s2 (round 25): _upload_media's (dict, None) /
        (None, IntegrationResult) contract is exhaustive by construction
        (confirmed by reading _upload_media in full, service.py:817-843),
        so the `if file is None` guard right after the `upload_error`
        early-return can never fire in production. Directly force the
        structurally-impossible combination (_upload_media mocked to
        return (None, None)) to exercise the guard's own body -- same
        defensive-branch-testing discipline as
        test_initialize_returns_error_when_auth_provider_none above."""
        test_file = tmp_path / "probe.txt"
        test_file.write_text("probe content")

        with patch.object(GoogleDriveService, "_resolve_file_details") as mock_resolve:
            mock_resolve.return_value = (
                Path(test_file),
                "probe.txt",
                "shared_folder",
                "text/plain",
            )
            with patch.object(
                real_drive_service, "_upload_media", return_value=(None, None)
            ):
                result = real_drive_service.upload_file(str(test_file))

        assert result.success is False
        assert result.error is not None
        assert "no file data" in result.error
