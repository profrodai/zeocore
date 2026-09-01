"""
Tests for GoogleSheetsService.

Mocks at the Google SDK boundary: `googleapiclient.discovery.build`'s
return value is a `MagicMock()` shaped like the real Sheets v4 Resource
(`.spreadsheets().get/create/batchUpdate(...).execute()` and
`.spreadsheets().values().get/update/append/clear(...).execute()`),
matching `docs/test_service.py`'s house style -- NOT `patch.object(service,
"get_spreadsheet")`, which the spawn brief explicitly calls out (via the
Docs precedent) as a weak anti-pattern that proves nothing about the real
implementation. No real Google API token or network access is required to
pass.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.google.sheets.protocols import SheetsIntegrationProtocol
from zeo_core.integrations.google.sheets.service import GoogleSheetsService


def _make_initialized_service(mock_build: MagicMock) -> GoogleSheetsService:
    """Construct a GoogleSheetsService and drive it through initialize()
    with the Sheets API client mocked, returning the initialized service
    with its mock sheets_service attached for assertion.

    Same shape as docs/test_service.py's `_make_initialized_service`:
    `BaseIntegrationService.initialize()`'s own eager config-loading check
    is patched out directly (matching `google/mail/test_mail_service.py`'s
    and `google/docs/test_service.py`'s identical workaround for the same
    underlying issue) rather than requiring a real config file on disk.
    """
    mock_sheets_service = MagicMock()
    mock_build.return_value = mock_sheets_service

    with (
        patch(
            "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init,
        patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ),
        patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate"
        ) as mock_auth,
        patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials"
        ) as mock_creds,
    ):
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_auth.return_value.success = True
        mock_creds.return_value = MagicMock()

        service = GoogleSheetsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()
        assert result.success is True
        assert service.sheets_service is mock_sheets_service
    return service


# ---------------------------------------------------------------------
# Construction / deferred config (RULING-408 item 4)
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceFreshDirectoryConstruction:
    """The required acceptance test for the deferred-config pattern:
    constructing the service from a directory with NO config file and NO
    repo must never raise. Only initialize() may fail later.

    HOME is also redirected (not just CWD via tmp_path), per the brief's
    explicit acceptance bar: credential_paths.py's platformdirs-based
    resolution reads HOME, and even though construction is deferred and
    never calls into credential_paths, the acceptance test is written to
    prove the invariant holds under the harsher condition, not merely the
    weaker one -- construction must not raise even when neither CWD nor
    the real user HOME offer any pre-existing config or credential state.
    """

    def test_fresh_directory_construction_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        # No client_secrets_file/credentials_file, no config_path, no
        # zeo_config.yaml anywhere in this fresh tmp_path, and HOME itself
        # redirected to the same empty directory -- construction must
        # still succeed by deferred-config construction.
        service = GoogleSheetsService()
        assert service._initialized is False
        assert service.sheets_service is None
        assert service.auth_provider is None

    def test_fresh_directory_construction_with_explicit_params(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        service = GoogleSheetsService(
            client_secrets_file="secrets.json",
            credentials_file="creds.json",
        )
        assert service.custom_config["client_secrets_file"] == "secrets.json"
        assert service._initialized is False

    def test_fresh_directory_construction_repeated_is_stable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Constructing twice in the same fresh directory must not raise
        on either call and must not leave state from the first instance
        bleeding into the second (each construction is independent)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        first = GoogleSheetsService()
        second = GoogleSheetsService()
        assert first._initialized is False
        assert second._initialized is False
        assert first is not second


class TestGoogleSheetsServiceInit:
    """Tests for GoogleSheetsService construction (not fresh-directory
    specific)."""

    def test_init_basic_properties(self) -> None:
        service = GoogleSheetsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert service.name == "GoogleSheets"
        assert service.version == "1.0.0"
        assert service._initialized is False
        assert service.scopes == GoogleSheetsService.SCOPES

    def test_init_scope_is_narrower_than_drive(self) -> None:
        """RULING-405/406's narrower-than-Drive clause: the default scope
        must be narrower than Drive's `.../auth/drive`."""
        service = GoogleSheetsService()
        assert service.scopes == ["https://www.googleapis.com/auth/spreadsheets"]
        assert "https://www.googleapis.com/auth/drive" not in service.scopes

    def test_init_custom_scopes_override_default(self) -> None:
        custom_scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        service = GoogleSheetsService(scopes=custom_scopes)
        assert service.scopes == custom_scopes

    def test_init_custom_config_requires_both_secrets_and_creds(self) -> None:
        """Providing only one of the two file paths must NOT populate
        custom_config -- matching docs/mail's own short-circuit contract
        (both-or-neither)."""
        service = GoogleSheetsService(client_secrets_file="/path/to/secrets.json")
        assert service.custom_config == {}

    def test_init_with_both_paths_populates_custom_config(self) -> None:
        service = GoogleSheetsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert service.custom_config == {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
        }

    def test_integration_id(self) -> None:
        service = GoogleSheetsService()
        assert service.integration_id == "googlesheets"

    def test_satisfies_sheets_integration_protocol(self) -> None:
        service = GoogleSheetsService()
        assert isinstance(service, SheetsIntegrationProtocol)


