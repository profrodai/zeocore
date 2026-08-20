"""Tests for Google Calendar data models."""

from datetime import datetime

from zeo_core.integrations.google.calendar.models import (
    Calendar,
    CalendarEvent,
    EventAttendee,
    EventDateTime,
)


class TestEventDateTime:
    """Tests for EventDateTime."""

    def test_from_api_response_timed(self) -> None:
        response = {
            "dateTime": "2026-08-21T10:00:00Z",
            "timeZone": "America/Los_Angeles",
        }
        dt = EventDateTime.from_api_response(response)
        assert dt.date_time is not None
        assert dt.date_time.year == 2026
        assert dt.time_zone == "America/Los_Angeles"
        assert dt.date is None

    def test_from_api_response_all_day(self) -> None:
        response = {"date": "2026-08-21"}
        dt = EventDateTime.from_api_response(response)
        assert dt.date == "2026-08-21"
        assert dt.date_time is None

    def test_from_api_response_none(self) -> None:
        dt = EventDateTime.from_api_response(None)
        assert dt.date_time is None
        assert dt.date is None

    def test_from_api_response_malformed_datetime(self) -> None:
        response = {"dateTime": "not-a-real-timestamp"}
        dt = EventDateTime.from_api_response(response)
        assert dt.date_time is None

    def test_to_api_dict_timed(self) -> None:
        dt = EventDateTime(
            date_time=datetime(2026, 8, 21, 10, 0, 0), time_zone="America/Los_Angeles"
        )
        result = dt.to_api_dict()
        assert "dateTime" in result
        assert result["timeZone"] == "America/Los_Angeles"

    def test_to_api_dict_all_day(self) -> None:
        dt = EventDateTime(date="2026-08-21")
        result = dt.to_api_dict()
        assert result == {"date": "2026-08-21"}

    def test_to_api_dict_empty(self) -> None:
        dt = EventDateTime()
        assert dt.to_api_dict() == {}


class TestEventAttendee:
    """Tests for EventAttendee."""

    def test_from_api_response(self) -> None:
        response = {
            "email": "person@example.com",
            "displayName": "Person",
            "responseStatus": "accepted",
            "optional": True,
            "organizer": False,
        }
        attendee = EventAttendee.from_api_response(response)
        assert attendee.email == "person@example.com"
        assert attendee.display_name == "Person"
        assert attendee.response_status == "accepted"
        assert attendee.optional is True

    def test_from_api_response_defaults(self) -> None:
        attendee = EventAttendee.from_api_response({"email": "a@example.com"})
        assert attendee.response_status == "needsAction"
        assert attendee.optional is False
        assert attendee.organizer is False

    def test_to_api_dict(self) -> None:
        attendee = EventAttendee(email="a@example.com", display_name="A", optional=True)
        result = attendee.to_api_dict()
        assert result == {
            "email": "a@example.com",
            "displayName": "A",
            "optional": True,
        }

    def test_to_api_dict_minimal(self) -> None:
        attendee = EventAttendee(email="a@example.com")
        assert attendee.to_api_dict() == {"email": "a@example.com"}


class TestCalendarEvent:
    """Tests for CalendarEvent."""

    def test_from_api_response_full(self) -> None:
        response = {
            "id": "event123",
            "status": "confirmed",
            "summary": "Team sync",
            "description": "Weekly sync",
            "location": "Room 1",
            "start": {"dateTime": "2026-08-21T10:00:00Z"},
            "end": {"dateTime": "2026-08-21T10:30:00Z"},
            "attendees": [{"email": "a@example.com"}],
            "organizer": {"email": "organizer@example.com"},
            "htmlLink": "https://calendar.google.com/event?eid=abc",
            "created": "2026-08-01T00:00:00Z",
            "updated": "2026-08-02T00:00:00Z",
            "recurringEventId": "recur123",
        }
        event = CalendarEvent.from_api_response(response)
        assert event.id == "event123"
        assert event.summary == "Team sync"
        assert event.description == "Weekly sync"
        assert event.location == "Room 1"
        assert len(event.attendees) == 1
        assert event.attendees[0].email == "a@example.com"
        assert event.organizer_email == "organizer@example.com"
        assert event.html_link == "https://calendar.google.com/event?eid=abc"
        assert event.created is not None
        assert event.updated is not None
        assert event.recurring_event_id == "recur123"

    def test_from_api_response_minimal(self) -> None:
        event = CalendarEvent.from_api_response({"id": "event123"})
        assert event.id == "event123"
        assert event.summary == ""
        assert event.status == "confirmed"
        assert event.attendees == []
        assert event.organizer_email is None

    def test_from_api_response_malformed_dates(self) -> None:
        response = {
            "id": "event123",
            "created": "not-a-date",
            "updated": "also-not-a-date",
        }
        event = CalendarEvent.from_api_response(response)
        assert event.created is None
        assert event.updated is None

    def test_from_api_response_organizer_not_dict(self) -> None:
        event = CalendarEvent.from_api_response({"id": "e1", "organizer": "not-a-dict"})
        assert event.organizer_email is None

    def test_from_api_response_ignores_non_dict_attendees(self) -> None:
        event = CalendarEvent.from_api_response(
            {"id": "e1", "attendees": ["not-a-dict", {"email": "a@example.com"}]}
        )
        assert len(event.attendees) == 1

    def test_to_api_dict_full(self) -> None:
        event = CalendarEvent(
            id="e1",
            summary="Sync",
            description="desc",
            location="loc",
            start=EventDateTime(date="2026-08-21"),
            end=EventDateTime(date="2026-08-22"),
            attendees=[EventAttendee(email="a@example.com")],
        )
        body = event.to_api_dict()
        assert body["summary"] == "Sync"
        assert body["description"] == "desc"
        assert body["location"] == "loc"
        assert body["start"] == {"date": "2026-08-21"}
        assert body["end"] == {"date": "2026-08-22"}
        assert body["attendees"] == [{"email": "a@example.com"}]

    def test_to_api_dict_minimal(self) -> None:
        event = CalendarEvent(id="e1", summary="Sync")
        body = event.to_api_dict()
        assert body == {"summary": "Sync"}


class TestCalendar:
    """Tests for Calendar."""

    def test_from_api_response_full(self) -> None:
        response = {
            "id": "cal123",
            "summary": "Work",
            "description": "Work calendar",
            "timeZone": "America/Los_Angeles",
            "accessRole": "owner",
            "primary": True,
        }
        calendar = Calendar.from_api_response(response)
        assert calendar.id == "cal123"
        assert calendar.summary == "Work"
        assert calendar.description == "Work calendar"
        assert calendar.time_zone == "America/Los_Angeles"
        assert calendar.access_role == "owner"
        assert calendar.primary is True

    def test_from_api_response_minimal(self) -> None:
        calendar = Calendar.from_api_response({"id": "cal123"})
        assert calendar.id == "cal123"
        assert calendar.summary == ""
        assert calendar.primary is False
        assert calendar.access_role is None
