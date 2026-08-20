"""Google Calendar integration for zeo_core.

Read + write access to Google Calendar calendars and events via the
`googleapiclient` Calendar v3 REST API, using the same OAuth
(`InstalledAppFlow` + local-server) flow as `integrations.google.drive` and
`integrations.google.mail` -- reuses `GoogleAuthProvider` and
`GoogleConfigProvider` as-is, no new auth or config mechanism invented.
Follows the same shape as `integrations.google.drive`: a shared config
model in `google/config.py`, a service class implementing
`CalendarIntegrationProtocol`, and registration under the
`zeo_core.integrations` entry-point group the same way (see this repo's
`pyproject.toml`, `[project.entry-points."zeo_core.integrations"]`, key
`google.calendar`).

Quickstart::

    from zeo_core.integrations.google.calendar import GoogleCalendarService

    calendar = GoogleCalendarService(
        client_secrets_file="config/google_client_secret.json",
        credentials_file="config/google_credentials.json",
    )
    result = calendar.initialize()
    assert result.success

    # Read: list upcoming events on the primary calendar
    events = calendar.list_events(time_min="2026-08-20T00:00:00Z")

    # Write: create an event
    tz = "America/Los_Angeles"
    created = calendar.create_event(
        summary="Team sync",
        start={"dateTime": "2026-08-21T10:00:00-07:00", "timeZone": tz},
        end={"dateTime": "2026-08-21T10:30:00-07:00", "timeZone": tz},
    )

Every call returns an `IntegrationResult[T]` (`.success`, `.content`,
`.error`) -- see `zeo_core.integrations.core.results`.
"""

from __future__ import annotations

from zeo_core.integrations.google.calendar.models import (
    Calendar,
    CalendarEvent,
    EventAttendee,
    EventDateTime,
)
from zeo_core.integrations.google.calendar.protocols import (
    CalendarIntegrationProtocol,
)
from zeo_core.integrations.google.calendar.service import GoogleCalendarService

__all__ = [
    "GoogleCalendarService",
    "Calendar",
    "CalendarEvent",
    "EventAttendee",
    "EventDateTime",
    "CalendarIntegrationProtocol",
    "create_integration",
]


def create_integration() -> CalendarIntegrationProtocol:
    """
    Create and configure a Google Calendar integration.

    This function is used as an entry point for automatic integration
    discovery.

    Returns:
        CalendarIntegrationProtocol: Configured Google Calendar service.
    """
    return GoogleCalendarService()
