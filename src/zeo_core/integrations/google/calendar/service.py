"""
Google Calendar integration service for zeo_core.

This module provides the main service class for Google Calendar
integration, handling calendar listing and event CRUD.

Structural precedent: `google/drive/service.py` (CRUD-over-a-resource, OAuth
auth, same config/auth-provider construction, same `initialize()` shape --
`super().initialize()` first, then `googleapiclient.discovery.build(...)`
inside a `ZeoApiError` try/except).

Design decision, made explicitly rather than presupposed (per the spawn
directive's own instruction to form independent judgment): drive/operations/*.py
exists as a set of free functions duplicating logic that already lives
inline in drive/service.py's own methods -- confirmed by grepping the whole
repo (`grep -rn "drive.operations"` in src/, tests/, examples/, docs/)
that nothing outside drive's own operations/ package and drive's own test
suite ever imports it; `service.py` itself never calls into it. That is
dead/unwired duplication, not a real factoring win, and this integration
does not replicate it: every Calendar method below is implemented directly
in this file, with no parallel `operations/` package. (Drive's own
operations/ dead code is a foreign, pre-existing gap -- named in this
stream's SOW restaufwand, not fixed here, per circle-of-control.)
"""

import logging
from typing import Any

from zeo_core.core.errors import (
    ZeoApiError,
    ZeoBaseAuthError,
    ZeoIntegrationError,
)
from zeo_core.integrations.core.base import BaseIntegrationService
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.google.auth import GoogleAuthProvider
from zeo_core.integrations.google.calendar.models import Calendar, CalendarEvent
from zeo_core.integrations.google.calendar.protocols import (
    CalendarIntegrationProtocol,
)
from zeo_core.integrations.google.config import GoogleConfigProvider

NoneType = type(None)


