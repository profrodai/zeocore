# Bluesky integration: posting, and the byte-offset hazard

**Created:** 2026-09-01 · **Status:** ACTIVE

`zeo_core.integrations.social.bluesky` posts to Bluesky with typed,
`IntegrationResult`-returning calls. Every block below was executed
against the installed package (`zeocore==0.6.0`) before being written
here. The one thing this tutorial exists to stop you from getting wrong
silently: **link/mention positions are UTF-8 byte offsets, not character
offsets.**

Requires the `bluesky` extra:

```bash
uv pip install "zeocore[bluesky]>=0.6.0"
```

## Step 1 — the first error you will hit, and what it means

```python
from zeo_core.integrations.social.bluesky.service import BlueskyIntegration

bsky = BlueskyIntegration()
result = bsky.initialize()
print(result.success, result.error)
```

Executed output on a machine with no Bluesky credentials configured
(stdout; you'll also see logger warnings on stderr about the credentials
path — those are noise, not a crash):

```
False Failed to authenticate Bluesky: No Bluesky identifier/app_password provided
```

This is expected on first run, not a bug. Credentials load from a JSON
file **outside the repo** — resolved via `platformdirs`
(`~/Library/Application Support/zeocore/bluesky/bluesky_credentials.json`
on macOS), written with mode `0600` — so you cannot accidentally commit a
token. **Use a Bluesky app password, never your account password**:
Settings → App Passwords on bsky.app.

To authenticate and persist credentials for later runs:

```python
from zeo_core.integrations.social.bluesky.auth import BlueskyAuthProvider
from zeo_core.integrations.social.bluesky.credential_paths import default_credentials_path

auth = BlueskyAuthProvider(credentials_file=default_credentials_path())
auth_result = auth.authenticate(identifier="you.bsky.social", app_password="xxxx-xxxx-xxxx-xxxx")
if auth_result.success:
    auth.save_credentials()
```

`authenticate()` makes a real network call, so it is not run in this
tutorial — the operator runs this step live, once, interactively.

## Step 2 — always check `.success` before touching `.content`

Every call — `initialize()`, `post()`, `authenticate()` — returns an
`IntegrationResult`: `.success` (bool), `.content` (payload, `None` on
failure), `.error` (`str | None`). Never read `.content` unguarded:

```python
result = bsky.post("hello from zeocore")
if not result.success:
    raise SystemExit(f"post failed: {result.error}")
print(result.content)
```

No post from this tutorial has been sent to Bluesky — posting is left to
the operator's own session, live.

## Step 3 — the byte-offset hazard (read this even if you skim everything else)

`post()` takes `links`/`mentions` as spans of **text you want linked**,
not offsets you compute yourself:

```python
from zeo_core.integrations.social.bluesky.facets import LinkSpan

bsky.post(
    "café ☕ https://example.com done",
    links=[LinkSpan(text="https://example.com", uri="https://example.com")],
)
```

Internally this calls `compute_facets()`, which locates `link.text`
inside your post and converts the match to Bluesky's wire format — a
**UTF-8 byte offset**, because the AT Protocol richtext spec indexes
facets in bytes, not codepoints. Executed directly, no credentials
needed:

```python
from zeo_core.integrations.social.bluesky.facets import compute_facets, LinkSpan

text = "café ☕ https://example.com done"
facets = compute_facets(text, links=[LinkSpan(text="https://example.com", uri="https://example.com")])
print(facets[0]["index"])
```

Real output:

```
{'byteStart': 10, 'byteEnd': 29}
```

But the **character** offset of that same substring is `(7, 26)` —
three lower, because `é` is 2 UTF-8 bytes (1 extra) and `☕` is 3 UTF-8
bytes (2 extra) ahead of it in the string. If you hand-built the facet
index yourself using `str.find()`/`len()` character math — the natural
first instinct — you would ship `byteStart: 7, byteEnd: 26`. Bluesky
would decode that against the byte string and highlight three bytes into
the URL: **a mangled link, silently, with no error from the API.** This
is the single most valuable thing to internalize from this tutorial:
**never hand-compute facet offsets — always go through `compute_facets()`
(or `post()`, which calls it for you).**

An all-ASCII post can't expose this bug — character and byte offsets
coincide when every character is one byte. Test with non-ASCII text
(accents, emoji, curly quotes) before you trust any facet-building code,
your own or otherwise.

## Reference

```python
BlueskyIntegration.post(
    text: str,
    links: list[LinkSpan] | None = None,
    mentions: list[MentionSpan] | None = None,
) -> IntegrationResult[dict]
```

`LinkSpan(text, uri)`; `MentionSpan(text, did)` — note `did`, not a
handle; resolving a handle to a DID is a separate, external lookup this
integration does not do for you.

## See also

- [`notion-integration.md`](notion-integration.md) — same
  `IntegrationResult` pattern, a config-file-based auth flow instead of a
  credentials-file one.
