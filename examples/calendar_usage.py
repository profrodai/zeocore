"""
Example: reading and writing Google Calendar events with
zeo_core.integrations.google.calendar.

Requires the 'calendar' extra:

    uv pip install "zeocore[calendar]"

Auth is the same OAuth (`InstalledAppFlow` + local-server) flow
`zeo_core.integrations.google.drive`/`google.mail` already use -- reused
as-is via `GoogleAuthProvider`, not a new flow. There is no single-token
shortcut the way Notion's `NOTION_TOKEN` works: a real run needs a Google
Cloud OAuth client-secrets JSON file (Google Cloud Console -> APIs &
Services -> Credentials -> "OAuth client ID", type "Desktop app") with the
Calendar API enabled on that project.

GAP NOTED (named here rather than silently invented): neither
`examples/` nor docs/README/GET-STARTED name an existing env-var
convention for a Drive/Gmail example script pointing at a client-secrets
file -- no `examples/drive_usage.py` or `examples/mail_usage.py` exists at
all to follow (checked: only notion_usage.py, jupytext_usage.py,
ffmpeg_usage.py exist as real integration examples; drive/mail have none).
This script therefore defines and documents its own env var,
`ZEO_GOOGLE_CALENDAR_CLIENT_SECRETS`, pointing at a real client-secrets
JSON file, as the graceful-skip precondition -- a sensible, self-contained
choice given no existing convention to match.

This example demonstrates the graceful-skip path (matching
examples/notion_usage.py's own pattern) when
ZEO_GOOGLE_CALENDAR_CLIENT_SECRETS isn't set: it still shows integration
construction and the real calling shapes, just without making a live API
call or running the interactive OAuth local-server flow. Set
ZEO_GOOGLE_CALENDAR_CLIENT_SECRETS to a real client-secrets file path to
see the live path run (this will open a browser for the OAuth consent
flow on first run, then cache credentials to a scratch credentials file
for subsequent runs).

Run this file directly:

    uv run examples/calendar_usage.py
    ZEO_GOOGLE_CALENDAR_CLIENT_SECRETS=/path/to/client_secrets.json \\
        uv run examples/calendar_usage.py
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from zeo_core.integrations.google.calendar import GoogleCalendarService


def main() -> None:
    """
    Initialize the Google Calendar integration and, if a real
    client-secrets file is available, run real read calls (list
    calendars, list upcoming events) and real write calls (create an
    event, update it, delete it) end to end.

    ZEO_GOOGLE_CALENDAR_CLIENT_SECRETS is checked BEFORE calling
    initialize(): the integration's own initialize() requires a real,
    existing client-secrets file to construct at all (GoogleAuthProvider's
    constructor verifies the file exists), so a missing/unset path is
    treated here as a graceful-skip precondition, not a failure to report
    from a failed construction.
    """
    client_secrets_file = os.environ.get("ZEO_GOOGLE_CALENDAR_CLIENT_SECRETS")

    if not client_secrets_file:
        print(
            "ZEO_GOOGLE_CALENDAR_CLIENT_SECRETS is not set -- skipping live "
            "initialization and API calls (graceful skip, not an error). "
            "Set it to a real OAuth client-secrets JSON file path (Google "
            "Cloud Console -> APIs & Services -> Credentials -> OAuth "
            "client ID -> Desktop app, with the Calendar API enabled) to "
            "see the live read/write calls run -- this will open a "
            "browser for the OAuth consent flow on first run."
        )
        print("\nThe calling shapes, unchanged whether live or skipped:")
        print("  calendar.list_calendars()")
        print('  calendar.list_events(time_min="2026-08-20T00:00:00Z")')
        print(
            '  calendar.create_event(summary="Team sync", '
            'start={"dateTime": "..."}, end={"dateTime": "..."})'
        )
        print('  calendar.update_event(event_id="...", summary="New title")')
        print('  calendar.delete_event(event_id="...")')
        return

    scratch_dir = Path("./tmp_calendar_example")
    scratch_dir.mkdir(exist_ok=True)
    credentials_path = scratch_dir / "google_credentials.json"

    try:
        calendar = GoogleCalendarService(
            client_secrets_file=client_secrets_file,
            credentials_file=str(credentials_path),
        )
        init_result = calendar.initialize()
        if not init_result.success:
            print(
                f"Failed to initialize Google Calendar integration: {init_result.error}"
            )
            return
        print(f"Google Calendar integration initialized: {init_result.message}")

        # Real read: list calendars on the authenticated user's calendar list.
        calendars_result = calendar.list_calendars()
        if not calendars_result.success:
            print(f"list_calendars failed: {calendars_result.error}")
            return
        calendars = calendars_result.content or []
        print(f"list_calendars() found {len(calendars)} calendar(s)")
        for cal in calendars:
            print(f"  - {cal.summary} ({cal.id})")

        # Real read: list upcoming events on the primary calendar.
        events_result = calendar.list_events(max_results=10)
        if not events_result.success:
            print(f"list_events failed: {events_result.error}")
            return
        events = events_result.content or []
        print(f"list_events() found {len(events)} upcoming event(s)")

        # Real write: create an event on the primary calendar.
        create_result = calendar.create_event(
            summary="zeocore calendar_usage.py demo",
            start={"date": "2099-01-01"},
            end={"date": "2099-01-02"},
            description="Created by zeocore's calendar_usage.py example.",
        )
        if not create_result.success:
            print(f"create_event failed: {create_result.error}")
            return
        new_event = create_result.content
        assert new_event is not None  # noqa: S101 -- success==True guarantees content
        print(f"Created event: {new_event.id}")

        # Real write: update the event we just created.
        update_result = calendar.update_event(
            event_id=new_event.id,
            summary="zeocore calendar_usage.py demo (updated)",
        )
        if update_result.success and update_result.content is not None:
            print(f"Updated event: {update_result.content.id}")
        else:
            print(f"update_event failed: {update_result.error}")

        # Real write: delete the event, cleaning up after the demo.
        delete_result = calendar.delete_event(event_id=new_event.id)
        if delete_result.success:
            print("Deleted the demo event.")
        else:
            print(f"delete_event failed: {delete_result.error}")
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
