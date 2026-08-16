# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive_service_error_paths.py  # noqa: E501
# === QV-LLM:END ===

"""
Tests for GoogleDriveService error-handling branches that were previously
uncovered: the ``except QuackApiError`` / ``except QuackBaseAuthError`` /
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
``except QuackBaseAuthError`` handlers in this file --
service.py:202-204 (``initialize``), 519-521 (``list_files``), 582-584
(``create_folder``), 630-632 (``set_file_permissions``), 679-681
(``get_sharing_link``), 728-730 (``delete_file``), and 907-909
(``upload_file``) -- are structurally unreachable dead code. In every one
of these six public methods, the only Google SDK call is wrapped by an
inner ``except Exception as api_error: raise QuackApiError(...)`` (or, for
``upload_file``, by ``_execute_upload``'s own identical inner wrapper) --
since ``QuackBaseAuthError`` IS an ``Exception``, that inner handler always
intercepts it first and converts it to ``QuackApiError`` before the outer
``except QuackBaseAuthError`` can ever see it. For ``initialize``, the
outer handler is dead for a different but related reason:
``BaseIntegrationService.initialize()`` (base.py:315-354) has its own
unconditional ``except Exception`` and never re-raises to its caller, so
the ``super().initialize()`` call (service.py:158) can never surface a
QuackBaseAuthError either. Net effect: authentication failures at the
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
from quack_core.core.errors import (
    QuackApiError,
    QuackBaseAuthError,
    QuackIntegrationError,
)
from quack_core.integrations.google.drive.service import GoogleDriveService


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
            "quack_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ):
            service = GoogleDriveService()
            service.shared_folder_id = "shared_folder"
            service._initialized = True
            service.drive_service = MagicMock()
            yield service


class TestListFilesErrorPaths:
    """Cover list_files' generic Exception branch (522-526); the
    QuackApiError branch is already exercised in test_drive_service_list.py.

    BUG (pinned, not fixed): list_files' `except QuackBaseAuthError` at
    service.py:519-521 is DEAD CODE -- see module docstring."""

    def test_list_files_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: service.py:519-521's `except QuackBaseAuthError`
        handler is unreachable dead code. A QuackBaseAuthError raised by
        the mocked SDK boundary is caught first by the inner `except
        Exception` (line 496) and converted to QuackApiError, so the
        outer handler at 519 never fires -- the error message says "API
        error", not "Authentication error", even though the underlying
        cause was an auth failure. Not fixed per this stream's charter
        (no unilateral production fixes) -- reported for a ruling."""
        real_drive_service.drive_service.files.side_effect = QuackBaseAuthError(
            "Auth failed", service="drive"
        )
        result = real_drive_service.list_files()
        assert result.success is False
        # This is the ACTUAL (buggy) behavior, not the intended one.
        assert "API error" in result.error
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
        QuackBaseAuthError dead-code bug pinned above)."""
        mock_list = MagicMock()
        real_drive_service.drive_service.files.return_value.list.return_value = (
            mock_list
        )
        mock_list.execute.return_value = {"files": [{"id": "file1", "name": "x"}]}

        result = real_drive_service.list_files()

        assert result.success is False
        assert "Failed to list files from Google Drive" in result.error


class TestCreateFolderErrorPaths:
    """Cover create_folder's generic Exception branch (585-589); the
    QuackApiError branch and the perm_result.success is False warning
    branch (570) are exercised here too since they were both in the
    missing-lines list.

    BUG (pinned, not fixed): same dead-code shape as list_files --
    create_folder's `except QuackBaseAuthError` at service.py:582-584 is
    unreachable. The only SDK call in the body is wrapped by an inner
    `except Exception -> raise QuackApiError` (service.py:559-565), so a
    QuackBaseAuthError raised at the boundary is always reported as "API
    error", never "Authentication error"."""

    def test_create_folder_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring."""
        real_drive_service.drive_service.files.side_effect = QuackBaseAuthError(
            "Auth failed", service="drive"
        )
        result = real_drive_service.create_folder("New Folder")
        assert result.success is False
        assert "API error" in result.error
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
            from quack_core.integrations.core.results import IntegrationResult

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
    `except Exception -> raise QuackApiError` (service.py:615-621), and the
    only statement outside that inner try is
    `return IntegrationResult.success_result(...)` (line 623-625), which
    cannot itself raise under normal operation. So neither the outer
    `except QuackBaseAuthError` (630-632) NOR the outer `except Exception`
    (633-637) is reachable through any legitimate call path -- both tests
    below deliberately still hit the (already covered elsewhere) `except
    QuackApiError` handler at 627-629, documenting that this is where
    every SDK-boundary exception actually lands, contrary to what the
    dead handlers' presence implies."""

    def test_set_file_permissions_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring."""
        real_drive_service.drive_service.permissions.side_effect = (
            QuackBaseAuthError("Auth failed", service="drive")
        )
        result = real_drive_service.set_file_permissions("file123")
        assert result.success is False
        assert "API error" in result.error
        assert "Authentication error" not in result.error

    def test_set_file_permissions_error_is_reported_as_api_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """A generic exception raised at the SDK boundary is, like the
        QuackBaseAuthError case above, converted to QuackApiError by the
        inner wrapper and reported as "API error" -- there is no code path
        left in the method body, outside that inner try, capable of
        raising a plain exception the generic `except Exception` at
        633-637 could actually catch."""
        real_drive_service.drive_service.permissions.side_effect = ValueError("boom")
        result = real_drive_service.set_file_permissions("file123")
        assert result.success is False
        assert "API error" in result.error


class TestGetSharingLinkErrorPaths:
    """Cover get_sharing_link's generic Exception branch (682-686).

    BUG (pinned, not fixed): same dead-code shape -- get_sharing_link's
    `except QuackBaseAuthError` at service.py:679-681 is unreachable behind
    its own inner `except Exception -> raise QuackApiError`
    (service.py:659-665)."""

    def test_get_sharing_link_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring. Note the message here is
        prefixed twice: get_sharing_link's inner wrap already says
        "Failed to get file metadata from Google Drive: ..." and the outer
        `except QuackApiError` handler (not the dead auth handler)
        prefixes "API error: " onto that."""
        real_drive_service.drive_service.files.side_effect = QuackBaseAuthError(
            "Auth failed", service="drive"
        )
        result = real_drive_service.get_sharing_link("file123")
        assert result.success is False
        assert "API error" in result.error
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
        assert "Failed to get sharing link from Google Drive" in result.error


