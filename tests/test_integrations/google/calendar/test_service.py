"""
Tests for GoogleCalendarService.

Mocks the `googleapiclient.discovery.build` return value shaped like the
real Calendar v3 Resource (`.events().list/get/insert/update/delete(...).
execute()`, `.calendarList().list().execute()`, `.calendars().get(...).
execute()`) -- no real Google API token or network access required to pass,
matching notion/drive's own chartered constraint.
"""

from unittest.mock import MagicMock, patch

from zeo_core.integrations.google.calendar.protocols import (
    CalendarIntegrationProtocol,
)
from zeo_core.integrations.google.calendar.service import GoogleCalendarService


def _make_initialized_service(mock_build: MagicMock) -> GoogleCalendarService:
    """Construct a GoogleCalendarService and drive it through initialize()
    with the Calendar API client mocked, returning the initialized service
    with its mock calendar_service attached for assertion."""
    mock_calendar_service = MagicMock()
    mock_build.return_value = mock_calendar_service

    with (
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
        mock_auth.return_value.success = True
        mock_creds.return_value = MagicMock()

        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()
        assert result.success is True
        assert service.calendar_service is mock_calendar_service
    return service


class TestGoogleCalendarServiceInit:
    """Tests for GoogleCalendarService construction."""

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    def test_init(self, mock_verify: MagicMock) -> None:
        mock_verify.return_value = None

        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            calendar_id="team@example.com",
        )

        assert service.name == "GoogleCalendar"
        assert service.config["client_secrets_file"] == "/path/to/secrets.json"
        assert service.config["credentials_file"] == "/path/to/credentials.json"
        assert service.config["calendar_id"] == "team@example.com"
        assert service.scopes == GoogleCalendarService.SCOPES
        assert service.default_calendar_id == "team@example.com"
        assert service._initialized is False

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    def test_init_default_calendar_id_is_primary(self, mock_verify: MagicMock) -> None:
        mock_verify.return_value = None
        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert service.default_calendar_id == "primary"

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    def test_init_always_constructs_real_config_and_auth_providers(
        self, mock_verify: MagicMock
    ) -> None:
        mock_verify.return_value = None
        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert service.config_provider is not None
        assert service.auth_provider is not None
        assert type(service.config_provider).__name__ == "GoogleConfigProvider"
        assert type(service.auth_provider).__name__ == "GoogleAuthProvider"

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    def test_is_calendar_integration_protocol(self, mock_verify: MagicMock) -> None:
        mock_verify.return_value = None
        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert isinstance(service, CalendarIntegrationProtocol)

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.config.GoogleConfigProvider.load_config")
    def test_initialize_config_from_file(
        self, mock_load_config: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_verify.return_value = None
        mock_load_config.return_value.success = True
        mock_load_config.return_value.content = {
            "client_secrets_file": "/config/secrets.json",
            "credentials_file": "/config/credentials.json",
            "calendar_id": "config-cal@example.com",
        }

        service = GoogleCalendarService(config_path="/path/to/config.yaml")
        assert service.config["client_secrets_file"] == "/config/secrets.json"
        assert service.config["credentials_file"] == "/config/credentials.json"
        assert service.config["calendar_id"] == "config-cal@example.com"

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.config.GoogleConfigProvider.load_config")
    def test_initialize_config_falls_back_to_defaults(
        self, mock_load_config: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_verify.return_value = None
        mock_load_config.return_value.success = False

        with patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider.get_default_config"
        ) as mock_default:
            mock_default.return_value = {
                "client_secrets_file": "/default/secrets.json",
                "credentials_file": "/default/credentials.json",
                "calendar_id": "primary",
            }
            service = GoogleCalendarService(config_path="/invalid/config.yaml")
            assert service.config["client_secrets_file"] == "/default/secrets.json"
            assert service.config["credentials_file"] == "/default/credentials.json"


class TestGoogleCalendarServiceInitializeLifecycle:
    """Tests for GoogleCalendarService.initialize()."""

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_initialize_success(
        self,
        mock_build: MagicMock,
        mock_get_credentials: MagicMock,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        mock_verify.return_value = None
        mock_authenticate.return_value.success = True
        mock_credentials = MagicMock()
        mock_get_credentials.return_value = mock_credentials
        mock_calendar_service = MagicMock()
        mock_build.return_value = mock_calendar_service

        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is True
        assert service._initialized is True
        assert service.calendar_service is mock_calendar_service
        mock_build.assert_called_once_with(
            "calendar", "v3", credentials=mock_credentials
        )

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    def test_initialize_auth_error(
        self, mock_authenticate: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_verify.return_value = None
        mock_authenticate.return_value.success = False
        mock_authenticate.return_value.error = "Auth error"

        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Auth error" in result.error

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    def test_initialize_credentials_error(
        self,
        mock_get_credentials: MagicMock,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        mock_verify.return_value = None
        mock_authenticate.return_value.success = True
        mock_get_credentials.side_effect = Exception("Creds error")

        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Creds error" in result.error

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_initialize_api_build_error(
        self,
        mock_build: MagicMock,
        mock_get_credentials: MagicMock,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        mock_verify.return_value = None
        mock_authenticate.return_value.success = True
        mock_get_credentials.return_value = MagicMock()
        mock_build.side_effect = Exception("API error")

        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    def test_auto_initialize_error_surfaces_from_read_call(
        self, mock_verify: MagicMock
    ) -> None:
        """A method called before initialize() auto-initializes via
        _ensure_initialized, and a real init failure (no credentials file
        wired up in this test) surfaces as an error_result rather than an
        unhandled exception."""
        mock_verify.return_value = None
        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.list_calendars()
        assert result.success is False


class TestGoogleCalendarServiceReadCalendars:
    """Tests for list_calendars / get_calendar."""

    @patch("googleapiclient.discovery.build")
    def test_list_calendars(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.calendarList().list().execute.return_value = {
            "items": [
                {"id": "primary", "summary": "Primary", "primary": True},
                {"id": "team@example.com", "summary": "Team"},
            ]
        }

        result = service.list_calendars()

        assert result.success is True
        assert result.content is not None
        assert len(result.content) == 2
        assert result.content[0].id == "primary"
        assert result.content[0].primary is True

    @patch("googleapiclient.discovery.build")
    def test_list_calendars_empty(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.calendarList().list().execute.return_value = {}

        result = service.list_calendars()

        assert result.success is True
        assert result.content == []

    @patch("googleapiclient.discovery.build")
    def test_list_calendars_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.calendarList().list().execute.side_effect = Exception(
            "boom"
        )

        result = service.list_calendars()

        assert result.success is False
        assert result.error is not None
        assert "boom" in result.error

    @patch("googleapiclient.discovery.build")
    def test_get_calendar(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.calendars().get().execute.return_value = {
            "id": "team@example.com",
            "summary": "Team",
            "timeZone": "America/Los_Angeles",
        }

        result = service.get_calendar("team@example.com")

        assert result.success is True
        assert result.content is not None
        assert result.content.id == "team@example.com"
        assert result.content.time_zone == "America/Los_Angeles"
        service.calendar_service.calendars().get.assert_called_with(
            calendarId="team@example.com"
        )

    @patch("googleapiclient.discovery.build")
    def test_get_calendar_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.calendars().get().execute.side_effect = Exception(
            "not found"
        )

        result = service.get_calendar("missing@example.com")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error


class TestGoogleCalendarServiceReadEvents:
    """Tests for list_events / get_event."""

    @patch("googleapiclient.discovery.build")
    def test_list_events(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().list().execute.return_value = {
            "items": [
                {"id": "e1", "summary": "Event 1"},
                {"id": "e2", "summary": "Event 2"},
            ]
        }

        result = service.list_events(
            time_min="2026-08-20T00:00:00Z", time_max="2026-08-27T00:00:00Z"
        )

        assert result.success is True
        assert result.content is not None
        assert len(result.content) == 2
        assert result.content[0].id == "e1"

    @patch("googleapiclient.discovery.build")
    def test_list_events_uses_default_calendar_and_max_results(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().list().execute.return_value = {"items": []}

        service.list_events()

        _, kwargs = service.calendar_service.events().list.call_args
        assert kwargs["calendarId"] == "primary"
        assert kwargs["maxResults"] == 250
        assert kwargs["singleEvents"] is True
        assert kwargs["orderBy"] == "startTime"

    @patch("googleapiclient.discovery.build")
    def test_list_events_with_query_and_explicit_calendar(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().list().execute.return_value = {"items": []}

        service.list_events(
            calendar_id="team@example.com", query="standup", max_results=10
        )

        _, kwargs = service.calendar_service.events().list.call_args
        assert kwargs["calendarId"] == "team@example.com"
        assert kwargs["q"] == "standup"
        assert kwargs["maxResults"] == 10

    @patch("googleapiclient.discovery.build")
    def test_list_events_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().list().execute.side_effect = Exception(
            "list failed"
        )

        result = service.list_events()

        assert result.success is False
        assert result.error is not None
        assert "list failed" in result.error

    @patch("googleapiclient.discovery.build")
    def test_get_event(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().get().execute.return_value = {
            "id": "e1",
            "summary": "Event 1",
        }

        result = service.get_event("e1")

        assert result.success is True
        assert result.content is not None
        assert result.content.id == "e1"
        service.calendar_service.events().get.assert_called_with(
            calendarId="primary", eventId="e1"
        )

    @patch("googleapiclient.discovery.build")
    def test_get_event_explicit_calendar(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().get().execute.return_value = {"id": "e1"}

        service.get_event("e1", calendar_id="team@example.com")

        service.calendar_service.events().get.assert_called_with(
            calendarId="team@example.com", eventId="e1"
        )

    @patch("googleapiclient.discovery.build")
    def test_get_event_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().get().execute.side_effect = Exception(
            "not found"
        )

        result = service.get_event("missing")

        assert result.success is False
        assert result.error is not None


class TestGoogleCalendarServiceWriteEvents:
    """Tests for create_event / update_event / delete_event."""

    @patch("googleapiclient.discovery.build")
    def test_create_event(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().insert().execute.return_value = {
            "id": "new-event",
            "summary": "Team sync",
        }

        result = service.create_event(
            summary="Team sync",
            start={"dateTime": "2026-08-21T10:00:00Z"},
            end={"dateTime": "2026-08-21T10:30:00Z"},
            description="Weekly sync",
            location="Room 1",
            attendees=[{"email": "a@example.com"}],
        )

        assert result.success is True
        assert result.content is not None
        assert result.content.id == "new-event"

        _, kwargs = service.calendar_service.events().insert.call_args
        assert kwargs["calendarId"] == "primary"
        body = kwargs["body"]
        assert body["summary"] == "Team sync"
        assert body["description"] == "Weekly sync"
        assert body["location"] == "Room 1"
        assert body["attendees"] == [{"email": "a@example.com"}]

    @patch("googleapiclient.discovery.build")
    def test_create_event_minimal(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().insert().execute.return_value = {
            "id": "new-event",
            "summary": "Quick sync",
        }

        result = service.create_event(
            summary="Quick sync",
            start={"date": "2026-08-21"},
            end={"date": "2026-08-22"},
        )

        assert result.success is True
        _, kwargs = service.calendar_service.events().insert.call_args
        body = kwargs["body"]
        assert "description" not in body
        assert "attendees" not in body

    @patch("googleapiclient.discovery.build")
    def test_create_event_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().insert().execute.side_effect = Exception(
            "insert failed"
        )

        result = service.create_event(
            summary="Sync", start={"date": "2026-08-21"}, end={"date": "2026-08-22"}
        )

        assert result.success is False
        assert result.error is not None
        assert "insert failed" in result.error

    @patch("googleapiclient.discovery.build")
    def test_update_event_merges_with_current(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().get().execute.return_value = {
            "id": "e1",
            "summary": "Old title",
            "start": {"date": "2026-08-21"},
            "end": {"date": "2026-08-22"},
            "location": "Old location",
        }
        service.calendar_service.events().update().execute.return_value = {
            "id": "e1",
            "summary": "New title",
            "start": {"date": "2026-08-21"},
            "end": {"date": "2026-08-22"},
            "location": "Old location",
        }

        result = service.update_event(event_id="e1", summary="New title")

        assert result.success is True
        assert result.content is not None
        assert result.content.summary == "New title"

        _, kwargs = service.calendar_service.events().update.call_args
        assert kwargs["eventId"] == "e1"
        assert kwargs["body"]["location"] == "Old location"
        assert kwargs["body"]["summary"] == "New title"

    @patch("googleapiclient.discovery.build")
    def test_update_event_get_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().get().execute.side_effect = Exception(
            "not found"
        )

        result = service.update_event(event_id="missing", summary="New title")

        assert result.success is False
        assert result.error is not None

    @patch("googleapiclient.discovery.build")
    def test_update_event_update_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().get().execute.return_value = {"id": "e1"}
        service.calendar_service.events().update().execute.side_effect = Exception(
            "update failed"
        )

        result = service.update_event(event_id="e1", summary="New title")

        assert result.success is False
        assert result.error is not None
        assert "update failed" in result.error

    @patch("googleapiclient.discovery.build")
    def test_delete_event(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)

        result = service.delete_event("e1")

        assert result.success is True
        assert result.content is True
        service.calendar_service.events().delete.assert_called_with(
            calendarId="primary", eventId="e1"
        )

    @patch("googleapiclient.discovery.build")
    def test_delete_event_explicit_calendar(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)

        service.delete_event("e1", calendar_id="team@example.com")

        service.calendar_service.events().delete.assert_called_with(
            calendarId="team@example.com", eventId="e1"
        )

    @patch("googleapiclient.discovery.build")
    def test_delete_event_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.calendar_service.events().delete().execute.side_effect = Exception(
            "delete failed"
        )

        result = service.delete_event("e1")

        assert result.success is False
        assert result.error is not None
        assert "delete failed" in result.error
