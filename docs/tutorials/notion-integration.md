# Notion integration, end to end: auth setup through a real read + write example

**Created:** 2026-08-20 · **Status:** ACTIVE

`zeo_core.integrations.notion` gives you a full read + write surface
against Notion's API through zeocore's usual typed, `IntegrationResult`-
returning shape. This tutorial walks the whole path — creating an
integration token, the one real gotcha in getting `initialize()` to
succeed, then a real search, a real database query, and a real page
creation — with every code block verified against the live source before
being written here.

Requires the `notion` extra:

```bash
pip install "zeocore[notion]"
```

## Step 1 — create an integration token

Notion's auth model is a single bearer **integration token**, not OAuth —
structurally the same shape as a GitHub personal access token, and
simpler to set up than the Google integrations' OAuth flow.

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
   and create a new internal integration. Give it a name (e.g.
   "zeocore-dev") and the capabilities you need (read content, insert
   content, update content — check all three if you're following this
   tutorial's write example too).
2. Copy the "Internal Integration Secret" it generates — this is your
   token.
3. **Share at least one page with the integration.** This step is easy to
   miss and is the single most common reason a correctly-configured
   integration sees nothing: an integration token authenticates fine but
   has access to *zero* pages/databases until you explicitly share them
   with it. Open a page in Notion, click "..." → "Connections" → find
   your integration by name → connect it. Anything nested under that
   page (including databases) becomes visible too.

Set the token as an environment variable:

```bash
export NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxx
```

## Step 2 — the one real gotcha: `initialize()` needs a config file to exist

This is worth stating plainly because it's easy to assume otherwise:
**`NOTION_TOKEN` alone, with zero config file anywhere on disk, is not
enough.** Verified directly against the source
(`zeo_core/integrations/core/base.py`'s `BaseIntegrationService.initialize()`):
loading configuration through zeocore's default-locations lookup
(`./zeo_config.yaml`, `./config/zeo_config.yaml`, `~/.zeo/config.yaml`)
*raises* if no file is found at any of them — there's no silent
fallback-to-defaults for this integration the way there is for, say, the
jupytext integration. `NotionConfigProvider` does correctly backfill the
token from `NOTION_TOKEN` once a config file (even an empty one) is
loaded — the gotcha is specifically the file's *existence*, not the
token's presence in it.

The fix is a one-line file. Create `zeo_config.yaml` in your project root:

```yaml
integrations:
  notion: {}
```

That's the entire file — an empty `notion` block is sufficient; the
token itself comes from `NOTION_TOKEN`.

## Step 3 — initialize and do a real read

```python
from zeo_core.integrations.notion import NotionIntegration

notion = NotionIntegration()  # picks up ./zeo_config.yaml by default
init_result = notion.initialize()
if not init_result.success:
    raise SystemExit(f"Failed to initialize: {init_result.error}")
print(f"Notion integration initialized: {init_result.message}")

# search() with no filter lists everything shared with this integration --
# useful as a first sanity check that sharing (Step 1.3) actually worked.
search_result = notion.search(query="")
if not search_result.success:
    raise SystemExit(f"search failed: {search_result.error}")

for obj in search_result.content or []:
    print(f"{obj['object']}: {obj.get('id')}")
```

Every method on `NotionIntegration` returns an `IntegrationResult`
(`.success`, `.content`, `.error`, `.message`) — check `.success` before
touching `.content`; on failure `.content` is `None` and `.error` carries
a string (Notion API errors, including invalid-token and
object-not-found, are caught and surfaced this way, never raised as
exceptions from these methods).

If `search_result.content` comes back empty even with a valid token,
that's almost always Step 1.3 (nothing shared with the integration yet),
not a code problem — go share a page.

### Querying a database

Notion's API changed its underlying model on 2025-09-03: a "database" is
now a container for one or more "data sources," and querying happens
against a data source ID, not the database ID directly. `zeo_core`'s
Notion integration hides this from you for the common case — you keep
passing a `database_id` and it resolves the (usually singular) data
source internally:

```python
query_result = notion.query_database(
    "your-database-id",
    filter={"property": "Status", "select": {"equals": "Done"}},
)
if query_result.success:
    for page in query_result.content or []:
        print(page.id, page.url)
```

(If you ever have a database with genuinely multiple data sources, the
lower-level `list_data_sources()`/`query_data_source()` methods on
`zeo_core.integrations.notion.NotionClient` — not on `NotionIntegration`
— expose that explicitly. Most databases have exactly one data source, so
you won't need them.)

## Step 4 — a real write: create a page, then append a block to it

```python
create_result = notion.create_page(
    parent={"type": "page_id", "page_id": "the-page-id-you-shared-in-step-1"},
    properties={"title": [{"text": {"content": "Created by zeocore"}}]},
)
if not create_result.success:
    raise SystemExit(f"create_page failed: {create_result.error}")

new_page = create_result.content
print(f"Created page: {new_page.id} ({new_page.url})")

append_result = notion.append_blocks(
    new_page.id,
    children=[
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": "Hello from zeocore."}}
                ]
            },
        }
    ],
)
print(f"append_blocks succeeded: {append_result.success}")
```

`create_result.content` is a real `NotionPage` model (`.id`, `.url`,
`.properties`, `.created_time`, ...), not a raw dict — pull `.id` off it
directly for the follow-up `append_blocks()` call, as shown above.

For creating a row inside a database instead of a bare page, the shape is
almost identical — `create_database_entry(database_id, properties=...)`
handles the same data-source resolution `query_database()` does, so you
still just pass a `database_id`.

## Full write surface, for reference

Everything demonstrated above plus what wasn't: `get_page(page_id)`,
`list_page_blocks(page_id)`, `get_database(database_id)`,
`create_database_entry(database_id, properties, children=None)`,
`update_page(page_id, properties=None, archived=None)`,
`update_block` (client-level only, via `NotionClient`, not
`NotionIntegration`). All follow the same `IntegrationResult` shape
demonstrated above.

## What doesn't work yet, stated plainly

The `auth_provider=` constructor argument on `NotionIntegration` is
accepted but currently discarded internally — the only auth path that
actually works today is the config-file + `NOTION_TOKEN` path this
tutorial walks. If you were expecting to inject a custom
`NotionAuthProvider` and have `NotionIntegration` use it, that wiring
isn't connected yet; `NotionAuthProvider` is real and independently
testable but not reachable through `NotionIntegration`'s own
initialization path.

## See also

- [`examples/notion_usage.py`](../../examples/notion_usage.py) — a
  runnable version of this tutorial's Steps 2–4, with a graceful skip
  when `NOTION_TOKEN` isn't set (so it's safe to run in CI or without
  credentials).
- [GET-STARTED.md](../../GET-STARTED.md)'s "Working with Notion
  Integration" section — the condensed reference version.
- [MCP server tutorial](mcp-server-with-claude-code.md) — for wiring a
  tool that uses this integration (via `ctx.services`) up to an
  MCP-native agent.
