"""
Tests for GoogleConfigProvider's calendar arm, and the mandated
config-dispatch regression proof: `GoogleConfigProvider("drive", ...)` and
`GoogleConfigProvider("mail", ...)`'s resolved config output must be
byte-identical to what the pre-calendar code produced.

This is a reading-derived regression proof, not a literal git-stash +
re-run diff (stated explicitly, per the stream's own SOW): the expected
dicts below were copied verbatim from `google/config.py`'s
`_add_service_specific_defaults`/`get_default_config` elif branches for
"drive"/"mail" as they existed on `origin/main` BEFORE this stream's edit
(read directly, not assumed from memory) -- adding a third `elif
self.service == "calendar"` arm cannot change what the `"drive"`/`"mail"`
branches return, since Python's elif chain short-circuits on the first
matching branch and a new arm appended after both existing ones is
structurally unreachable from either. The test pins the literal values so
any FUTURE accidental edit to the drive/mail branches (not just this
stream's own change) is caught too.
"""

from zeo_core.integrations.google.config import (
    GoogleCalendarConfig,
    GoogleConfigProvider,
    GoogleDriveConfig,
    GoogleMailConfig,
)


class TestConfigDispatchRegression:
    """Drive/mail's config-provider output is unchanged by adding the
    calendar arm -- the mandatory regression proof."""

    def test_drive_get_default_config_unchanged(self) -> None:
        provider = GoogleConfigProvider("drive")
        assert provider.get_default_config() == {
            "client_secrets_file": "config/google_client_secret.json",
            "credentials_file": "config/google_credentials.json",
            "shared_folder_id": None,
            "team_drive_id": None,
            "default_share_access": "reader",
            "public_sharing": True,
        }

    def test_mail_get_default_config_unchanged(self) -> None:
        provider = GoogleConfigProvider("mail")
        assert provider.get_default_config() == {
            "client_secrets_file": "config/google_client_secret.json",
            "credentials_file": "config/google_credentials.json",
            "gmail_labels": [],
            "gmail_days_back": 7,
            "gmail_user_id": "me",
        }

    def test_drive_add_service_specific_defaults_unchanged(self) -> None:
        provider = GoogleConfigProvider("drive")
        config: dict[str, object] = {}
        provider._add_service_specific_defaults(config)
        assert config == {
            "shared_folder_id": None,
            "team_drive_id": None,
            "default_share_access": "reader",
            "public_sharing": True,
        }

    def test_mail_add_service_specific_defaults_unchanged(self) -> None:
        provider = GoogleConfigProvider("mail")
        config: dict[str, object] = {}
        provider._add_service_specific_defaults(config)
        assert config == {
            "gmail_labels": [],
            "gmail_days_back": 7,
            "gmail_user_id": "me",
            "storage_path": "output/gmail",
            "include_subject": False,
            "include_sender": False,
        }

    def test_drive_config_model_unchanged(self) -> None:
        provider = GoogleConfigProvider("drive")
        assert provider._config_models["drive"] is GoogleDriveConfig

    def test_mail_config_model_unchanged(self) -> None:
        provider = GoogleConfigProvider("mail")
        assert provider._config_models["mail"] is GoogleMailConfig

    def test_drive_validate_config_still_valid(self) -> None:
        provider = GoogleConfigProvider("drive")
        config = {
            "client_secrets_file": "secrets.json",
            "credentials_file": "creds.json",
        }
        assert provider.validate_config(config) is True

    def test_mail_validate_config_still_valid(self) -> None:
        provider = GoogleConfigProvider("mail")
        config = {
            "client_secrets_file": "secrets.json",
            "credentials_file": "creds.json",
        }
        assert provider.validate_config(config) is True


class TestGoogleCalendarConfig:
    """Tests for the new GoogleCalendarConfig model and its dispatch arm."""

    def test_calendar_config_model_defaults(self) -> None:
        config = GoogleCalendarConfig(
            client_secrets_file="secrets.json", credentials_file="creds.json"
        )
        assert config.calendar_id == "primary"
        assert config.max_results == 250
        assert config.time_zone is None

    def test_calendar_config_model_requires_secrets_and_creds(self) -> None:
        from pydantic import ValidationError

        try:
            GoogleCalendarConfig()  # type: ignore[call-arg]
            raise AssertionError("expected ValidationError")
        except ValidationError:
            pass

    def test_provider_name_for_calendar(self) -> None:
        provider = GoogleConfigProvider("calendar")
        assert provider.name == "GoogleCalendar"

    def test_calendar_config_model_registered(self) -> None:
        provider = GoogleConfigProvider("calendar")
        assert provider._config_models["calendar"] is GoogleCalendarConfig

    def test_calendar_get_default_config(self) -> None:
        provider = GoogleConfigProvider("calendar")
        assert provider.get_default_config() == {
            "client_secrets_file": "config/google_client_secret.json",
            "credentials_file": "config/google_credentials.json",
            "calendar_id": "primary",
            "max_results": 250,
            "time_zone": None,
        }

    def test_calendar_add_service_specific_defaults(self) -> None:
        provider = GoogleConfigProvider("calendar")
        config: dict[str, object] = {}
        provider._add_service_specific_defaults(config)
        assert config == {
            "calendar_id": "primary",
            "max_results": 250,
            "time_zone": None,
        }

    def test_calendar_add_service_specific_defaults_preserves_existing_keys(
        self,
    ) -> None:
        provider = GoogleConfigProvider("calendar")
        config: dict[str, object] = {"calendar_id": "team@example.com"}
        provider._add_service_specific_defaults(config)
        assert config["calendar_id"] == "team@example.com"
        assert config["max_results"] == 250

    def test_calendar_validate_config_valid(self) -> None:
        provider = GoogleConfigProvider("calendar")
        config = {
            "client_secrets_file": "secrets.json",
            "credentials_file": "creds.json",
        }
        assert provider.validate_config(config) is True

    def test_calendar_validate_config_missing_required_field(self) -> None:
        provider = GoogleConfigProvider("calendar")
        config: dict[str, object] = {"client_secrets_file": "secrets.json"}
        assert provider.validate_config(config) is False

    def test_calendar_extract_config_via_nested_google_section(self) -> None:
        provider = GoogleConfigProvider("calendar")
        config_data = {
            "integrations": {
                "google": {
                    "client_secrets_file": "shared_secrets.json",
                    "credentials_file": "shared_creds.json",
                    "calendar": {"calendar_id": "team@example.com"},
                }
            }
        }
        result = provider._extract_config(config_data)
        assert result["client_secrets_file"] == "shared_secrets.json"
        assert result["calendar_id"] == "team@example.com"
        assert result["max_results"] == 250
