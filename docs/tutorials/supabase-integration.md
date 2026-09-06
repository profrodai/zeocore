# Supabase integration

ZeoCore's Supabase integration covers the application SDK surface: Database,
Auth, Storage, Edge Functions, and Realtime. It does not administer a Supabase
project and it does not expose Vault plaintext.

## 1. Install and configure

```bash
uv add "zeocore[supabase]"
cp .env.example .env
```

Add the values shown under **Connect → App Frameworks** in the Supabase
dashboard:

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

Use a publishable key for user-facing applications. Row Level Security (RLS)
is the authority. A broader project grant never widens a ZeoCore operation by
itself.

`SUPABASE_SECRET_KEY` is server-only. ZeoCore ignores it unless non-secret
configuration explicitly sets `allow_privileged_key: true`. That is suitable
only for an isolated broker or trusted maintenance process—not a browser,
model tool, preview deployment, or ordinary web runtime.

## 2. Initialize once

```python
from zeo_core.config import load_dotenv_file
from zeo_core.integrations.database.supabase import SupabaseIntegration

load_dotenv_file()
supabase = SupabaseIntegration()
result = supabase.initialize()
if not result.success:
    raise RuntimeError(result.error)
```

Initialization creates no table, bucket, user, or network request. It constructs
the official SDK client with bounded timeouts and in-memory session persistence
disabled by default.

## 3. Database

```python
from zeo_core.integrations.database.supabase import (
    SupabaseFilter,
    SupabaseFilterOperator,
    SupabaseOrder,
)

ready = supabase.select(
    "tasks",
    columns=("id", "title", "created_at"),
    filters=(
        SupabaseFilter(
            field="status",
            operator=SupabaseFilterOperator.EQ,
            value="ready",
        ),
    ),
    orders=(SupabaseOrder(field="created_at", descending=True),),
    limit=25,
    count="exact",
)

created = supabase.insert("tasks", {"title": "Make tea", "status": "ready"})
changed = supabase.update(
    "tasks",
    {"status": "done"},
    filters=(SupabaseFilter(field="id", value=created.content.rows[0]["id"]),),
)
```

`update()` and `delete()` reject an empty filter list. Table, column, function,
schema, and filter-field names are identifiers—not fragments of SQL. For
transactional domain behavior, publish a reviewed PostgreSQL function and call
it by name with `rpc()`. ZeoCore never accepts raw SQL.

## 4. Auth

```python
signed_in = supabase.sign_in_with_password(
    email="member@example.com",
    password=password_from_a_secret_input,
)
print(signed_in.content.user.email)
```

Passwords and Supabase access/refresh tokens cross the SDK boundary because
the provider requires them, but they are never returned in
`SupabaseSessionStatus` or `IntegrationResult`. The public result contains only
`authenticated`, safe user identity/metadata, and `expires_at`.

Available flows include password sign-up/sign-in, email OTP, OAuth initiation,
verified user lookup, explicit refresh, password-reset email, and sign-out.
Persist rotating sessions in your application-owned custody layer, not in a
model prompt or log.

## 5. Storage

```python
supabase.upload_bytes(
    "artifacts",
    "reports/run-42.json",
    report_bytes,
    content_type="application/json",
)
downloaded = supabase.download_bytes("artifacts", "reports/run-42.json")
```

Object paths are relative POSIX paths and reject traversal. Uploads and
downloads are limited by `max_object_bytes`. Bucket listing/creation/deletion,
object listing, copy, move, and bounded removal are available. Signed URLs are
not: they are bearer credentials and need a product-specific disclosure and
expiry contract.

## 6. Edge Functions

```python
invoked = supabase.invoke_function(
    "render-report",
    body={"report_id": "42"},
)
```

The caller supplies a function name, never a URL. `Authorization`, `apikey`,
and `Cookie` headers are rejected because credential injection belongs to the
SDK. Responses are bounded and normalized without raw response headers.

## 7. Realtime

Realtime is async-only in Supabase's Python SDK, so ZeoCore does not hide an
event loop:

```python
from zeo_core.integrations.database.supabase import SupabaseRealtimeEvent

subscription = await supabase.realtime.subscribe_table(
    "tasks",
    on_change,
    event=SupabaseRealtimeEvent.UPDATE,
)
try:
    await wait_for_your_application_signal()
finally:
    await supabase.realtime.unsubscribe(subscription.id)
    await supabase.realtime.close()
```

Reconnect and retry policy stays with the host application so a connection
failure cannot silently multiply work.

## 8. Vault and privileged roles

There is intentionally no `vault()` or `decrypted_secrets()` method. Supabase
Vault decrypts secrets when its decrypted view is queried; an application role
that can select that view can obtain plaintext. A safe hosted custody design
uses separate web and broker identities, restrictive function privileges,
fixed `search_path`, authenticated metadata, encrypted envelopes, audit
evidence, and preview isolation.

ZeoCore supplies the integration boundary. Your migrations and deployment must
prove RLS, Storage policies, function grants, role separation, backup behavior,
and cross-tenant refusal against the real project.