class GoogleCalendarService(BaseIntegrationService, CalendarIntegrationProtocol):
    """Integration service for Google Calendar."""

    SCOPES: list[str] = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    def __init__(
        self,
        client_secrets_file: str | None = None,
        credentials_file: str | None = None,
        calendar_id: str | None = None,
        config_path: str | None = None,
        scopes: list[str] | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Initialize the Google Calendar integration service.

        Args:
            client_secrets_file: Path to client secrets file.
            credentials_file: Path to credentials file.
            calendar_id: Default calendar ID to operate against.
            config_path: Path to configuration file.
            scopes: OAuth scopes for API access.
            log_level: Logging level.
        """
        config_provider = GoogleConfigProvider("calendar", log_level)
        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        # Config resolution (and the GoogleAuthProvider construction that
        # depends on it) is deferred to initialize(), matching
        # google/mail/service.py's pattern -- __init__ must not raise for a
        # caller who has no config file yet and intends to supply one before
        # calling initialize(). Doing this work here instead made
        # construction from a fresh directory with no config raise
        # unconditionally (RULING-409 s3), which is the defect this SOW
        # exists to remove.
        self._init_client_secrets_file = client_secrets_file
        self._init_credentials_file = credentials_file
        self._init_calendar_id = calendar_id
        self.config: dict[str, Any] = {}
        self.scopes: list[str] = scopes or self.SCOPES
        self.auth_provider: GoogleAuthProvider | None = None
        self.calendar_service: Any = None
        self.default_calendar_id: str = calendar_id or "primary"

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "GoogleCalendar"

    def _initialize_config(
        self,
        client_secrets_file: str | None,
        credentials_file: str | None,
        calendar_id: str | None,
    ) -> dict[str, Any]:
        """
        Initialize configuration from parameters or config file.

        Args:
            client_secrets_file: Path to client secrets file.
            credentials_file: Path to credentials file.
            calendar_id: Default calendar ID to operate against.

        Returns:
            dict: Configuration dictionary.

        Raises:
            ZeoIntegrationError: If configuration initialization fails.
        """
        from zeo_core.core.errors import ZeoIntegrationError

        if client_secrets_file and credentials_file:
            return {
                "client_secrets_file": client_secrets_file,
                "credentials_file": credentials_file,
                "calendar_id": calendar_id or "primary",
            }

        # self.config_provider is typed ConfigProviderProtocol | None on the
        # base class, but __init__ (a few lines above this call) always
        # constructs and passes a real GoogleConfigProvider before
        # _initialize_config runs -- never None for this concrete class.
        # Narrow explicitly (matching drive/service.py's identical
        # precedent) rather than assert.
        if self.config_provider is None:
            raise ZeoIntegrationError(
                "GoogleCalendarService has no config_provider configured"
            )

        config_result = self.config_provider.load_config(self.config_path)
        if not config_result.success or not config_result.content:
            default_config = self.config_provider.get_default_config()
            if not self.config_provider.validate_config(default_config):
                raise ZeoIntegrationError(
                    "Failed to load configuration and default configuration is invalid",
                    {"provider": self.config_provider.name},
                )
            return default_config

        config = config_result.content
        if client_secrets_file:
            config["client_secrets_file"] = client_secrets_file
        if credentials_file:
            config["credentials_file"] = credentials_file
        if calendar_id:
            config["calendar_id"] = calendar_id
        return config

    def initialize(self) -> IntegrationResult[NoneType]:
        """
        Initialize the Google Calendar service.

        Returns:
            IntegrationResult: Result of initialization.
        """
        try:
            # Config resolution and GoogleAuthProvider construction are
            # deferred here from __init__ (matching google/mail/service.py
            # and google/drive/service.py) so that a caller with no config
            # file yet can still construct the service and supply one
            # before calling initialize(). This runs BEFORE
            # super().initialize() -- not after, unlike mail -- because
            # base.py's own initialize() independently attempts
            # config_provider.load_config() whenever self.config is still
            # falsy, which would otherwise force a config FILE to exist on
            # disk even when the caller passed explicit client_secrets_file/
            # credentials_file params, breaking the already-supported
            # explicit-params path (confirmed failing empirically before
            # this ordering fix: this service's own existing test suite,
            # which constructs with explicit params and no config file,
            # failed with "Configuration file not found" once
            # super().initialize() ran first). Populating self.config here
            # first makes base.py's `if not self.config` guard skip its own
            # load attempt.
            if not self._initialized:
                try:
                    self.config = self._initialize_config(
                        self._init_client_secrets_file,
                        self._init_credentials_file,
                        self._init_calendar_id,
                    )
                except ZeoIntegrationError as e:
                    self.logger.error(f"Failed to initialize configuration: {e}")
                    return IntegrationResult.error_result(
                        f"Failed to initialize configuration: {e}"
                    )
                self.default_calendar_id = self.config.get("calendar_id") or "primary"
                self.auth_provider = GoogleAuthProvider(
                    client_secrets_file=self.config["client_secrets_file"],
                    credentials_file=self.config["credentials_file"],
                    scopes=self.scopes,
                    log_level=self.log_level,
                )

            init_result = super().initialize()
            if not init_result.success:
                return init_result

            # self.auth_provider is typed AuthProviderProtocol | None on the
            # base class, but is always constructed above, a few lines into
            # this method, before this point can run -- never None here.
            # Narrow explicitly, same reasoning as drive/service.py's
            # identical guard.
            if self.auth_provider is None:
                return IntegrationResult.error_result(
                    "GoogleCalendarService has no auth_provider configured"
                )

            try:
                credentials = self.auth_provider.get_credentials()
            except ZeoBaseAuthError as auth_error:
                self.logger.error(f"Authentication failed: {auth_error}")
                return IntegrationResult.error_result(
                    f"Failed to authenticate with Google Calendar: {auth_error}"
                )

            try:
                from googleapiclient.discovery import build

                self.calendar_service = build("calendar", "v3", credentials=credentials)
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to initialize Google Calendar API: {api_error}",
                    service="Google Calendar",
                    api_method="build",
                    original_error=api_error,
                ) from api_error

            self._initialized = True
            return IntegrationResult.success_result(
                message="Google Calendar service initialized successfully"
            )

        except ZeoApiError as e:
            self.logger.error(f"API error during initialization: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during initialization: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Calendar service: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize Google Calendar service: {e}"
            )

    def _resolve_calendar_id(self, calendar_id: str | None) -> str:
        """Resolve the calendar id to operate against: an explicit
        argument wins, else the service's configured default."""
        return calendar_id or self.default_calendar_id

    # ------------------------------------------------------------------
    # Read: calendars
    # ------------------------------------------------------------------

    def list_calendars(self) -> IntegrationResult[list[Calendar]]:
        """
        List calendars on the authenticated user's calendar list.

        Returns:
            IntegrationResult with the list of calendars.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            try:
                response = self.calendar_service.calendarList().list().execute()
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to list calendars from Google Calendar: {api_error}",
                    service="Google Calendar",
                    api_method="calendarList.list",
                    original_error=api_error,
                ) from api_error

            calendars = [
                Calendar.from_api_response(item) for item in response.get("items", [])
            ]
            return IntegrationResult.success_result(
                content=calendars, message=f"Listed {len(calendars)} calendars"
            )

        except ZeoApiError as e:
            self.logger.error(f"API error during listing calendars: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during listing calendars: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to list calendars: {e}")
            return IntegrationResult.error_result(
                f"Failed to list calendars from Google Calendar: {e}"
            )

    def get_calendar(self, calendar_id: str) -> IntegrationResult[Calendar]:
        """
        Retrieve a single calendar's metadata.

        Args:
            calendar_id: ID of the calendar.

        Returns:
            IntegrationResult with the calendar.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            try:
                response = (
                    self.calendar_service.calendars()
                    .get(calendarId=calendar_id)
                    .execute()
                )
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to get calendar from Google Calendar: {api_error}",
                    service="Google Calendar",
                    api_method="calendars.get",
                    original_error=api_error,
                ) from api_error

            calendar = Calendar.from_api_response(response)
            return IntegrationResult.success_result(
                content=calendar, message=f"Retrieved calendar {calendar.id}"
            )

        except ZeoApiError as e:
            self.logger.error(f"API error during getting calendar: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during getting calendar: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get calendar: {e}")
            return IntegrationResult.error_result(
                f"Failed to get calendar from Google Calendar: {e}"
            )

    # ------------------------------------------------------------------
    # Read: events
    # ------------------------------------------------------------------

    def list_events(
        self,
        calendar_id: str | None = None,
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int | None = None,
        query: str | None = None,
    ) -> IntegrationResult[list[CalendarEvent]]:
        """
        List events on a calendar, optionally filtered by a date range.

        Args:
            calendar_id: ID of the calendar to query (defaults to the
                service's configured default, itself "primary" unless set).
            time_min: RFC3339 lower bound (exclusive) for event end time.
            time_max: RFC3339 upper bound (exclusive) for event start time.
            max_results: Maximum number of events to return (defaults to
                the configured max_results).
            query: Optional free-text search query.

        Returns:
            IntegrationResult with the list of events.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            resolved_calendar_id = self._resolve_calendar_id(calendar_id)
            resolved_max_results = max_results or self.config.get("max_results", 250)

            list_kwargs: dict[str, Any] = {
                "calendarId": resolved_calendar_id,
                "maxResults": resolved_max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if time_min:
                list_kwargs["timeMin"] = time_min
            if time_max:
                list_kwargs["timeMax"] = time_max
            if query:
                list_kwargs["q"] = query

            try:
                response = self.calendar_service.events().list(**list_kwargs).execute()
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to list events from Google Calendar: {api_error}",
                    service="Google Calendar",
                    api_method="events.list",
                    original_error=api_error,
                ) from api_error

            events = [
                CalendarEvent.from_api_response(item)
                for item in response.get("items", [])
            ]
            return IntegrationResult.success_result(
                content=events, message=f"Listed {len(events)} events"
            )

        except ZeoApiError as e:
            self.logger.error(f"API error during listing events: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during listing events: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to list events: {e}")
            return IntegrationResult.error_result(
                f"Failed to list events from Google Calendar: {e}"
            )

    def get_event(
        self, event_id: str, calendar_id: str | None = None
    ) -> IntegrationResult[CalendarEvent]:
        """
        Retrieve a single event by ID.

        Args:
            event_id: ID of the event.
            calendar_id: ID of the calendar containing the event (defaults
                to the service's configured default).

        Returns:
            IntegrationResult with the event.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            resolved_calendar_id = self._resolve_calendar_id(calendar_id)
            try:
                response = (
                    self.calendar_service.events()
                    .get(calendarId=resolved_calendar_id, eventId=event_id)
                    .execute()
                )
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to get event from Google Calendar: {api_error}",
                    service="Google Calendar",
                    api_method="events.get",
                    original_error=api_error,
                ) from api_error

            event = CalendarEvent.from_api_response(response)
            return IntegrationResult.success_result(
                content=event, message=f"Retrieved event {event.id}"
            )

        except ZeoApiError as e:
            self.logger.error(f"API error during getting event: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during getting event: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get event: {e}")
            return IntegrationResult.error_result(
                f"Failed to get event from Google Calendar: {e}"
            )

    # ------------------------------------------------------------------
    # Write: events
    # ------------------------------------------------------------------

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
        """
        Create a new event on a calendar.

        Args:
            summary: Event title.
            start: Start time, Calendar API shape (`{"dateTime": ...,
                "timeZone": ...}` or `{"date": "YYYY-MM-DD"}`).
            end: End time, same shape as `start`.
            calendar_id: ID of the calendar to create the event on
                (defaults to the service's configured default).
            description: Optional event description.
            location: Optional event location.
            attendees: Optional list of `{"email": ...}` attendee dicts.

        Returns:
            IntegrationResult with the created event.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            resolved_calendar_id = self._resolve_calendar_id(calendar_id)
            body: dict[str, Any] = {"summary": summary, "start": start, "end": end}
            if description is not None:
                body["description"] = description
            if location is not None:
                body["location"] = location
            if attendees is not None:
                body["attendees"] = attendees

            try:
                response = (
                    self.calendar_service.events()
                    .insert(calendarId=resolved_calendar_id, body=body)
                    .execute()
                )
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to create event in Google Calendar: {api_error}",
                    service="Google Calendar",
                    api_method="events.insert",
                    original_error=api_error,
                ) from api_error

            event = CalendarEvent.from_api_response(response)
            return IntegrationResult.success_result(
                content=event, message=f"Created event {event.id}"
            )

        except ZeoApiError as e:
            self.logger.error(f"API error during creating event: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during creating event: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create event: {e}")
            return IntegrationResult.error_result(
                f"Failed to create event in Google Calendar: {e}"
            )

    def _merge_event_update_fields(
        self,
        current: dict[str, Any],
        summary: str | None,
        start: dict[str, Any] | None,
        end: dict[str, Any] | None,
        description: str | None,
        location: str | None,
    ) -> dict[str, Any]:
        """Merge the caller's changed fields onto the current event body
        (in place, and returned for chaining) -- extracted from
        update_event to keep its own branch count under the C901
        threshold, same reasoning as google/config.py's
        _apply_nested_integrations_google/_apply_direct_service_key split;
        behavior unchanged from the original inline block."""
        if summary is not None:
            current["summary"] = summary
        if start is not None:
            current["start"] = start
        if end is not None:
            current["end"] = end
        if description is not None:
            current["description"] = description
        if location is not None:
            current["location"] = location
        return current

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
        """
        Update an existing event's fields (patch semantics: unset
        parameters are left unmodified via a get-then-update round-trip,
        matching `events.update`'s own full-resource-body requirement --
        the Calendar API's `update` verb requires a full event body, not
        a partial one, so this reads the current event first and merges).

        Args:
            event_id: ID of the event to update.
            calendar_id: ID of the calendar containing the event (defaults
                to the service's configured default).
            summary: New event title, if changing.
            start: New start time, if changing.
            end: New end time, if changing.
            description: New description, if changing.
            location: New location, if changing.

        Returns:
            IntegrationResult with the updated event.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            resolved_calendar_id = self._resolve_calendar_id(calendar_id)

            try:
                current = (
                    self.calendar_service.events()
                    .get(calendarId=resolved_calendar_id, eventId=event_id)
                    .execute()
                )
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to load event before update from Google Calendar: "
                    f"{api_error}",
                    service="Google Calendar",
                    api_method="events.get",
                    original_error=api_error,
                ) from api_error

            current = self._merge_event_update_fields(
                current, summary, start, end, description, location
            )

            try:
                response = (
                    self.calendar_service.events()
                    .update(
                        calendarId=resolved_calendar_id,
                        eventId=event_id,
                        body=current,
                    )
                    .execute()
                )
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to update event in Google Calendar: {api_error}",
                    service="Google Calendar",
                    api_method="events.update",
                    original_error=api_error,
                ) from api_error

            event = CalendarEvent.from_api_response(response)
            return IntegrationResult.success_result(
                content=event, message=f"Updated event {event.id}"
            )

        except ZeoApiError as e:
            self.logger.error(f"API error during updating event: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during updating event: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to update event: {e}")
            return IntegrationResult.error_result(
                f"Failed to update event in Google Calendar: {e}"
            )

    def delete_event(
        self, event_id: str, calendar_id: str | None = None
    ) -> IntegrationResult[bool]:
        """
        Delete an event from a calendar.

        Args:
            event_id: ID of the event to delete.
            calendar_id: ID of the calendar containing the event (defaults
                to the service's configured default).

        Returns:
            IntegrationResult indicating success.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            resolved_calendar_id = self._resolve_calendar_id(calendar_id)
            try:
                self.calendar_service.events().delete(
                    calendarId=resolved_calendar_id, eventId=event_id
                ).execute()
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to delete event from Google Calendar: {api_error}",
                    service="Google Calendar",
                    api_method="events.delete",
                    original_error=api_error,
                ) from api_error

            return IntegrationResult.success_result(
                content=True, message=f"Event deleted successfully: {event_id}"
            )

        except ZeoApiError as e:
            self.logger.error(f"API error during deleting event: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during deleting event: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to delete event: {e}")
            return IntegrationResult.error_result(
                f"Failed to delete event from Google Calendar: {e}"
            )
