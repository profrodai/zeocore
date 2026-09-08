# Supabase account setup

**Reviewed:** 2026-09-09. Integration: `supabase`. Install with
`uv pip install -e ".[supabase]"`. Read [environment setup](environments.md) and the
[full Supabase tutorial](../tutorials/supabase-integration.md).

## Obtain the URL and application key

Sign into [Supabase Dashboard](https://supabase.com/dashboard), create/select the
project in the correct organization, and wait for provisioning. Open **Connect**
for its project URL and publishable key. **Settings → API Keys** lets you create
or select a particular key. Use the new `sb_publishable_...` key for ordinary
user-facing access. The project database password and a Supabase management token
are not Data API credentials.
[Official API key guide](https://supabase.com/docs/guides/getting-started/api-keys).

The required variables are `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`.
`SUPABASE_KEY` remains a compatibility input. A server-only `SUPABASE_SECRET_KEY`
requires `allow_privileged_key: true` in ZeoCore config; it bypasses RLS and is not
appropriate for a normal client-side test. Prefer a publishable key plus explicit
user authentication/RLS. Do not put a secret key in a browser or distributed app.

## Test account track

Choose a real isolated backend:

1. **Local stack:** install the provider's CLI and its documented container runtime,
   create a dedicated directory, then run `supabase init` and `supabase start`.
   Obtain the local URL/key from the startup output or `supabase status`; do not
   copy a hosted production URL into local tests. Follow the
   [official local workflow](https://supabase.com/docs/guides/local-development/cli-workflows).
2. **Separate hosted project:** create a project named `zeocore-test`, provision
   synthetic schema/data and copy that project's URL/key. This remains a real
   hosted service with billing/resource limits, not a free universal sandbox.

Set `ZEO_TEST_SUPABASE_URL` to the selected URL and use the secure key prompt below
or `ZEO_TEST_SUPABASE_PUBLISHABLE_KEY`. For a loopback HTTP local stack, put this in
`test/config/integrations.yaml`:

```yaml
supabase:
  allow_local_http: true
  schema: public
  max_rows: 100
```

For hosted HTTPS omit `allow_local_http`. The exception is for an explicitly
selected local stack, not arbitrary insecure URLs.

In the test project's SQL editor/local migration create a small table
`zeocore_probe` with an `id` column and one synthetic row. Configure table grants
and an RLS SELECT policy for the intended test role, or sign in as a test user whose
policy permits that row. Do not disable RLS on production to make the probe work.

For a fresh disposable test project, this SQL creates the read-only probe. Run
it in that test project's SQL editor or a local migration. It intentionally
exposes only this synthetic row to the anonymous test role; use your own
reviewed policies for authenticated and production data. On a second run, an
existing table/policy error means inspect the existing fixture before proceeding.

```sql
create table public.zeocore_probe (id text primary key);
insert into public.zeocore_probe values ('zeocore-test-probe');
alter table public.zeocore_probe enable row level security;
grant select on public.zeocore_probe to anon;
create policy zeocore_probe_read on public.zeocore_probe
  for select to anon using (id = 'zeocore-test-probe');
```

Save `check_supabase.py`:

```python
from zeo_core.integrations.database.supabase import SupabaseIntegration

service = SupabaseIntegration()
configured = service.initialize()
if not configured.success:
    raise SystemExit("Supabase initialization failed; check URL, key and local HTTP policy")
result = service.select("zeocore_probe", columns=("id",), limit=1)
if not result.success:
    raise SystemExit("SELECT failed; check grants, RLS and schema")
if result.content is None or result.content.rows != [{"id": "zeocore-test-probe"}]:
    raise SystemExit("Expected probe row missing; check RLS, project and fixture")
print("Supabase bounded SELECT returned the expected fixture row")
```

```bash
ZEO_TEST_SUPABASE_URL="http://127.0.0.1:54321" python -m zeo_core.integrations.environments   --mode test --root "$ZEO_ENV_ROOT" --integration supabase   --secret SUPABASE_PUBLISHABLE_KEY -- python /absolute/path/check_supabase.py
```

For hosted tests substitute that project's HTTPS URL. Successful empty results may
mean an RLS policy filtered the row; the check above fails in that case.
For production, adapt the expected row and table to an approved harmless resource.
Never add this anonymous test policy to a production data table.

## Production account track

Provision or select the real project and apply reviewed migrations, grants and RLS
policies. Configure `ZEO_PRODUCTION_SUPABASE_URL` and the production publishable key,
with separate user authentication where needed. Use the production HTTPS URL and
leave `allow_local_http` false. Run an equivalent bounded read of an approved
production resource with `--mode production`, using its actual table/row IDs.
Do not seed synthetic users into production or run a local reset against it.

Use separate projects, not just separate keys within one project. When both live
namespaces supply the same nonempty `SUPABASE_URL`, the launcher refuses either
mode before starting the application, even with different keys. This is an exact
URL comparison; aliases/custom domains and an absent opposite-mode URL cannot
establish project separation. Verify the project identity in the dashboard too.

## Bounded E2E and cleanup

Against the test backend, insert one uniquely identified fixture row through the
integration, SELECT it, update it, SELECT again and delete that exact row. Verify
the row is gone and that an unrelated row was untouched. Test Auth with dedicated
users, Storage with a disposable bucket/object prefix, Functions with a test-only
function, and Realtime with a subscription tied to the fixture row. Clean up those
objects individually; a database-wide reset is only for your disposable local stack.
The [Supabase example](../../examples/supabase_usage.py) and tests use controlled
backends; retain a separate receipt for each live surface you actually qualified.

## Troubleshooting and rotation

401: verify URL and key belong to the same project and the key type is supported.
403/empty rows: inspect SQL grants, RLS and signed-in identity; a publishable key
is not a user session. Connection refused: check local stack status and selected
port. Missing table: apply the migration to the selected backend, not just generated
types. Realtime and Functions require their own deployed/configured resources.

Create/rotate the selected project's key in Settings → API Keys, update its namespace,
restart and rerun the probe. Revoke the old key after validation. Rotating a newer
key does not automatically revoke legacy keys; audit them separately in that page.
