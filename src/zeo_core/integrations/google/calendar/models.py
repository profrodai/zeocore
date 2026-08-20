"""
Data models for Google Calendar integration.

This module provides Pydantic models for Google Calendar events and
calendars, standardizing the representation of Calendar resources, mirroring
`google/drive/models.py`'s `from_api_response(cls, response: dict) ->
Model` convention with the same defensive date/int parsing.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventDateTime(BaseModel):
    """Model for a Calendar event's start/end time.

    Google Calendar events are either timed (`dateTime` + `timeZone`) or
    all-day (`date` only, no time component) -- both fields are kept
    optional and a caller checks which is populated, mirroring the real API
    response shape rather than collapsing the distinction.
    """

    date_time: datetime | None = Field(
        None, description="RFC3339 timestamp for a timed event"
    )
    date: str | None = Field(
        None, description="ISO 8601 date (YYYY-MM-DD) for an all-day event"
    )
    time_zone: str | None = Field(
        None, description="IANA time zone for date_time, if set"
    )

    @classmethod
    def from_api_response(cls, response: dict[str, Any] | None) -> "EventDateTime":
        """Build an EventDateTime from a Calendar API start/end sub-object."""
        if not response:
            return cls()

        date_time = None
        if "dateTime" in response and response["dateTime"]:
            try:
                date_time = datetime.fromisoformat(
                    response["dateTime"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        return cls(
            date_time=date_time,
            date=response.get("date"),
            time_zone=response.get("timeZone"),
        )

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize back to the Calendar API's start/end sub-object shape."""
        result: dict[str, Any] = {}
        if self.date_time is not None:
            result["dateTime"] = self.date_time.isoformat()
            if self.time_zone:
                result["timeZone"] = self.time_zone
        elif self.date is not None:
            result["date"] = self.date
        return result


class EventAttendee(BaseModel):
    """Model for a Calendar event attendee."""

    email: str = Field(..., description="Attendee email address")
    display_name: str | None = Field(None, description="Attendee display name")
    response_status: str = Field(
        "needsAction",
        description="RSVP status (needsAction, declined, tentative, accepted)",
    )
    optional: bool = Field(False, description="Whether attendance is optional")
    organizer: bool = Field(False, description="Whether this attendee is the organizer")

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> "EventAttendee":
        """Create an EventAttendee from a Calendar API attendee entry."""
        return cls(
            email=response.get("email", ""),
            display_name=response.get("displayName"),
            response_status=response.get("responseStatus", "needsAction"),
            optional=response.get("optional", False),
            organizer=response.get("organizer", False),
        )

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize back to the Calendar API's attendee entry shape."""
        result: dict[str, Any] = {"email": self.email}
        if self.display_name:
            result["displayName"] = self.display_name
        if self.optional:
            result["optional"] = self.optional
        return result


class CalendarEvent(BaseModel):
    """Model for a Google Calendar event."""

    id: str = Field(..., description="Event ID")
    status: str = Field("confirmed", description="Event status")
    summary: str = Field("", description="Event title")
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location")
    start: EventDateTime = Field(
        default_factory=EventDateTime, description="Event start time"
    )
    end: EventDateTime = Field(
        default_factory=EventDateTime, description="Event end time"
    )
    attendees: list[EventAttendee] = Field(
        default_factory=list, description="Event attendees"
    )
    organizer_email: str | None = Field(None, description="Organizer's email address")
    html_link: str | None = Field(
        None, description="Link to the event in Google Calendar"
    )
    created: datetime | None = Field(None, description="Creation time")
    updated: datetime | None = Field(None, description="Last modification time")
    recurring_event_id: str | None = Field(
        None, description="ID of the recurring event this is an instance of"
    )

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> "CalendarEvent":
        """
        Create a CalendarEvent instance from a Google Calendar API response.

        Args:
            response: Google Calendar API event resource dictionary.

        Returns:
            CalendarEvent: Event information.
        """
        created = None
        if "created" in response:
            try:
                created = datetime.fromisoformat(
                    response["created"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        updated = None
        if "updated" in response:
            try:
                updated = datetime.fromisoformat(
                    response["updated"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        attendees = [
            EventAttendee.from_api_response(a)
            for a in response.get("attendees", [])
            if isinstance(a, dict)
        ]

        organizer = response.get("organizer")
        organizer_email = (
            organizer.get("email") if isinstance(organizer, dict) else None
        )

        return cls(
            id=response.get("id", ""),
            status=response.get("status", "confirmed"),
            summary=response.get("summary", ""),
            description=response.get("description"),
            location=response.get("location"),
            start=EventDateTime.from_api_response(response.get("start")),
            end=EventDateTime.from_api_response(response.get("end")),
            attendees=attendees,
            organizer_email=organizer_email,
            html_link=response.get("htmlLink"),
            created=created,
            updated=updated,
            recurring_event_id=response.get("recurringEventId"),
        )

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize to the Calendar API's event-resource request shape
        (create/update bodies) -- deliberately narrower than the full
        response shape: only fields a caller can legitimately set."""
        body: dict[str, Any] = {"summary": self.summary}
        if self.description is not None:
            body["description"] = self.description
        if self.location is not None:
            body["location"] = self.location
        start_dict = self.start.to_api_dict()
        if start_dict:
            body["start"] = start_dict
        end_dict = self.end.to_api_dict()
        if end_dict:
            body["end"] = end_dict
        if self.attendees:
            body["attendees"] = [a.to_api_dict() for a in self.attendees]
        return body


class Calendar(BaseModel):
    """Model for a Google Calendar (as returned by calendars().get() or
    calendarList().list())."""

    id: str = Field(..., description="Calendar ID")
    summary: str = Field("", description="Calendar title")
    description: str | None = Field(None, description="Calendar description")
    time_zone: str | None = Field(None, description="Calendar's IANA time zone")
    access_role: str | None = Field(
        None, description="Access role granted to the authenticated user"
    )
    primary: bool = Field(
        False, description="Whether this is the authenticated user's primary calendar"
    )

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> "Calendar":
        """
        Create a Calendar instance from a Google Calendar API response
        (either a `calendars().get()` resource or a `calendarList().list()`
        entry -- both share this same core field set).

        Args:
            response: Google Calendar API calendar resource dictionary.

        Returns:
            Calendar: Calendar information.
        """
        return cls(
            id=response.get("id", ""),
            summary=response.get("summary", ""),
            description=response.get("description"),
            time_zone=response.get("timeZone"),
            access_role=response.get("accessRole"),
            primary=response.get("primary", False),
        )
