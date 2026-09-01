# Google Calendar integration, end to end: OAuth setup through a real read + write example

**Created:** 2026-08-20 · **Status:** ACTIVE

`zeo_core.integrations.google.calendar` gives you a full read + write
surface against the Google Calendar API through zeocore's usual typed,
`IntegrationResult`-returning shape. This tutorial walks the whole path —
Google Cloud OAuth setup, the one real gotcha in getting `initialize()`
to succeed, then real calendar/event reads, and real event writes — with
every code block verified against the live source before being written
here.

Requires the `calendar` extra:

```bash
uv pip install "zeocore[calendar]"
```

## Step 1 — Google Cloud OAuth setup

Google Calendar's auth model is OAuth 2.0 (`InstalledAppFlow` + a local
redirect server), the same flow `zeo_core.integrations.google.drive` and
`google.mail` already use — `zeo_core.integrations.google.calendar` reuses
the identical `GoogleAuthProvider` rather than inventing a second flow.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/),
   create (or reuse) a project.
2. Enable the **Google Calendar API** for that project (APIs & Services →
   Library → search "Google Calendar API" → Enable).
3. Create OAuth 2.0 credentials: APIs & Services → Credentials → Create
   Credentials → OAuth client ID → Application type **Desktop app**.
4. Download the client secrets JSON file it generates — this is your
   `client_secrets_file`.

There is no single-token shortcut the way Notion's `NOTION_TOKEN` works:
the first `initialize()` call with no cached credentials opens a real
browser window for the OAuth consent flow, then caches the resulting
credentials to `credentials_file` for subsequent runs (no browser needed
again until the refresh token itself is revoked).

## Step 2 — the one real gotcha: `initialize()` needs a config file to exist (or explicit constructor args)

This mirrors the same gotcha the Notion tutorial names for
`NotionIntegration`, but the mechanism is different and worth stating
precisely: verified directly against the source
(`zeo_core/integrations/google/calendar/service.py`'s
`GoogleCalendarService.__init__` calling `_initialize_config`, which calls
`GoogleConfigProvider.load_config()` **eagerly, at construction time** —
not deferred to `initialize()` the way `NotionIntegration` defers its own
config load). Two ways to satisfy this:

**Option A — pass `client_secrets_file`/`credentials_file` directly:**

```python
from zeo_core.integrations.google.calendar import GoogleCalendarService

calendar = GoogleCalendarService(
    client_secrets_file="path/to/client_secrets.json",
    credentials_file="path/to/credentials.json",
)
```

This is the simplest path and skips the config-file lookup entirely — the
explicit constructor args win.

**Option B — a config file, matching drive/mail's own convention:**

```yaml
integrations:
  google:
    client_secrets_file: path/to/client_secrets.json
    credentials_file: path/to/credentials.json
    calendar:
      calendar_id: primary
```

Both work identically once past construction — Option A is what this
tutorial uses below since it needs no file scaffolding.

## Step 3 — initialize and do a real read

```python
from zeo_core.integrations.google.calendar import GoogleCalendarService

calendar = GoogleCalendarService(
    client_secrets_file="path/to/client_secrets.json",
    credentials_file="path/to/credentials.json",
)
init_result = calendar.initialize()
if not init_result.success:
    raise SystemExit(f"Failed to initialize: {init_result.error}")
print(f"Google Calendar integration initialized: {init_result.message}")

# list_calendars() -- a first sanity check that auth actually worked.
calendars_result = calendar.list_calendars()
if not calendars_result.success:
    raise SystemExit(f"list_calendars failed: {calendars_result.error}")

for cal in calendars_result.content or []:
    print(f"{cal.summary} ({cal.id}) -- primary={cal.primary}")
```

Every method on `GoogleCalendarService` returns an `IntegrationResult`
(`.success`, `.content`, `.error`, `.message`) — check `.success` before
touching `.content`; on failure `.content` is `None` and `.error` carries
a string (Calendar API errors are caught and surfaced this way, never
raised as exceptions from these methods).

### Listing events with a date range

```python
events_result = calendar.list_events(
    calendar_id="primary",  # optional -- defaults to the service's own default
    time_min="2026-08-20T00:00:00Z",
    time_max="2026-08-27T00:00:00Z",
)
if events_result.success:
    for event in events_result.content or []:
        print(f"{event.summary} ({event.id}): {event.start.date_time or event.start.date}")
```

`time_min`/`time_max` are RFC3339 timestamps, passed straight through to
the Calendar API's own `events().list()` filtering — there's no separate
date-parsing layer to learn. Events are returned with recurring events
already expanded into individual instances (`singleEvents=True`,
`orderBy="startTime"` internally) since that's what most callers actually
want when listing a range.

## Step 4 — a real write: create an event, update it, delete it

```python
create_result = calendar.create_event(
    summary="Team sync",
    start={"dateTime": "2026-08-21T10:00:00-07:00", "timeZone": "America/Los_Angeles"},
    end={"dateTime": "2026-08-21T10:30:00-07:00", "timeZone": "America/Los_Angeles"},
    description="Weekly sync",
    attendees=[{"email": "teammate@example.com"}],
)
if not create_result.success:
    raise SystemExit(f"create_event failed: {create_result.error}")

new_event = create_result.content
print(f"Created event: {new_event.id}")

# Update just the summary -- update_event does a get-then-merge round trip
# internally (the Calendar API's events().update() requires a full event
# body, not a partial patch), so only the fields you pass change.
update_result = calendar.update_event(event_id=new_event.id, summary="Team sync (moved)")
print(f"Updated: {update_result.success}")

delete_result = calendar.delete_event(event_id=new_event.id)
print(f"Deleted: {delete_result.success}")
```

`create_result.content` is a real `CalendarEvent` model (`.id`,
`.summary`, `.start`, `.end`, `.attendees`, `.html_link`, ...), not a raw
dict — pull `.id` off it directly for the follow-up
`update_event`/`delete_event` calls, as shown above.

For an all-day event, use `{"date": "2026-08-21"}` instead of `dateTime`
for `start`/`end` — both shapes are the real Calendar API's own
convention, passed through unchanged.

## Full surface, for reference

Everything demonstrated above plus what wasn't: `get_calendar(calendar_id)`,
`get_event(event_id, calendar_id=None)`. All follow the same
`IntegrationResult` shape demonstrated above. A free-text search across
events is available via `list_events(query="...")`. Freebusy queries
(`freebusy().query()`) are **not** built — explicitly scoped out as a
stretch goal, not required for the read+write CRUD surface this
integration targets.

## What doesn't work yet, stated plainly

`update_event`'s get-then-merge approach means an update is not atomic
against a concurrent external edit to the same event — if something else
changes the event between the internal `get` and the internal `update`,
the last write wins on the fields you didn't pass, same as any
read-modify-write without an `If-Match`/ETag guard. The Calendar API does
support `etag`-based conditional updates; this integration does not wire
that through yet.

## See also

- [`examples/calendar_usage.py`](../../examples/calendar_usage.py) — a
  runnable version of this tutorial's Steps 3–4, with a graceful skip when
  `ZEO_GOOGLE_CALENDAR_CLIENT_SECRETS` isn't set (so it's safe to run in CI
  or without credentials).
- [GET-STARTED.md](../../GET-STARTED.md)'s "Working with Google Calendar
  Integration" section — the condensed reference version.
- [Notion integration tutorial](notion-integration.md) — the other
  read+write integration this repo ships, useful as a structural
  comparison (bearer-token auth vs. this integration's OAuth).
