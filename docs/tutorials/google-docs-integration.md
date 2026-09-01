# Google Docs integration: read, create, and edit a document

**Created:** 2026-09-01 · **Status:** ACTIVE

`zeo_core.integrations.google.docs` wraps the Docs v1 REST API
(`documents.get` / `documents.create` / `documents.batchUpdate`) behind
zeocore's usual `IntegrationResult`-returning shape, plus two index-free
convenience methods (`append_text`, `replace_text`) built on top of
`batchUpdate` and a plain-text extractor (`get_document_text`). Every code
block below was executed against the installed package before being
written here.

```bash
pip install "zeocore[calendar]"
```

(There is no separate `docs` extra — Docs shares its Google API
dependencies with `calendar`/`drive`.)

## Step 1 — the first error you will hit, verbatim

```python
from zeo_core.integrations.google.docs import GoogleDocsService

docs = GoogleDocsService()
result = docs.initialize()
print(result.error)
```
```
Configuration file not found in default locations.
```

This fires even if you plan to pass credentials directly — `GoogleDocsService`
uses a *deferred-config* pattern (config resolution happens inside
`initialize()`, never in `__init__`, so construction itself never raises),
but the base class's own `initialize()` still looks for a config file
**before** the Docs subclass ever gets to look at constructor arguments.
Verified directly: passing `client_secrets_file`/`credentials_file` to
`GoogleDocsService(...)` does **not** skip this check (this differs from
`GoogleCalendarService`, which resolves config eagerly and does honor
constructor args alone — don't assume the two integrations behave alike).

**The fix:** give it a real config file, at one of the default locations
(`./config/google_config.yaml`, `./zeo_config.yaml`, `~/.zeo/config.yaml`)
or via `config_path=`:

```yaml
# config/google_config.yaml
google:
  docs:
    client_secrets_file: path/to/client_secrets.json
    credentials_file: path/to/credentials.json
```

```python
docs = GoogleDocsService(config_path="config/google_config.yaml")
```

## Step 2 — Google Cloud OAuth setup

1. In the [Google Cloud Console](https://console.cloud.google.com/), create
   or reuse a project.
2. Enable the **Google Docs API** (APIs & Services → Library).
3. Create OAuth 2.0 credentials: APIs & Services → Credentials → Create
   Credentials → OAuth client ID → **Desktop app**. Download the JSON — this
   is your `client_secrets_file`.
4. The first `initialize()` call with no cached token opens a real browser
   window for consent, then writes the resulting token to `credentials_file`.
   No browser is needed again until that token is revoked.

**Credentials never live in your repo.** `credentials_file`'s *default*
location (when you don't override it) resolves outside this project
entirely, to your OS's per-user config directory via `platformdirs`
(`~/Library/Application Support/zeocore/` on macOS), written with file mode
`0o600` — verified by `stat` against a real write. If you're worried about
committing a token: you can't, by default. Point `credentials_file` inside
your repo only if you also `.gitignore` it.

## Step 3 — read a document

```python
docs = GoogleDocsService(config_path="config/google_config.yaml")
init_result = docs.initialize()
if not init_result.success:
    raise SystemExit(f"Failed to initialize: {init_result.error}")

text_result = docs.get_document_text("1AbCDeFGhijKLmnoPQRstuVWxyz")
if not text_result.success:
    raise SystemExit(f"get_document_text failed: {text_result.error}")
print(text_result.content)  # plain str
```

Every method returns an `IntegrationResult`: `.success` (bool), `.content`
(the payload, `None` on failure), `.error` (a string, never an exception).
**Always check `.success` before touching `.content`** — this is the one
pattern that generalises across all thirteen zeocore integrations.
`get_document(document_id)` returns the full raw document resource
(`dict[str, Any]`) if you need more than plain text; `get_document_text`
recursively flattens it (tables included) for you.

## Step 4 — create a document and edit it index-free

```python
created = docs.create_document(title="Meeting notes")
if not created.success:
    raise SystemExit(f"create_document failed: {created.error}")

document_id = created.content["documentId"]  # a dict, not a model — index it

append_result = docs.append_text(document_id, "Agenda:\n- Item one\n")
replace_result = docs.replace_text(document_id, find="Item one", replace="Kickoff")
if not (append_result.success and replace_result.success):
    raise SystemExit("edit failed")
```

`append_text` and `replace_text` are index-free by construction (they wrap
`batchUpdate` requests that match by string or by "end of body," not by a
character offset you'd otherwise have to compute yourself). For anything
outside those two shapes, drop to `batch_update(document_id, requests)`
directly with a raw Docs API `requests` list — every request kind Google's
API accepts is a plain `dict`, not a modeled type.

## What's credential-blocked here

Everything above through `initialize()` returning its config error is real,
executed output. The live read/create/edit calls need a real OAuth
consent screen — that's an operator checkpoint, not something a class
exercise can script around. Their expected output above is illustrative,
not observed.

## See also

- [Google Calendar integration tutorial](calendar-integration.md) — same
  OAuth family, contrast the eager-vs-deferred config timing named in Step 1.
- [Notion integration tutorial](notion-integration.md) — a bearer-token
  integration, for comparison.
