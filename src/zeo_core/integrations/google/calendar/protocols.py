"""
Protocol definitions for Google Calendar integration.

This module defines protocol classes for the Google Calendar service and
resource shape, ensuring proper typing throughout the codebase and avoiding
the use of Any -- mirrors `google/drive/protocols.py`'s structure and its
`GoogleCredentials` protocol, adapted to the Calendar v3 REST surface this
integration actually calls (events().list/get/insert/update/delete,
calendarList().list, calendars().get).
"""

from typing import Any, Protocol, TypeVar, runtime_checkable

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.core.results import IntegrationResult

from .models import Calendar, CalendarEvent

T = TypeVar("T")  # Generic type for result content
R = TypeVar("R", covariant=True)  # Generic type for return values


@runtime_checkable
class CalendarRequest(Protocol[R]):
    """Protocol for Google Calendar request objects."""

    def execute(self) -> R:
        """
        Execute the request.

        Returns:
            R: The API response.
        """
        ...


@runtime_checkable
class CalendarEventsResource(Protocol):
    """Protocol for the Google Calendar `events` resource."""

    def list(
        self,
        calendarId: str,
        timeMin: str | None = None,
        timeMax: str | None = None,
        maxResults: int | None = None,
        singleEvents: bool | None = None,
        orderBy: str | None = None,
        pageToken: str | None = None,
        q: str | None = None,
    ) -> CalendarRequest[dict[str, object]]:
        """
        List events on a calendar, optionally filtered by a date range.

        Args:
            calendarId: ID of the calendar to query.
            timeMin: RFC3339 lower bound (exclusive) for event end time.
            timeMax: RFC3339 upper bound (exclusive) for event start time.
            maxResults: Maximum number of events to return.
            singleEvents: Whether to expand recurring events into instances.
            orderBy: Sort order ("startTime" or "updated").
            pageToken: Token for a subsequent page of results.
            q: Free-text search query.

        Returns:
            CalendarRequest: Request object for listing events.
        """
        ...

    def get(self, calendarId: str, eventId: str) -> CalendarRequest[dict[str, object]]:
        """
        Get a single event by ID.

        Args:
            calendarId: ID of the calendar containing the event.
            eventId: ID of the event.

        Returns:
            CalendarRequest: Request object for getting the event.
        """
        ...

    def insert(
        self, calendarId: str, body: dict[str, object]
    ) -> CalendarRequest[dict[str, object]]:
        """
        Create a new event on a calendar.

        Args:
            calendarId: ID of the calendar to create the event on.
            body: Event resource body.

        Returns:
            CalendarRequest: Request object for creating the event.
        """
        ...

    def update(
        self, calendarId: str, eventId: str, body: dict[str, object]
    ) -> CalendarRequest[dict[str, object]]:
        """
        Update an existing event.

        Args:
            calendarId: ID of the calendar containing the event.
            eventId: ID of the event to update.
            body: Updated event resource body.

        Returns:
            CalendarRequest: Request object for updating the event.
        """
        ...

    def delete(self, calendarId: str, eventId: str) -> CalendarRequest[None]:
        """
        Delete an event.

        Args:
            calendarId: ID of the calendar containing the event.
            eventId: ID of the event to delete.

        Returns:
            CalendarRequest: Request object for deleting the event.
        """
        ...


@runtime_checkable
class CalendarListResource(Protocol):
    """Protocol for the Google Calendar `calendarList` resource."""

    def list(self, pageToken: str | None = None) -> CalendarRequest[dict[str, object]]:
        """
        List calendars on the authenticated user's calendar list.

        Args:
            pageToken: Token for a subsequent page of results.

        Returns:
            CalendarRequest: Request object for listing calendars.
        """
        ...


@runtime_checkable
class CalendarsResource(Protocol):
    """Protocol for the Google Calendar `calendars` resource."""

    def get(self, calendarId: str) -> CalendarRequest[dict[str, object]]:
        """
        Get a single calendar's metadata.

        Args:
            calendarId: ID of the calendar.

        Returns:
            CalendarRequest: Request object for getting the calendar.
        """
        ...


@runtime_checkable
class CalendarService(Protocol):
    """Protocol for the Google Calendar API service (the object
    `googleapiclient.discovery.build("calendar", "v3", ...)` returns)."""

    def events(self) -> CalendarEventsResource:
        """
        Get the events resource.

        Returns:
            CalendarEventsResource: The events resource.
        """
        ...

    def calendarList(self) -> CalendarListResource:  # noqa: N802 -- matches the real googleapiclient method name verbatim, see per-file-ignore
        """
        Get the calendarList resource.

        Returns:
            CalendarListResource: The calendarList resource.
        """
        ...

    def calendars(self) -> CalendarsResource:
        """
        Get the calendars resource.

        Returns:
            CalendarsResource: The calendars resource.
        """
        ...


@runtime_checkable
class GoogleCredentials(Protocol):
    """Protocol for Google API credentials."""

    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]


@runtime_checkable
class CalendarIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for the Google Calendar integration's public surface.

    There is no ready-made "calendar" or generic read+write-CRUD protocol on
    `integrations/core/protocols.py` to reuse (`StorageIntegrationProtocol`
    there is upload/download/list/create_folder -- file-storage shaped, not
    calendar shaped). Built fresh here, following `notion/protocols.py`'s
    `NotionIntegrationProtocol` precedent: a `@runtime_checkable` Protocol
    subclassing `IntegrationProtocol`, read methods first, write methods
    second.
    """

    # -- Read --

    def list_calendars(self) -> IntegrationResult[list[Calendar]]:
        """List calendars on the authenticated user's calendar list."""
        ...

    def get_calendar(self, calendar_id: str) -> IntegrationResult[Calendar]:
        """Retrieve a single calendar's metadata."""
        ...

    def list_events(
        self,
        calendar_id: str | None = None,
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int | None = None,
        query: str | None = None,
    ) -> IntegrationResult[list[CalendarEvent]]:
        """List events on a calendar, optionally filtered by date range."""
        ...

    def get_event(
        self, event_id: str, calendar_id: str | None = None
    ) -> IntegrationResult[CalendarEvent]:
        """Retrieve a single event by ID."""
        ...

    # -- Write --

    def create_event(
        self,
        summary: str,
        start: dict[str, Any],
        end: dict[str, Any],
        calendar_id: str | None = None,
        description: str | None = None,
        location: str | None = None,
        attendees: list[dict[str, Any]] | None = None,
    ) -> IntegrationResult[CalendarEvent]:
        """Create a new event on a calendar."""
        ...

    def update_event(
        self,
        event_id: str,
        calendar_id: str | None = None,
        summary: str | None = None,
        start: dict[str, Any] | None = None,
        end: dict[str, Any] | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> IntegrationResult[CalendarEvent]:
        """Update an existing event's fields."""
        ...

    def delete_event(
        self, event_id: str, calendar_id: str | None = None
    ) -> IntegrationResult[bool]:
        """Delete an event from a calendar."""
        ...
