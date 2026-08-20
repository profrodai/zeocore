# zeocore 0.3.0

A focused, purely additive release: one new integration, no breaking changes, no removals.

## What's new

**Google Calendar integration** (`zeocore[calendar]`) — full read and write against the
Calendar v3 API: `list_calendars`/`get_calendar`, `list_events` (date-range filtering via
`time_min`/`time_max`)/`get_event`, and `create_event`/`update_event`/`delete_event`. Reuses the
same OAuth (`InstalledAppFlow` + local-server) flow and `GoogleAuthProvider`/`GoogleConfigProvider`
the Drive and Gmail integrations already use — no new auth or config mechanism introduced. See
`examples/calendar_usage.py` and `docs/tutorials/calendar-integration.md`.

`zeo_core.integrations.google` now also re-exports `GoogleCalendarService`, `Calendar`, and
`CalendarEvent` at the shallow path, alongside the existing `GoogleDriveService`/
`GoogleMailService` re-exports.

## Named, not fixed

Two pre-existing gaps were found while building the Calendar integration and are recorded here
rather than silently fixed (out of this release's own scope):

- `zeo_core.integrations.google.drive.operations/*` is dead code — nothing outside drive's own
  test suite imports it; `drive/service.py`'s public methods duplicate the same logic inline.
  Pre-existing; the Calendar integration does not replicate this pattern.
- `GoogleDriveService`'s and `GoogleCalendarService`'s real `integration_id` property
  (`"googledrive"`/`"googlecalendar"`) does not match the dotted `pyproject.toml` entry-point
  table key (`"google.drive"`/`"google.calendar"`) — a pre-existing naming mismatch, confirmed
  identical for `GoogleDriveService`, not introduced by this release.

## Upgrading

```bash
pip install --upgrade zeocore
```

No breaking changes in this release — upgrading from `0.2.x` requires no code changes.

Full diff: https://github.com/zeroemployeeorg/zeocore/compare/v0.2.0...v0.3.0
