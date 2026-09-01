# zeocore 0.6.0

This file is the short release announcement. Full history is in
[CHANGELOG.md](CHANGELOG.md) (Keep a Changelog).

**Six Google integrations, Bluesky, a tutorial set, and a raised Python floor.**

## Breaking: Python 3.14 or newer is now required

**The floor moved from 3.13 to 3.14.** An environment on 3.13 will no longer
resolve new releases -- `pip` will refuse the install rather than fail at
runtime. If you are pinned to 3.13, stay on 0.5.0 until you can upgrade the
interpreter. This aligns zeocore with sovereign-agent 1.1.0, which already
requires 3.14.

Everything else in this release adds surfaces rather than changing them.

## What you can do now

Read the text of a Google Doc and publish it to Bluesky, from a clean install,
without a developer portal for the Bluesky side:

```bash
pip install "zeocore[calendar,bluesky]"
```

```python
from zeo_core.integrations.google.docs import create_integration as docs
from zeo_core.integrations.social.bluesky import create_integration as bluesky
```

**The Google modules live behind an extra.** A base `pip install zeocore` does
not pull the Google API client, so `zeo_core.integrations.google.*` will not
import until you install `[calendar]`, `[google]`, `[drive]`, `[gmail]` or
`[all]` -- they share one dependency set, and there is no separate `docs`,
`sheets` or `slides` extra. Bluesky needs `[bluesky]`.

## The integrations

- **Google Docs** -- `get_document_text` (a recursive walk that includes
  tables), plus `create_document` and `batch_update` with index-free
  `replace_text` / `append_text`.
- **Google Sheets** -- reading and writing cell ranges.
- **Google Slides** -- presentation and page access.
- **Google Calendar, Drive and Gmail** -- as before.
- **Bluesky** -- authenticates with an app password from ordinary account
  settings; no OAuth, no developer app, no approval wait. Rich-text facets are
  computed from **UTF-8 byte offsets**, so links and mentions survive emoji and
  accents. The library computes them; hand-built offsets silently mangle a post.

Every call returns the same `IntegrationResult`: check `.success` before reading
`.content`, and `.error` carries the reason.

## Tutorials

[docs/tutorials/](docs/tutorials/) now covers capability authoring, results and
errors, context/config/files, and one per integration --
[Google Docs](docs/tutorials/google-docs-integration.md),
[Bluesky](docs/tutorials/bluesky-integration.md), Calendar, Notion and MCP.
Indexed from [docs/README.md](docs/README.md).

**Every command in the two newest tutorials was executed against the installed
package before it was written down**, including the errors you will hit first.

## Adopter path

1. `pip install "zeocore[calendar,bluesky]"` (Python 3.14+).
2. Get your tokens: [GET-STARTED.md](GET-STARTED.md) walks through the developer
   portal for Bluesky, LinkedIn, Google, Notion and GitHub -- which product to
   pick, which scopes to ask for, and where the value goes.
3. Put secrets in `.env`, which the library now actually loads.
4. Construct an integration and call it.

`make doctor` reports what an environment is missing rather than failing
opaquely, if step 1 does not go cleanly.

## Credentials moved, and why you should care

Credential files used to land in **whatever directory you were standing in**,
silently. They now go to an OS-appropriate per-user location. An existing
credential is migrated once with a visible notice; if the same credential exists
in both places with different contents, the library refuses and tells you rather
than guessing.

OAuth tokens are also now checked against the scopes you were **granted** rather
than the ones the code asked for. A cached token missing a scope used to look
valid and then fail on the first API call.

If you have been running from a checkout, your existing credential is moved on
first use. Nothing is deleted.

## Ownership

Filed under the ZeoCore project. Issues and questions:
[github.com/zeroemployeeorg/zeocore](https://github.com/zeroemployeeorg/zeocore).
