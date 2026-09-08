# Google Workspace account setup

<!-- Teaches CLAUDE.md Rev 17; verified against provider documentation 2026-09-08. -->

Install the shared Google dependencies in your activated source checkout with
`uv pip install -e ".[google]"`.

Covers `google.mail`, `google.drive`, `google.calendar`, `google.docs`,
`google.sheets`, and `google.slides`. First prepare the directories in
[test and production environments](environments.md). Google uses an OAuth
client JSON file and a user authorization token; a plain Google API key does
not authorize these user-data integrations. The local adapter opens a browser
on first authorization and saves refresh credentials. For unattended use,
authorize the chosen account on the deployment host before scheduling jobs,
or use the separately provisioned [hosted profile](zeoconnect.md).

## Test account and OAuth client

1. Create a dedicated Google user for test data. In
   [Google Cloud Console](https://console.cloud.google.com/), create and select
   a project named for ZeoCore testing. Record its project ID.
2. Open **APIs & Services → Library** and enable the API for each service you
   will use: Gmail API, Google Drive API, Google Calendar API, Google Docs API,
   Google Sheets API, or Google Slides API.
3. Open **Google Auth Platform**. Configure **Branding** with the app name,
   support email and contact details. Under **Audience**, choose Internal only
   when your Workspace organization supports it; otherwise choose External and
   keep the test app in Testing. Add the dedicated user under **Test users**.
4. Under **Data Access**, add the scopes for the selected service below. Under
   **Clients**, create an OAuth client with application type **Desktop app**.
   Download its JSON. Keep the whole file, not just the client ID.
   [Google's consent setup](https://developers.google.com/workspace/guides/configure-oauth-consent)
   and [credential creation](https://developers.google.com/workspace/guides/create-credentials)
   show the current screens.
5. After preparing test mode, place the downloaded file at the exact location
   below. Replace the source filename with your download; do not commit it.

```bash
mkdir -p "$ZEO_ENV_ROOT/test/credentials/google"
chmod 700 "$ZEO_ENV_ROOT/test/credentials/google"
cp "$HOME/Downloads/client_secret_TEST.json"   "$ZEO_ENV_ROOT/test/credentials/google/google_client_secret.json"
chmod 600 "$ZEO_ENV_ROOT/test/credentials/google/google_client_secret.json"
```

The client JSON identifies the app. The later `mail_credentials.json`,
`drive_credentials.json`, etc. authorize the user and are secrets too. This
guide gives each service its own token file to avoid accidentally reusing a
token with a different scope set. Managed mode does not import old global
Google credentials automatically.

## First live read

Save this complete script as `check_google.py` at an absolute path. It requests
read-only scopes for its initial checks. The resource argument is mandatory
for Docs, Sheets, Slides and Calendar. For Drive it is a test folder ID.
For Gmail it is a search query, such as `subject:ZEOCORE-TEST`.

```python
import sys
from zeo_core.integrations.environment import managed_state_dir
from zeo_core.integrations.google.mail.service import GoogleMailService
from zeo_core.integrations.google.drive.service import GoogleDriveService
from zeo_core.integrations.google.calendar.service import GoogleCalendarService
from zeo_core.integrations.google.docs.service import GoogleDocsService
from zeo_core.integrations.google.sheets.service import GoogleSheetsService
from zeo_core.integrations.google.slides.service import GoogleSlidesService

name, resource = sys.argv[1:3]
state = managed_state_dir()
assert state is not None, "Use the environment launcher"
credentials = state / "credentials" / "google"
common = dict(
    client_secrets_file=str(credentials / "google_client_secret.json"),
    credentials_file=str(credentials / f"{name}_credentials.json"),
)
scopes = {
    "mail": "gmail.readonly", "drive": "drive.metadata.readonly",
    "calendar": "calendar.readonly", "docs": "documents.readonly",
    "sheets": "spreadsheets.readonly", "slides": "presentations.readonly",
}
classes = {
    "mail": GoogleMailService, "drive": GoogleDriveService,
    "calendar": GoogleCalendarService, "docs": GoogleDocsService,
    "sheets": GoogleSheetsService, "slides": GoogleSlidesService,
}
argument = "oauth_scope" if name == "mail" else "scopes"
service = classes[name](**common, **{
    argument: ["https://www.googleapis.com/auth/" + scopes[name]]
})
initialized = service.initialize()
assert initialized.success, initialized.message
read = {
    "mail": lambda: service.list_emails(query=resource),
    "drive": lambda: service.list_files(remote_path=resource),
    "calendar": lambda: service.list_events(calendar_id=resource, max_results=1),
    "docs": lambda: service.get_document(resource),
    "sheets": lambda: service.get_spreadsheet(resource),
    "slides": lambda: service.get_presentation(resource),
}
result = read[name]()
assert result.success, result.message
assert result.content, "Expected seeded test data; check account, resource and grants"
print("Google read succeeded; verify the selected identity in the browser")
```

Run one service at a time. Replace the integration, service name and resource
for the others using the table below. The browser must show the dedicated test
user; cancel and switch accounts if it shows a production user.

```bash
python -m zeo_core.integrations.environments --mode test   --root "$ZEO_ENV_ROOT" --integration google.docs --   python /absolute/path/check_google.py docs TEST_DOCUMENT_ID
```

## Service-specific resources and E2E checks

Scope suffixes below follow `https://www.googleapis.com/auth/`. These are
separate service authorizations; enabling one API does not enable the others.
The write tests require changing the script/application's requested scopes
and authorizing again with a fresh token file inside the same test directory.
Do not count a read-only check as proof of a write workflow.

### Gmail

Use `google.mail`, script name `mail`, and `subject:ZEOCORE-TEST`. Send a uniquely
named message from another designated test mailbox to the test user first.
The scope is `gmail.readonly`. List and download that message, compare its
subject/body/attachment locally, then remove the test message in Gmail. This
adapter reads mail; marketing sends belong to [Kit](kit.md) or
[HubSpot](hubspot.md), not an unimplemented Gmail send method.
Production uses the real mailbox's separate OAuth authorization and its own
search query. Keep downloaded mail under `production/work`.

### Drive

Use `google.drive`, script name `drive`, and a folder ID copied from the
folder's browser URL. Seed a file there. The first listing uses
`drive.metadata.readonly`; file download needs a content-reading scope such as
`drive.readonly`. For a selected-file application, explicitly use
`scope_profile="selected-file"` (`drive.file`) and select/grant files through
the application's Google flow. That scope does not reveal every pre-existing
file merely because the user can see it in Drive. A dedicated test account
can instead authorize the local adapter's broader default scopes for its
upload/download test. Upload a uniquely named file, download and compare its
bytes, then trash only the returned test file in Drive. Production must point
to the separately selected production folder; do not reuse test IDs.

### Calendar

Use `google.calendar`, script name `calendar`. In Google Calendar, create a
secondary test calendar, seed an event, and copy its **Settings → Integrate
calendar → Calendar ID**. The read check uses `calendar.readonly`. For event
creation/update/deletion request `calendar.events` and pass that calendar ID
to every operation; do not rely on the default `primary`. Create an event with
no attendees, read and update it, then delete it. Production uses its own
calendar ID and account; adding attendees can send real invitations.

### Docs

Use `google.docs`, script name `docs`, and the ID between `/d/` and `/edit` in
a test document URL. Write a distinctive paragraph first. Read with
`documents.readonly`. For E2E creation/editing use `documents`, create a new
document, insert text through the documented batch update API, read it back
and inspect it in Docs. Trash it through Drive's UI when finished. Production
uses a document owned by or shared with the production user.

### Sheets

Use `google.sheets`, script name `sheets`, and the spreadsheet URL's `/d/` ID.
Seed cell A1 and read with `spreadsheets.readonly`. For E2E writes use
`spreadsheets`, create a disposable spreadsheet, write a known small cell
range, read and compare the values, then trash it in Drive. Keep production
spreadsheet IDs and ranges in production-only application configuration.

### Slides

Use `google.slides`, script name `slides`, and the presentation URL's `/d/` ID.
Seed a slide and read with `presentations.readonly`. For E2E writes use
`presentations`, create a disposable presentation, add a slide/text using the
batch update API, read it back and inspect its render in Slides. Trash it in
Drive. Production uses its own presentation and template IDs.

## Production account and deployment

Create a separate Cloud project and Desktop OAuth client for production,
enable only its required APIs, and repeat consent configuration. Complete
Google's applicable verification and Workspace administrator approval before
using it with the intended audience. A test-user authorization is not evidence
that an external production rollout is approved. Testing refresh tokens may
expire; production credentials still require revocation/error handling.
See [Google's OAuth lifecycle](https://developers.google.com/identity/protocols/oauth2).

Prepare production mode, then copy the **production** client download to
`$ZEO_ENV_ROOT/production/credentials/google/google_client_secret.json` using
the same directory and permission commands with `production` substituted.
Never copy the test refresh-token files. Run a read first and sign in as the
real production user:

```bash
python -m zeo_core.integrations.environments --mode production   --root "$ZEO_ENV_ROOT" --integration google.docs --   python /absolute/path/check_google.py docs PRODUCTION_DOCUMENT_ID
```

Repeat with each required integration/service/resource. Only after those
checks should the production agent's approved workflow use write scopes.
For headless deployment, protect the per-service token files with the host's
secret storage/access controls; browser authorization and token refresh must
actually work on that host before scheduling it.

## Repair and rotation

`access_denied`: verify the browser account is an allowed test user and the
Workspace admin permits the app. API-disabled errors: enable the named API in
the project that issued this client. A 403 can also mean insufficient scopes
or resource sharing; do not solve it by granting every scope. A 404 may hide
an inaccessible resource; inspect its ID and sharing with the selected user.
On expired/revoked tokens, revoke that app's access in the Google account,
remove only the affected mode/service's cached token and authorize again.
Rotate the OAuth client through Cloud Console if its JSON is exposed. Never
print token JSON in troubleshooting logs or transfer a production token into
the test directory.
