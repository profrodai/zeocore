"""Tests for Google Calendar protocol definitions -- mirrors
tests/test_integrations/google/drive/test_protocols.py's structural-
conformance shape (a MagicMock built with the right attrs satisfies
isinstance() against the runtime_checkable Protocols)."""

from unittest.mock import MagicMock

from zeo_core.integrations.google.calendar.protocols import (
    CalendarEventsResource,
    CalendarListResource,
    CalendarRequest,
    CalendarService,
    CalendarsResource,
    GoogleCredentials,
)


class TestCalendarRequest:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.execute = MagicMock(return_value={})
        assert isinstance(mock, CalendarRequest)


class TestCalendarEventsResource:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.list = MagicMock()
        mock.get = MagicMock()
        mock.insert = MagicMock()
        mock.update = MagicMock()
        mock.delete = MagicMock()
        assert isinstance(mock, CalendarEventsResource)


class TestCalendarListResource:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.list = MagicMock()
        assert isinstance(mock, CalendarListResource)


class TestCalendarsResource:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.get = MagicMock()
        assert isinstance(mock, CalendarsResource)


class TestCalendarService:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.events = MagicMock()
        mock.calendarList = MagicMock()
        mock.calendars = MagicMock()
        assert isinstance(mock, CalendarService)


class TestGoogleCredentials:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.token = "tok"  # noqa: S105 -- test fixture, fake credential value
        mock.refresh_token = "refresh"  # noqa: S105 -- test fixture
        mock.token_uri = "https://oauth2.googleapis.com/token"  # noqa: S105 -- test fixture, fake credential value
        mock.client_id = "id"
        mock.client_secret = "secret"  # noqa: S105 -- test fixture
        mock.scopes = ["scope"]
        assert isinstance(mock, GoogleCredentials)
