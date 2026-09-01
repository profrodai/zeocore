# zeocore 0.6.0

This file is the short release announcement. Full history is in
[CHANGELOG.md](CHANGELOG.md) (Keep a Changelog).

Two new integrations — **Google Docs** and **Bluesky** — and the credential
handling needed to use them safely. Everything existing keeps working; this
release adds surfaces rather than changing them.

## What you can do now

Read the text of a Google Doc and publish it to Bluesky, from a clean install,
without a developer portal for the Bluesky side:

```python
from zeo_core.integrations.google.docs import create_integration as docs
from zeo_core.integrations.social.bluesky import create_integration as bluesky
```

Google Docs gives you `get_document_text` (a recursive walk that includes
tables), plus `create_document` and `batch_update` with index-free
`replace_text` / `append_text`. Bluesky authenticates with an app password from
ordinary account settings — no OAuth, no developer app, no approval wait.

## Adopter path

1. `pip install "zeocore[google,bluesky]"` (Python 3.14+).
2. Get your tokens: [GET-STARTED.md](GET-STARTED.md) now walks through the
   developer portal for Bluesky, LinkedIn, Google, Notion and GitHub — which
   product to pick, which scopes to ask for, and where the value goes.
3. Put secrets in `.env`, which the library now actually loads.
4. Construct an integration and call it.

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