class TestDeleteFileErrorPaths:
    """BUG (pinned, not fixed): same as set_file_permissions above --
    delete_file has TWO dead exception handlers. Its only SDK calls are
    wrapped by an inner `except Exception -> raise QuackApiError`
    (service.py:712-719), and the only statement outside that inner try is
    `return IntegrationResult.success_result(...)` (line 721-723), which
    cannot itself raise. So neither the outer `except QuackBaseAuthError`
    (728-730) NOR the outer `except Exception` (731-735) is reachable --
    both tests below hit the (already covered elsewhere) `except
    QuackApiError` handler at 725-727 instead."""

    def test_delete_file_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring."""
        real_drive_service.drive_service.files.side_effect = QuackBaseAuthError(
            "Auth failed", service="drive"
        )
        result = real_drive_service.delete_file("file123")
        assert result.success is False
        assert "API error" in result.error
        assert "Authentication error" not in result.error

    def test_delete_file_error_is_reported_as_api_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """A generic exception raised at the SDK boundary is, like the
        QuackBaseAuthError case above, converted to QuackApiError by the
        inner wrapper and reported as "API error"."""
        real_drive_service.drive_service.files.side_effect = ValueError("boom")
        result = real_drive_service.delete_file("file123")
        assert result.success is False
        assert "API error" in result.error


class TestUploadFileErrorPaths:
    """Cover upload_file's generic Exception branch (910-914), using a
    real on-disk file resolved through the real
    _resolve_file_details/PathService.

    BUG (pinned, not fixed): same dead-code shape as the other five
    methods above -- upload_file's `except QuackBaseAuthError` at
    service.py:907-909 is unreachable. The only SDK call
    (files().create().execute(), reached via _execute_upload) is wrapped
    by _execute_upload's OWN inner `except Exception -> raise
    QuackApiError` (service.py:374-380), so a QuackBaseAuthError raised at
    that boundary is always reported as "API error", never "Authentication
    error"."""

    def test_upload_file_auth_error_is_reported_as_api_error_not_auth_error(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS A BUG: see class docstring. Raises QuackBaseAuthError from
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
            mock_execute.side_effect = QuackBaseAuthError(
                "Auth failed", service="drive"
            )
            result = real_drive_service.upload_file(rel_name)
            assert result.success is False
            assert "API error" in result.error
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
            assert "Failed to upload file to Google Drive" in result.error
        finally:
            real_file.unlink(missing_ok=True)


class TestExecuteUploadErrorWrapping:
    """Cover _execute_upload's own except Exception -> QuackApiError wrap
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

        with pytest.raises(QuackApiError, match="Failed to upload file"):
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
            from quack_core.integrations.core.results import IntegrationResult

            mock_init.return_value = IntegrationResult.error_result(
                "Not initialized"
            )
            result = real_drive_service.get_file_info("file123")
        assert result.success is False
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
        QuackIntegrationError rather than crashing with AttributeError."""
        with patch(
            "quack_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ):
            service = GoogleDriveService.__new__(GoogleDriveService)
            service.config_provider = None
            service.config_path = None

            with pytest.raises(
                QuackIntegrationError, match="no config_provider configured"
            ):
                service._initialize_config(None, None, None)

    def test_initialize_config_raises_when_default_config_invalid(self) -> None:
        """Line 135: config load fails AND the default config itself fails
        validate_config -- must raise QuackIntegrationError rather than
        silently returning an invalid default."""
        with patch(
            "quack_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load, patch(
            "quack_core.integrations.google.config.GoogleConfigProvider."
            "validate_config"
        ) as mock_validate:
            from quack_core.integrations.core.results import ConfigResult

            mock_load.return_value = ConfigResult(success=False, content=None)
            mock_validate.return_value = False

            with patch(
                "quack_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                with pytest.raises(
                    QuackIntegrationError,
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
            "quack_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load:
            from quack_core.integrations.core.results import ConfigResult

            mock_load.return_value = ConfigResult(
                success=True,
                content={
                    "client_secrets_file": "/loaded/secrets.json",
                    "credentials_file": "/loaded/credentials.json",
                    "shared_folder_id": "loaded_folder",
                },
            )

            with patch(
                "quack_core.integrations.google.auth.GoogleAuthProvider."
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
            "quack_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load:
            from quack_core.integrations.core.results import ConfigResult

            mock_load.return_value = ConfigResult(
                success=True,
                content={
                    "client_secrets_file": "/loaded/secrets.json",
                    "credentials_file": "/loaded/credentials.json",
                },
            )
            with patch(
                "quack_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                service = GoogleDriveService(
                    client_secrets_file="/override/secrets.json",
                    config_path="/path/to/config.yaml",
                )
        assert service.config["client_secrets_file"] == "/override/secrets.json"
        assert service.config["credentials_file"] == "/loaded/credentials.json"

        with patch(
            "quack_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load:
            from quack_core.integrations.core.results import ConfigResult

            mock_load.return_value = ConfigResult(
                success=True,
                content={
                    "client_secrets_file": "/loaded/secrets.json",
                    "credentials_file": "/loaded/credentials.json",
                },
            )
            with patch(
                "quack_core.integrations.google.auth.GoogleAuthProvider."
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
    get_credentials() QuackBaseAuthError catch (176-180).

    NOTE on the OUTER `except QuackBaseAuthError` at service.py:202-204:
    this is DEAD CODE too, same shape as the six sibling bugs pinned
    above, but unreachable for a structurally different reason: it is not
    guarded by an inner `except Exception` wrapper, it is guarded by
    BaseIntegrationService.initialize() (base.py:315-354) itself never
    propagating any exception to its caller -- that method has its own
    unconditional `except Exception` (base.py:350) that catches
    everything and returns an IntegrationResult instead of raising. Since
    `super().initialize()` (service.py:158) is the only statement between
    the outer try and the inner get_credentials() try/except that could
    plausibly raise QuackBaseAuthError, and it structurally cannot, lines
    202-204 have no legitimate trigger -- forcing them would require
    patching BaseIntegrationService.initialize() itself to behave
    differently than it ever does in production, which is not a real
    scenario and is intentionally NOT done here. Left uncovered rather
    than faked; see this file's module docstring / the final report for
    the bug list."""

    def test_initialize_returns_error_when_auth_provider_none(self) -> None:
        with patch(
            "quack_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ):
            service = GoogleDriveService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            service.auth_provider = None

            result = service.initialize()

        assert result.success is False
        assert "no auth_provider configured" in result.error

    @patch("quack_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("quack_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    def test_initialize_get_credentials_auth_error(
        self, mock_get_credentials: MagicMock, mock_authenticate: MagicMock
    ) -> None:
        """Lines 176-180: get_credentials() raising QuackBaseAuthError IS
        legitimately caught by its own dedicated inner try/except (unlike
        the six dead outer handlers pinned above -- this inner one is not
        itself nested inside a broader `except Exception` that would beat
        it to the exception)."""
        with patch(
            "quack_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ):
            mock_authenticate.return_value.success = True
            mock_get_credentials.side_effect = QuackBaseAuthError(
                "Bad credentials", service="drive"
            )

            service = GoogleDriveService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            result = service.initialize()

        assert result.success is False
        assert "Failed to authenticate with Google Drive" in result.error
        assert "Bad credentials" in result.error


class TestResolveFileDetailsErrorPaths:
    """_resolve_file_details' filename-fallback branch (line 244), using
    the real PathService/standalone, no mocking of quack_core internals,
    per RULING-235.

    NOTE: line 231 (`if not path_obj_result.success or ...: raise
    QuackIntegrationError("Failed to resolve path: ...")`) is not
    exercised here. The real PathService.resolve_project_path is lenient
    -- confirmed live this session -- it successfully resolves even
    directory-traversal-style inputs (`../../../etc/...`) and non-string
    inputs (None, ints, bytes) by joining them onto the project root
    rather than failing, so there is no real input that makes it return
    success=False. Forcing that branch would require mocking
    `paths_service`/`PathService` directly, which RULING-235 forbids as a
    quack_core internal, not an SDK/network boundary -- so this line is
    left uncovered rather than faked."""

    @pytest.fixture
    def service(self) -> Generator[GoogleDriveService, None, None]:
        with patch.object(GoogleDriveService, "_initialize_config") as mock_init:
            mock_init.return_value = {
                "client_secrets_file": "/fake/test/dir/mock_secrets.json",
                "credentials_file": "/fake/test/dir/mock_credentials.json",
            }
            with patch(
                "quack_core.integrations.google.auth.GoogleAuthProvider."
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

    BUG FOUND, PINNED, NOT FIXED (see final report): service.py:416,
    `parent_dir = standalone.join_path(download_path).parent`, calls
    `.parent` directly on `standalone.join_path(...)`'s return value.
    `join_path` returns a `DataResult` (confirmed live this session), not
    a raw `Path` -- `DataResult` has `.path` (a `PosixPath`) and `.data`
    (a str) but NO `.parent` attribute. This means download_file's real
    body ALWAYS raises `AttributeError: 'DataResult' object has no
    attribute 'parent'` immediately after fetching metadata, for every
    single call, regardless of what the Drive API or the download itself
    would have done -- it never reaches directory creation (417), the
    chunked download loop (424-441), or the disk write (448-457) at all.
    Every one of those lines is consequently UNREACHABLE in the current
    codebase, not merely untested. This is the exact "Result-wrapping
    return value handled as if it were the raw unwrapped value" disease
    shape this stream's charter calls out (RULING-236 through 240's
    fixes), just not yet ruled on for this specific call site. Not fixed
    per this stream's charter (no unilateral production fixes) --
    reported for a ruling."""

    def test_download_file_not_initialized(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """Line 396 (_ensure_initialized guard) -- reachable, runs before
        the join_path(...).parent bug."""
        real_drive_service._initialized = False
        with patch.object(real_drive_service, "initialize") as mock_init:
            from quack_core.integrations.core.results import IntegrationResult

            mock_init.return_value = IntegrationResult.error_result(
                "Not initialized"
            )
            result = real_drive_service.download_file("file123")
        assert result.success is False
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
        assert "Failed to get file metadata from Google Drive" in result.error

    def test_download_file_join_path_parent_bug_blocks_every_successful_call(
        self, real_drive_service: GoogleDriveService
    ) -> None:
        """PINS THE BUG: see class docstring. Metadata fetch succeeds
        (the real, legitimate part of the flow), but the very next line
        (416) crashes with AttributeError on `.parent`, landing in the
        OUTER generic `except Exception` handler (459-461) -- not the
        directory-creation-failure branch, not the download-error branch,
        not a success. This is true even though nothing about this
        request was otherwise wrong: valid metadata, a fully mockable SDK
        download that a correctly-implemented method would have
        completed successfully."""
        mock_execute = (
            real_drive_service.drive_service.files.return_value
            .get.return_value.execute
        )
        mock_execute.return_value = {
            "name": "downloaded.txt",
            "mimeType": "text/plain",
        }
        target = "coverage90_download_parent_bug_probe.txt"

        result = real_drive_service.download_file("file123", target)

        assert result.success is False
        assert "'DataResult' object has no attribute 'parent'" in result.error
        # Confirms the file was never even attempted to be written --
        # the crash happens before get_media()/MediaIoBaseDownload is
        # ever reached.
        assert not Path(target).exists()
        real_drive_service.drive_service.files.return_value.get_media.assert_not_called()

    def test_download_file_directory_creation_line_is_unreachable(
        self, real_drive_service: GoogleDriveService, tmp_path: Path
    ) -> None:
        """Line 419 (create_directory's success check) is, per the pinned
        bug above, UNREACHABLE: line 416 crashes before line 417's
        create_directory call is ever made, regardless of what real
        filesystem state would have made create_directory itself fail
        (here: a real file blocking the directory location). The error
        message is the same generic AttributeError, not a
        "Failed to create directory" message -- confirming
        create_directory is never actually invoked."""
        mock_execute = (
            real_drive_service.drive_service.files.return_value
            .get.return_value.execute
        )
        mock_execute.return_value = {
            "name": "downloaded.txt",
            "mimeType": "text/plain",
        }
        blocking_file = tmp_path / "blocking_file"
        blocking_file.write_text("I am a file, not a directory")
        target = str(blocking_file / "downloaded.txt")

        result = real_drive_service.download_file("file123", target)

        assert result.success is False
        assert "Failed to create directory" not in result.error
        assert "'DataResult' object has no attribute 'parent'" in result.error


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
                "quack_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ):
                svc = GoogleDriveService()
                svc._initialized = False
                with patch.object(svc, "initialize") as mock_service_init:
                    from quack_core.integrations.core.results import (
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
        assert "Not initialized" in result.error

    def test_create_folder_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.create_folder("New Folder")
        assert result.success is False
        assert "Not initialized" in result.error

    def test_set_file_permissions_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.set_file_permissions("file123")
        assert result.success is False
        assert "Not initialized" in result.error

    def test_get_sharing_link_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.get_sharing_link("file123")
        assert result.success is False
        assert "Not initialized" in result.error

    def test_delete_file_not_initialized(
        self, uninitialized_service: GoogleDriveService
    ) -> None:
        result = uninitialized_service.delete_file("file123")
        assert result.success is False
        assert "Not initialized" in result.error


class TestUploadHelperBranches:
    """_build_upload_metadata's description-included branch (802),
    _apply_public_sharing's permission-failure warning (850), and
    upload_file's own QuackIntegrationError catch when
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
        from quack_core.integrations.core.results import IntegrationResult

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
        QuackIntegrationError for a real, genuinely nonexistent file is
        caught directly and turned into an error result, without ever
        reaching the SDK boundary."""
        result = real_drive_service.upload_file(
            "coverage90_upload_nonexistent_probe.txt"
        )
        assert result.success is False
        assert "File not found" in result.error
        real_drive_service.drive_service.files.assert_not_called()
