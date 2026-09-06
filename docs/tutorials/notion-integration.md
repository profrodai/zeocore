# Notion API 2026-03-11

**Created:** 2026-08-20 · **Last-updated:** 2026-09-05 · **Status:** ACTIVE

ZeoCore uses `notion-client>=3.1.0`, explicitly opts into Notion API
`2026-03-11`, and offers two layers:

- `NotionIntegration` returns ZeoCore `IntegrationResult` objects and retains
  the common page/database/block convenience calls.
- `NotionClient.execute(NotionOperation, **payload)` reaches the complete
  current data API. `paged()` preserves one cursor page and `iterate()` walks
  all pages.

Install and prove the credential-free path first:

```bash
uv pip install "zeocore[notion]"
uv run python examples/notion_demo.py --simulated
```

## Create and store the credential

For a private/internal connection:

1. Open the [Notion integrations portal](https://www.notion.so/my-integrations).
2. Create an internal integration and select only the content, comment, user,
   and file capabilities your application needs.
3. Copy its integration secret once.
4. Share each required root page/database with that integration from Notion's
   `…` → `Connections` menu. Authentication alone grants access to nothing.
5. In your application directory, copy ZeoCore's `.env.example` to `.env` and
   replace only the placeholder:

   ```dotenv
   NOTION_TOKEN=ntn_your_real_value
   ```

   `.env` is gitignored. Do not put the token in YAML, source code, shell
   history, an exception, or a notebook cell.

ZeoCore does not implicitly read files on import. Either load `.env` once in
your entrypoint or let `uv` inject it:

```bash
uv run --env-file .env python examples/notion_demo.py --live-read
```

The demo never writes. Live mutation requires application code that names the
target IDs and invokes a write operation deliberately.

## Common typed calls

```python
from zeo_core.integrations.notion import NotionIntegration

notion = NotionIntegration()
initialized = notion.initialize()  # NOTION_TOKEN is sufficient; no YAML needed
if not initialized.success:
    raise RuntimeError(initialized.error)

page = notion.get_page("page-id")
blocks = notion.list_page_blocks("page-id")
```

Notion databases are containers and data sources are queryable tables. The
legacy `query_database()` convenience call now proceeds only when the database
has exactly one data source; zero or multiple sources are rejected. For a
multi-source database, choose the ID explicitly:

```python
from zeo_core.integrations.notion import NotionClient

client = notion.client
assert isinstance(client, NotionClient)
sources = client.list_data_sources("database-id")
rows, cursor = client.query_data_source(sources[0].id)
```

The old `archived=` Python argument remains as a compatibility alias, but the
wire request always uses `in_trash`, as required by API 2026-03-11. Block
insertion uses `position={"type": "start" | "end" | "after_block", ...}`;
the removed `after` parameter is never sent.

## Complete operation matrix

Every row is a `NotionOperation` value accepted by `execute`; the same list is
available mechanically as `client.supported_operations`.

| Resource | Operations |
|---|---|
| Pages | retrieve, retrieve property, create, update, move, retrieve markdown, update markdown |
| Blocks | retrieve, update, delete, list/append children, query meeting notes |
| Databases | retrieve, create, update |
| Data sources | retrieve, query, create, update, list templates |
| Users | list, retrieve, current bot |
| Search | cursor-paginated search; filters use `page` or `data_source` |
| Comments | create, list, retrieve, update, delete |
| File uploads | create, send part, complete, retrieve, list |
| Views | create, retrieve, update, delete, list |
| View queries | create cached query, page results, delete query |
| Custom emoji | list |

Example—walk every comment without dropping cursor state:

```python
from zeo_core.integrations.notion import NotionOperation

for comment in client.iterate(
    NotionOperation.COMMENT_LIST,
    block_id="page-or-block-id",
    page_size=100,
):
    print(comment["id"])
```

The SDK performs bounded retries for `429` and server failures. After
exhaustion, ZeoCore raises `NotionAPIError` with stable code/status/retry
metadata and a sanitized message; it never copies the provider response body.

## Governed `notion.page.upsert`

The 44-operation client is a provider API surface. It does not mean an actor is
authorized to call any of those operations. ZeoCore separately admits one
narrow, reconcilable business effect: `notion.page.upsert` revision
`notion.page-upsert@1`.

Inspect its closed request contract without a credential or network call:

```bash
uv run python examples/notion_governed_upsert.py
```

The example hashes the source meeting artifact, binds that digest and the
destination data-source ID into a deterministic idempotency marker, requires a
source citation for every interpreted statement, and renders canonical
Markdown. Extra fields, malformed Notion IDs, missing citations, and a marker
for a different artifact or destination fail validation before dispatch.

Behind the scenes, an authorized production invocation follows this path:

1. `notion_page_upsert_revision()` fixes the operation ID, effect class,
   argument schema, Notion origin/path, idempotency mode, and reconciler.
2. `EffectOrchestrator` verifies the exact authorization and durable
   idempotency claim, then records dispatch start before a provider call.
3. `KeychainEffectDispatcher` (local) or a conforming hosted custody dispatcher
   resolves the opaque `SecretRef` only inside the provider boundary.
4. `NotionPageUpsertDispatcher` searches the destination's `ZEO Idempotency`
   property. It creates when absent, returns the matching page when identical,
   and replaces content only when the existing title still agrees.
5. It reads the page back and confirms only when title, marker, and canonical
   Markdown match the request.
6. If the provider call may have happened but confirmation was lost, the
   execution becomes `AMBIGUOUS`. `NotionPageUpsertReconciler` performs only the
   marker lookup and read-back; it never creates or updates a page.

A destination data source used by this operation needs a title property named
`Name` and a rich-text property named `ZEO Idempotency`. The integration must be
connected to that data source. Reusing an idempotency key with different
canonical arguments is refused by orchestration; finding multiple pages with
the same marker fails safe rather than choosing one.

The example intentionally stops at request construction. A live effect also
needs a stored connector revision, connection, opaque credential reference,
exact `EffectAuthorization`, durable `BrokerExecutionStore`, dispatcher, and
reconciler. This ceremony prevents a tutorial from teaching that possession of
`NOTION_TOKEN` is mutation authority.

## Public OAuth

`NotionOAuthBroker` covers exchange, refresh, introspection, and revocation
separately from the data-operation registry. Set `NOTION_OAUTH_CLIENT_ID` and
`NOTION_OAUTH_CLIENT_SECRET` in `.env`, inject a ZeoCore `SecretStore`, and
call `exchange(code=...)`. The access and optional refresh token are placed
directly into custody; the returned `NotionOAuthGrant` carries only redacted
`SecretRef` values and workspace metadata. Introspection and revocation read
the bearer value from `NOTION_TOKEN` so no public method accepts or returns it.
For rotation, inject the prior refresh credential as
`NOTION_OAUTH_REFRESH_TOKEN` and call `refresh_environment_grant()`; its
replacement credentials go straight into the same custody path. A deployment
secret manager should inject that value—never copy a SecretRef's material back
through application code or a YAML file.

OAuth is deliberately not an `execute()` operation: the token endpoint creates
new credential material, while every operation in that registry returns an
ordinary dictionary. Mixing the two would turn a correct data API into a
credential-disclosure channel.

## Current-version sources

- [Notion versioning](https://developers.notion.com/reference/versioning)
- [2026-03-11 upgrade guide](https://developers.notion.com/guides/get-started/upgrade-guide-2026-03-11)
- [Pagination](https://developers.notion.com/reference/intro#pagination)
- [Request limits and Retry-After](https://developers.notion.com/reference/request-limits)