# ---------------------------------------------------------------------
# initialize()
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceInitialize:
    @patch("googleapiclient.discovery.build")
    def test_initialize_success_builds_sheets_v4_client(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        assert service._initialized is True
        mock_build.assert_called_once()
        _, kwargs = mock_build.call_args
        # Positional args are ("sheets", "v4", credentials=...)
        args, kwargs = mock_build.call_args
        assert args[0] == "sheets"
        assert args[1] == "v4"

    @patch("googleapiclient.discovery.build")
    def test_initialize_auth_failure_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError
        from zeo_core.integrations.core.results import IntegrationResult

        with (
            patch(
                "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
            ) as mock_base_init,
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ),
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials"
            ) as mock_creds,
        ):
            mock_base_init.return_value = IntegrationResult.success_result()
            mock_creds.side_effect = ZeoBaseAuthError("no credentials available")

            service = GoogleSheetsService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            result = service.initialize()

            assert result.success is False
            assert result.error is not None
            assert "Failed to authenticate" in result.error
            assert service._initialized is False

    def test_initialize_missing_config_returns_error_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No custom_config, no config file on disk anywhere -- initialize()
        (not __init__) is where this genuinely surfaces."""
        from zeo_core.integrations.core.results import IntegrationResult

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))

        with patch(
            "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.success_result()
            service = GoogleSheetsService()
            result = service.initialize()

            assert result.success is False
            assert service._initialized is False

    @patch("googleapiclient.discovery.build")
    def test_initialize_api_build_failure_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        mock_build.side_effect = RuntimeError("network unreachable")

        with (
            patch(
                "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
            ) as mock_base_init,
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ),
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate"
            ) as mock_auth,
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials"
            ) as mock_creds,
        ):
            mock_base_init.return_value = IntegrationResult.success_result()
            mock_auth.return_value.success = True
            mock_creds.return_value = MagicMock()

            service = GoogleSheetsService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            result = service.initialize()

            assert result.success is False
            assert result.error is not None
            assert "API error" in result.error
            assert service._initialized is False

    def test_initialize_base_failure_short_circuits(self) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        with patch(
            "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.error_result(
                "base init failed"
            )
            service = GoogleSheetsService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            result = service.initialize()
            assert result.success is False
            assert result.error == "base init failed"


# ---------------------------------------------------------------------
# Uninitialized guard: every public method must refuse to run before
# initialize() succeeds, matching docs/service.py's `_ensure_initialized`
# convention exactly.
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceUninitializedGuard:
    def test_get_spreadsheet_before_initialize(self) -> None:
        service = GoogleSheetsService()
        result = service.get_spreadsheet("abc")
        assert result.success is False

    def test_create_spreadsheet_before_initialize(self) -> None:
        service = GoogleSheetsService()
        result = service.create_spreadsheet("New Sheet")
        assert result.success is False

    def test_get_values_before_initialize(self) -> None:
        service = GoogleSheetsService()
        result = service.get_values("abc", "Sheet1!A1:B2")
        assert result.success is False

    def test_update_values_before_initialize(self) -> None:
        service = GoogleSheetsService()
        result = service.update_values("abc", "Sheet1!A1", [["x"]])
        assert result.success is False

    def test_append_values_before_initialize(self) -> None:
        service = GoogleSheetsService()
        result = service.append_values("abc", "Sheet1!A1", [["x"]])
        assert result.success is False

    def test_clear_values_before_initialize(self) -> None:
        service = GoogleSheetsService()
        result = service.clear_values("abc", "Sheet1!A1:B2")
        assert result.success is False

    def test_batch_update_before_initialize(self) -> None:
        service = GoogleSheetsService()
        result = service.batch_update("abc", [{"addSheet": {}}])
        assert result.success is False


# ---------------------------------------------------------------------
# spreadsheets.get
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceGetSpreadsheet:
    @patch("googleapiclient.discovery.build")
    def test_get_spreadsheet_calls_sdk_with_spreadsheet_id(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        mock_spreadsheet: dict[str, Any] = {
            "spreadsheetId": "sheet123",
            "properties": {"title": "My Sheet"},
        }
        (
            service.sheets_service.spreadsheets.return_value.get.return_value.execute.return_value
        ) = mock_spreadsheet

        result = service.get_spreadsheet("sheet123")

        assert result.success is True
        assert result.content == mock_spreadsheet
        service.sheets_service.spreadsheets.return_value.get.assert_called_with(
            spreadsheetId="sheet123"
        )

    @patch("googleapiclient.discovery.build")
    def test_get_spreadsheet_sdk_error_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.get.return_value.execute.side_effect
        ) = RuntimeError("404 not found")

        result = service.get_spreadsheet("missing")

        assert result.success is False
        assert result.error is not None
        assert "Failed to get spreadsheet" in result.error

    @patch("googleapiclient.discovery.build")
    def test_get_spreadsheet_none_sheets_service_guard(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.sheets_service = None
        result = service.get_spreadsheet("sheet123")
        assert result.success is False
        assert result.error == "Google Sheets service is not initialized"


# ---------------------------------------------------------------------
# spreadsheets.create
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceCreateSpreadsheet:
    @patch("googleapiclient.discovery.build")
    def test_create_spreadsheet_calls_sdk_with_title_body(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        mock_created: dict[str, Any] = {
            "spreadsheetId": "new-sheet-id",
            "properties": {"title": "Q3 numbers"},
        }
        (
            service.sheets_service.spreadsheets.return_value.create.return_value.execute.return_value
        ) = mock_created

        result = service.create_spreadsheet("Q3 numbers")

        assert result.success is True
        assert result.content == mock_created
        service.sheets_service.spreadsheets.return_value.create.assert_called_with(
            body={"properties": {"title": "Q3 numbers"}}
        )

    @patch("googleapiclient.discovery.build")
    def test_create_spreadsheet_sdk_error_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.create.return_value.execute.side_effect
        ) = RuntimeError("quota exceeded")

        result = service.create_spreadsheet("Q3 numbers")

        assert result.success is False
        assert result.error is not None
        assert "Failed to create spreadsheet" in result.error

    @patch("googleapiclient.discovery.build")
    def test_create_spreadsheet_none_sheets_service_guard(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.sheets_service = None
        result = service.create_spreadsheet("Q3 numbers")
        assert result.success is False
        assert result.error == "Google Sheets service is not initialized"


# ---------------------------------------------------------------------
# spreadsheets.values.get
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceGetValues:
    @patch("googleapiclient.discovery.build")
    def test_get_values_calls_sdk_with_range(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        mock_value_range: dict[str, Any] = {
            "range": "Sheet1!A1:B2",
            "majorDimension": "ROWS",
            "values": [["Name", "Score"], ["Ada", "100"]],
        }
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value
        ) = mock_value_range

        result = service.get_values("sheet123", "Sheet1!A1:B2")

        assert result.success is True
        assert result.content == mock_value_range
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.get.assert_called_with(
                spreadsheetId="sheet123", range="Sheet1!A1:B2"
            )
        )

    @patch("googleapiclient.discovery.build")
    def test_get_values_sdk_error_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect
        ) = RuntimeError("invalid range")

        result = service.get_values("sheet123", "NotASheet!A1")

        assert result.success is False
        assert result.error is not None
        assert "Failed to get values" in result.error

    @patch("googleapiclient.discovery.build")
    def test_get_values_none_sheets_service_guard(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.sheets_service = None
        result = service.get_values("sheet123", "Sheet1!A1:B2")
        assert result.success is False
        assert result.error == "Google Sheets service is not initialized"


# ---------------------------------------------------------------------
# spreadsheets.values.update
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceUpdateValues:
    @patch("googleapiclient.discovery.build")
    def test_update_values_calls_sdk_with_value_range_body(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        mock_response: dict[str, Any] = {
            "spreadsheetId": "sheet123",
            "updatedRange": "Sheet1!A1:B1",
            "updatedCells": 2,
        }
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value
        ) = mock_response

        result = service.update_values("sheet123", "Sheet1!A1:B1", [["Name", "Score"]])

        assert result.success is True
        assert result.content == mock_response
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.assert_called_with(
                spreadsheetId="sheet123",
                range="Sheet1!A1:B1",
                body={"range": "Sheet1!A1:B1", "values": [["Name", "Score"]]},
                valueInputOption="USER_ENTERED",
            )
        )

    @patch("googleapiclient.discovery.build")
    def test_update_values_default_value_input_option_is_user_entered(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value
        ) = {}

        service.update_values("sheet123", "Sheet1!A1", [["x"]])

        _, kwargs = (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.call_args
        )
        assert kwargs["valueInputOption"] == "USER_ENTERED"

    @patch("googleapiclient.discovery.build")
    def test_update_values_raw_option_passed_through(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value
        ) = {}

        service.update_values(
            "sheet123", "Sheet1!A1", [["=SUM(1,2)"]], value_input_option="RAW"
        )

        _, kwargs = (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.call_args
        )
        assert kwargs["valueInputOption"] == "RAW"

    @patch("googleapiclient.discovery.build")
    def test_update_values_sdk_error_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.side_effect
        ) = RuntimeError("permission denied")

        result = service.update_values("sheet123", "Sheet1!A1", [["x"]])

        assert result.success is False
        assert result.error is not None
        assert "Failed to update values" in result.error

    @patch("googleapiclient.discovery.build")
    def test_update_values_none_sheets_service_guard(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.sheets_service = None
        result = service.update_values("sheet123", "Sheet1!A1", [["x"]])
        assert result.success is False
        assert result.error == "Google Sheets service is not initialized"


# ---------------------------------------------------------------------
# spreadsheets.values.append
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceAppendValues:
    @patch("googleapiclient.discovery.build")
    def test_append_values_calls_sdk_with_value_range_body(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        mock_response: dict[str, Any] = {
            "spreadsheetId": "sheet123",
            "tableRange": "Sheet1!A1:B1",
            "updates": {"updatedRange": "Sheet1!A2:B2"},
        }
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value
        ) = mock_response

        result = service.append_values("sheet123", "Sheet1!A1", [["Ada", "100"]])

        assert result.success is True
        assert result.content == mock_response
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.append.assert_called_with(
                spreadsheetId="sheet123",
                range="Sheet1!A1",
                body={"range": "Sheet1!A1", "values": [["Ada", "100"]]},
                valueInputOption="USER_ENTERED",
            )
        )

    def test_append_values_never_requires_caller_supplied_row_index(self) -> None:
        """Index-free by construction: append_values' signature has no row-
        index parameter anywhere -- the caller passes only a range
        identifying the TABLE, never a target row, matching the API's own
        'finds the first empty row after the table' semantics."""
        import inspect

        sig = inspect.signature(GoogleSheetsService.append_values)
        param_names = set(sig.parameters.keys())
        assert not any("row" in name.lower() for name in param_names)
        assert not any("index" in name.lower() for name in param_names)

    @patch("googleapiclient.discovery.build")
    def test_append_values_sdk_error_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.side_effect
        ) = RuntimeError("invalid range")

        result = service.append_values("sheet123", "Sheet1!A1", [["x"]])

        assert result.success is False
        assert result.error is not None
        assert "Failed to append values" in result.error

    @patch("googleapiclient.discovery.build")
    def test_append_values_none_sheets_service_guard(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.sheets_service = None
        result = service.append_values("sheet123", "Sheet1!A1", [["x"]])
        assert result.success is False
        assert result.error == "Google Sheets service is not initialized"


# ---------------------------------------------------------------------
# spreadsheets.values.clear
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceClearValues:
    @patch("googleapiclient.discovery.build")
    def test_clear_values_calls_sdk_with_range(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        mock_response: dict[str, Any] = {
            "spreadsheetId": "sheet123",
            "clearedRange": "Sheet1!A1:B2",
        }
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.clear.return_value.execute.return_value
        ) = mock_response

        result = service.clear_values("sheet123", "Sheet1!A1:B2")

        assert result.success is True
        assert result.content == mock_response
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.clear.assert_called_with(
                spreadsheetId="sheet123", range="Sheet1!A1:B2"
            )
        )

    @patch("googleapiclient.discovery.build")
    def test_clear_values_sdk_error_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.clear.return_value.execute.side_effect
        ) = RuntimeError("invalid range")

        result = service.clear_values("sheet123", "NotASheet!A1")

        assert result.success is False
        assert result.error is not None
        assert "Failed to clear values" in result.error

    @patch("googleapiclient.discovery.build")
    def test_clear_values_none_sheets_service_guard(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.sheets_service = None
        result = service.clear_values("sheet123", "Sheet1!A1:B2")
        assert result.success is False
        assert result.error == "Google Sheets service is not initialized"


# ---------------------------------------------------------------------
# spreadsheets.batchUpdate
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceBatchUpdate:
    @patch("googleapiclient.discovery.build")
    def test_batch_update_calls_sdk_with_requests_body(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        mock_response: dict[str, Any] = {
            "spreadsheetId": "sheet123",
            "replies": [{}],
        }
        (
            service.sheets_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value
        ) = mock_response
        requests: list[dict[str, Any]] = [
            {"addSheet": {"properties": {"sheetId": 1, "title": "New"}}}
        ]

        result = service.batch_update("sheet123", requests)

        assert result.success is True
        assert result.content == mock_response
        service.sheets_service.spreadsheets.return_value.batchUpdate.assert_called_with(
            spreadsheetId="sheet123", body={"requests": requests}
        )

    @patch("googleapiclient.discovery.build")
    def test_batch_update_preserves_caller_order_through_request_builder(
        self, mock_build: MagicMock
    ) -> None:
        """Proves the SERVICE actually routes through SheetsRequestBuilder
        (not just that the builder itself preserves order in isolation):
        the exact request list handed to the mocked SDK call is identical,
        in order, to what the caller passed in."""
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value
        ) = {}
        requests: list[dict[str, Any]] = [
            {"addSheet": {"properties": {"sheetId": 5, "title": "A"}}},
            {
                "repeatCell": {
                    "range": {"sheetId": 5, "startRowIndex": 0, "endRowIndex": 1}
                }
            },
            {"deleteSheet": {"sheetId": 2}},
        ]

        service.batch_update("sheet123", requests)

        _, kwargs = (
            service.sheets_service.spreadsheets.return_value.batchUpdate.call_args
        )
        assert kwargs["body"]["requests"] == requests

    @patch("googleapiclient.discovery.build")
    def test_batch_update_sdk_error_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.batchUpdate.return_value.execute.side_effect
        ) = RuntimeError("invalid request")

        result = service.batch_update("sheet123", [{"addSheet": {}}])

        assert result.success is False
        assert result.error is not None
        assert "Failed to apply batch update" in result.error

    @patch("googleapiclient.discovery.build")
    def test_batch_update_none_sheets_service_guard(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.sheets_service = None
        result = service.batch_update("sheet123", [{"addSheet": {}}])
        assert result.success is False
        assert result.error == "Google Sheets service is not initialized"

    @patch("googleapiclient.discovery.build")
    def test_batch_update_empty_requests_list(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value
        ) = {"spreadsheetId": "sheet123", "replies": []}

        result = service.batch_update("sheet123", [])

        assert result.success is True
        service.sheets_service.spreadsheets.return_value.batchUpdate.assert_called_with(
            spreadsheetId="sheet123", body={"requests": []}
        )


# ---------------------------------------------------------------------
# Outer except ZeoApiError / except ZeoBaseAuthError branches.
#
# Every one of the 7 curated methods (and initialize()) wraps its SDK call
# in an INNER try/except Exception (per drive/service.py's error-handling
# shape, copied for shape only -- see service.py's own module docstring),
# which means the OUTER `except ZeoApiError`/`except ZeoBaseAuthError`
# blocks can never be reached by an exception raised from the mocked SDK
# call itself -- that is caught first by the inner handler. This is an
# inherited structural property (Docs/Calendar/Drive/Mail all have the
# identical shape; docs/test_service.py leaves the same class of branch
# uncovered), not something introduced here.
#
# These tests exercise the outer branches legitimately rather than leaving
# them dead: they simulate a REALISTIC secondary-failure scenario --
# `IntegrationResult.error_result` itself raising one of this codebase's
# own error types while the inner handler is already responding to a first
# failure. This is not a contrived call directly into the except block; it
# is the one real code path that can reach the outer handlers without
# calling private methods directly.
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceOuterExceptBranches:
    @patch("googleapiclient.discovery.build")
    def test_get_spreadsheet_outer_zeo_api_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoApiError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.get.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [
                ZeoApiError("secondary", service="Google Sheets", api_method="get"),
                MagicMock(),
            ]
            service.get_spreadsheet("abc")
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_get_spreadsheet_outer_zeo_auth_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.get.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [ZeoBaseAuthError("secondary"), MagicMock()]
            service.get_spreadsheet("abc")
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_create_spreadsheet_outer_zeo_api_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoApiError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.create.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [
                ZeoApiError("secondary", service="Google Sheets", api_method="create"),
                MagicMock(),
            ]
            service.create_spreadsheet("title")
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_create_spreadsheet_outer_zeo_auth_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.create.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [ZeoBaseAuthError("secondary"), MagicMock()]
            service.create_spreadsheet("title")
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_get_values_outer_zeo_api_error_branch(self, mock_build: MagicMock) -> None:
        from zeo_core.core.errors import ZeoApiError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [
                ZeoApiError("secondary", service="Google Sheets", api_method="get"),
                MagicMock(),
            ]
            service.get_values("abc", "Sheet1!A1")
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_get_values_outer_zeo_auth_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [ZeoBaseAuthError("secondary"), MagicMock()]
            service.get_values("abc", "Sheet1!A1")
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_update_values_outer_zeo_api_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoApiError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [
                ZeoApiError("secondary", service="Google Sheets", api_method="update"),
                MagicMock(),
            ]
            service.update_values("abc", "Sheet1!A1", [["x"]])
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_update_values_outer_zeo_auth_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [ZeoBaseAuthError("secondary"), MagicMock()]
            service.update_values("abc", "Sheet1!A1", [["x"]])
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_append_values_outer_zeo_api_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoApiError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [
                ZeoApiError("secondary", service="Google Sheets", api_method="append"),
                MagicMock(),
            ]
            service.append_values("abc", "Sheet1!A1", [["x"]])
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_append_values_outer_zeo_auth_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [ZeoBaseAuthError("secondary"), MagicMock()]
            service.append_values("abc", "Sheet1!A1", [["x"]])
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_clear_values_outer_zeo_api_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoApiError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.clear.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [
                ZeoApiError("secondary", service="Google Sheets", api_method="clear"),
                MagicMock(),
            ]
            service.clear_values("abc", "Sheet1!A1")
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_clear_values_outer_zeo_auth_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.values.return_value.clear.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [ZeoBaseAuthError("secondary"), MagicMock()]
            service.clear_values("abc", "Sheet1!A1")
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_batch_update_outer_zeo_api_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoApiError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.batchUpdate.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [
                ZeoApiError(
                    "secondary", service="Google Sheets", api_method="batchUpdate"
                ),
                MagicMock(),
            ]
            service.batch_update("abc", [{"addSheet": {}}])
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_batch_update_outer_zeo_auth_error_branch(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError

        service = _make_initialized_service(mock_build)
        (
            service.sheets_service.spreadsheets.return_value.batchUpdate.return_value.execute.side_effect
        ) = RuntimeError("boom")

        with patch(
            "zeo_core.integrations.google.sheets.service.IntegrationResult.error_result"
        ) as mock_err:
            mock_err.side_effect = [ZeoBaseAuthError("secondary"), MagicMock()]
            service.batch_update("abc", [{"addSheet": {}}])
            assert mock_err.call_count == 2

    @patch("googleapiclient.discovery.build")
    def test_initialize_outer_zeo_api_error_branch_from_get_credentials(
        self, mock_build: MagicMock
    ) -> None:
        """initialize()'s own outer except ZeoApiError: triggered by
        get_credentials() itself raising ZeoApiError directly (a real,
        if rare, possibility -- GoogleAuthProvider.get_credentials can
        surface a network-layer API error, not only ZeoBaseAuthError)."""
        from zeo_core.core.errors import ZeoApiError
        from zeo_core.integrations.core.results import IntegrationResult

        with (
            patch(
                "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
            ) as mock_base_init,
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ),
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials"
            ) as mock_creds,
        ):
            mock_base_init.return_value = IntegrationResult.success_result()
            mock_creds.side_effect = ZeoApiError(
                "network layer failure", service="Google Sheets", api_method="auth"
            )

            service = GoogleSheetsService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            result = service.initialize()

            assert result.success is False
            assert result.error is not None
            assert "API error" in result.error
            assert service._initialized is False

    def test_initialize_outer_zeo_base_auth_error_branch_from_provider_construction(
        self,
    ) -> None:
        """initialize()'s outer except ZeoBaseAuthError: the INNER
        try/except around get_credentials() only covers that one call:
        GoogleAuthProvider(...) construction itself, one statement
        earlier, is outside that inner try -- if IT raises
        ZeoBaseAuthError (a real possibility: the base __init__ can
        validate the client secrets path eagerly), only the OUTER handler
        can catch it."""
        from zeo_core.core.errors import ZeoBaseAuthError
        from zeo_core.integrations.core.results import IntegrationResult

        with (
            patch(
                "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
            ) as mock_base_init,
            patch(
                "zeo_core.integrations.google.sheets.service.GoogleAuthProvider"
            ) as mock_provider_cls,
        ):
            mock_base_init.return_value = IntegrationResult.success_result()
            mock_provider_cls.side_effect = ZeoBaseAuthError("bad client secrets")

            service = GoogleSheetsService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            result = service.initialize()

            assert result.success is False
            assert result.error is not None
            assert "Authentication error" in result.error
            assert service._initialized is False


# ---------------------------------------------------------------------
# Defensive branches: _require_config_provider / _initialize_config
# (matching docs/test_service.py's identical defensive-branch-testing
# discipline for these structurally-hard-to-reach guards)
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceDefensiveBranches:
    def test_require_config_provider_raises_when_none(self) -> None:
        """__init__ always constructs a real GoogleConfigProvider before
        super().__init__ runs, so _require_config_provider's own `if
        self.config_provider is None` guard can never fire in production.
        Directly force the structurally-impossible state to exercise the
        guard's own raise, same defensive-branch-testing discipline as
        docs/test_service.py's and mail/test_mail_service.py's identical
        test."""
        from zeo_core.core.errors import ZeoIntegrationError

        service = GoogleSheetsService(config_path="/path/to/config.yaml")
        service.config_provider = None
        with pytest.raises(ZeoIntegrationError, match="no config_provider configured"):
            service._require_config_provider()

    def test_initialize_config_load_from_file_failure(self) -> None:
        from zeo_core.core.errors import ZeoIntegrationError

        service = GoogleSheetsService(config_path="/path/to/config.yaml")
        with patch.object(service.config_provider, "load_config") as mock_load_config:
            mock_load_config.return_value = MagicMock(success=False, content=None)
            with pytest.raises(
                ZeoIntegrationError, match="Failed to load configuration"
            ):
                service._initialize_config()

    def test_initialize_config_unexpected_exception_returns_none(self) -> None:
        service = GoogleSheetsService(config_path="/path/to/config.yaml")
        with (
            patch.object(service.config_provider, "load_config") as mock_load_config,
            patch.object(service.logger, "error") as mock_error,
        ):
            mock_load_config.side_effect = RuntimeError("unexpected boom")

            result = service._initialize_config()

            assert result is None
            mock_error.assert_called_once()

    def test_initialize_config_loads_from_file_when_no_custom_config(self) -> None:
        service = GoogleSheetsService(config_path="/path/to/config.yaml")
        with patch.object(service.config_provider, "load_config") as mock_load_config:
            mock_load_config.return_value = MagicMock(
                success=True,
                content={
                    "client_secrets_file": "s.json",
                    "credentials_file": "c.json",
                },
            )
            config = service._initialize_config()
            assert config == {
                "client_secrets_file": "s.json",
                "credentials_file": "c.json",
            }


# ---------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------


class TestGoogleSheetsServiceValidateConfig:
    def test_validate_config_valid(self) -> None:
        service = GoogleSheetsService()
        is_valid, errors = service.validate_config(
            {
                "client_secrets_file": "secrets.json",
                "credentials_file": "creds.json",
            }
        )
        assert is_valid is True
        assert errors == []

    def test_validate_config_missing_required_field(self) -> None:
        service = GoogleSheetsService()
        is_valid, errors = service.validate_config(
            {"client_secrets_file": "secrets.json"}
        )
        assert is_valid is False
        assert len(errors) == 1

    def test_validate_config_with_spreadsheet_id(self) -> None:
        service = GoogleSheetsService()
        is_valid, errors = service.validate_config(
            {
                "client_secrets_file": "secrets.json",
                "credentials_file": "creds.json",
                "spreadsheet_id": "abc123",
            }
        )
        assert is_valid is True
        assert errors == []
