"""
Tests for GoogleConfigProvider's sheets arm, and the mandated
config-dispatch regression proof: `GoogleConfigProvider("drive"/"mail"/
"calendar"/"docs", ...)`'s resolved config output must be unchanged by
adding the `"sheets"` arm.

Mirrors tests/test_integrations/google/docs/test_config.py's structure and
reading-derived regression-proof method exactly (per RULING-408 item 6,
adding a "sheets" key to the three dispatch points in google/config.py is
ADDITIVE, not a change to the existing pattern -- and per the spawn brief,
those insertion points already existed on the prep branch before this
stream started; this file proves they behave correctly, it does not add
them).
"""

from unittest.mock import patch

from zeo_core.integrations.google.config import (
    GoogleCalendarConfig,
    GoogleConfigProvider,
    GoogleDocsConfig,
    GoogleDriveConfig,
    GoogleMailConfig,
    GoogleSheetsConfig,
)
from zeo_core.integrations.google.credential_paths import (
    default_client_secret_path,
    default_credentials_path,
)

_EXPECTED_SECRET_PATH = default_client_secret_path()
_EXPECTED_CREDS_PATH = default_credentials_path()


class TestConfigDispatchRegression:
    """Drive/mail/calendar/docs' config-provider output is unchanged by the
    sheets arm's presence -- the mandatory regression proof."""

    def test_drive_get_default_config_unchanged(self) -> None:
        with patch(
            "zeo_core.integrations.google.credential_paths.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = False

            provider = GoogleConfigProvider("drive")
            assert provider.get_default_config() == {
                "client_secrets_file": _EXPECTED_SECRET_PATH,
                "credentials_file": _EXPECTED_CREDS_PATH,
                "shared_folder_id": None,
                "team_drive_id": None,
                "default_share_access": "reader",
                "public_sharing": True,
            }

    def test_mail_get_default_config_unchanged(self) -> None:
        with patch(
            "zeo_core.integrations.google.credential_paths.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = False

            provider = GoogleConfigProvider("mail")
            assert provider.get_default_config() == {
                "client_secrets_file": _EXPECTED_SECRET_PATH,
                "credentials_file": _EXPECTED_CREDS_PATH,
                "gmail_labels": [],
                "gmail_days_back": 7,
                "gmail_user_id": "me",
            }

    def test_calendar_get_default_config_unchanged(self) -> None:
        with patch(
            "zeo_core.integrations.google.credential_paths.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = False

            provider = GoogleConfigProvider("calendar")
            assert provider.get_default_config() == {
                "client_secrets_file": _EXPECTED_SECRET_PATH,
                "credentials_file": _EXPECTED_CREDS_PATH,
                "calendar_id": "primary",
                "max_results": 250,
                "time_zone": None,
            }

    def test_docs_get_default_config_unchanged(self) -> None:
        with patch(
            "zeo_core.integrations.google.credential_paths.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = False

            provider = GoogleConfigProvider("docs")
            assert provider.get_default_config() == {
                "client_secrets_file": _EXPECTED_SECRET_PATH,
                "credentials_file": _EXPECTED_CREDS_PATH,
                "document_id": None,
            }

    def test_drive_config_model_unchanged(self) -> None:
        provider = GoogleConfigProvider("drive")
        assert provider._config_models["drive"] is GoogleDriveConfig

    def test_mail_config_model_unchanged(self) -> None:
        provider = GoogleConfigProvider("mail")
        assert provider._config_models["mail"] is GoogleMailConfig

    def test_calendar_config_model_unchanged(self) -> None:
        provider = GoogleConfigProvider("calendar")
        assert provider._config_models["calendar"] is GoogleCalendarConfig

    def test_docs_config_model_unchanged(self) -> None:
        provider = GoogleConfigProvider("docs")
        assert provider._config_models["docs"] is GoogleDocsConfig


class TestGoogleSheetsConfig:
    """Tests for the GoogleSheetsConfig model and its dispatch arm."""

    def test_sheets_config_model_defaults(self) -> None:
        config = GoogleSheetsConfig(
            client_secrets_file="secrets.json", credentials_file="creds.json"
        )
        assert config.spreadsheet_id is None

    def test_sheets_config_model_requires_secrets_and_creds(self) -> None:
        from pydantic import ValidationError

        try:
            GoogleSheetsConfig()  # type: ignore[call-arg]
            raise AssertionError("expected ValidationError")
        except ValidationError:
            pass

    def test_provider_name_for_sheets(self) -> None:
        provider = GoogleConfigProvider("sheets")
        assert provider.name == "GoogleSheets"

    def test_sheets_config_model_registered(self) -> None:
        provider = GoogleConfigProvider("sheets")
        assert provider._config_models["sheets"] is GoogleSheetsConfig

    def test_sheets_get_default_config(self) -> None:
        with patch(
            "zeo_core.integrations.google.credential_paths.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = False

            provider = GoogleConfigProvider("sheets")
            assert provider.get_default_config() == {
                "client_secrets_file": _EXPECTED_SECRET_PATH,
                "credentials_file": _EXPECTED_CREDS_PATH,
                "spreadsheet_id": None,
            }

    def test_sheets_add_service_specific_defaults(self) -> None:
        provider = GoogleConfigProvider("sheets")
        config: dict[str, object] = {}
        provider._add_service_specific_defaults(config)
        assert config == {"spreadsheet_id": None}

    def test_sheets_add_service_specific_defaults_preserves_existing_keys(
        self,
    ) -> None:
        provider = GoogleConfigProvider("sheets")
        config: dict[str, object] = {"spreadsheet_id": "abc123"}
        provider._add_service_specific_defaults(config)
        assert config["spreadsheet_id"] == "abc123"

    def test_sheets_validate_config_valid(self) -> None:
        provider = GoogleConfigProvider("sheets")
        config = {
            "client_secrets_file": "secrets.json",
            "credentials_file": "creds.json",
        }
        assert provider.validate_config(config) is True

    def test_sheets_validate_config_missing_required_field(self) -> None:
        provider = GoogleConfigProvider("sheets")
        config: dict[str, object] = {"client_secrets_file": "secrets.json"}
        assert provider.validate_config(config) is False

    def test_sheets_extract_config_via_nested_google_section(self) -> None:
        provider = GoogleConfigProvider("sheets")
        config_data = {
            "integrations": {
                "google": {
                    "client_secrets_file": "shared_secrets.json",
                    "credentials_file": "shared_creds.json",
                    "sheets": {"spreadsheet_id": "sheet-xyz"},
                }
            }
        }
        result = provider._extract_config(config_data)
        assert result["client_secrets_file"] == "shared_secrets.json"
        assert result["spreadsheet_id"] == "sheet-xyz"
