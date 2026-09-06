# zeocore 0.9.0

This file is the short release announcement. Full history is in
[CHANGELOG.md](CHANGELOG.md).

**Supabase becomes a first-class integration, with complete teaching paths for
Supabase and governed Notion work.**

ZeoCore 0.9.0 adds the maintained Supabase Python SDK behind ZeoCore's typed,
bounded integration conventions. It also makes the Notion API 2026-03-11 and
the admitted `notion.page.upsert` effect substantially easier to learn and
operate. Python 3.14 or newer remains required.

## Supabase: five product surfaces, one explicit boundary

Install `zeocore[supabase]` to use:

- bounded PostgREST select, insert, upsert, update, delete, and named RPC;
- end-user Auth flows whose public results contain identity and expiry, never
  access or refresh tokens;
- bounded Storage bucket and object operations with traversal-resistant paths;
- named Edge Function invocation that rejects caller-supplied credential
  headers; and
- explicit async Realtime subscriptions with caller-owned lifecycle policy.

Publishable keys are the default and Row Level Security remains authoritative.
Privileged server keys require explicit opt-in and do not imply application
authorization. OAuth authorization URLs must stay on the configured Supabase
project origin, provider exception text is discarded, and lazy Realtime client
construction does not retain a raw project key.

This is an application integration, not a project-administration or custody
escape hatch. It exposes no raw SQL, arbitrary provider URL, signed bearer URL,
Management API, or `vault.decrypted_secrets` surface. Product-specific RLS,
database roles, encrypted credential envelopes, deployment isolation, backups,
and tenant proofs remain the host application's responsibility.

## Notion: complete current API plus governed upsert

The Notion integration continues to cover all 44 operations in API
`2026-03-11`: pages, blocks, databases, data sources, users, search, comments,
file uploads, views, meeting notes, Markdown, cursor pagination, and current
request shapes.

The documentation now separately teaches `notion.page.upsert`, the narrow
effect contract introduced in 0.8.0. Its request binds cited interpreted
content, the source artifact digest, destination, and a deterministic marker.
The dispatcher creates once, recognizes exact replay, replaces only the bound
page, and verifies by read-back. A lost response moves to read-only marker
reconciliation instead of issuing a blind second create.

Hosted refresh, introspection, and revocation can use organization-bound
`SecretRef` objects through a custody-internal dispatcher. The local environment
credential path remains available, but it is not the hosted multi-tenant path.

## Documentation and examples

- `docs/tutorials/supabase-integration.md` now starts at project creation and
  RLS, then walks every supported surface and the production security boundary.
- `examples/supabase_usage.py` remains read-only and does nothing until both a
  project and an explicit demo table are configured.
- `docs/tutorials/notion-integration.md` covers the complete current operation
  matrix, credentials, pagination, OAuth custody, and governed page upsert.
- `examples/notion_demo.py` is credential-free by default, while
  `examples/notion_governed_upsert.py` renders the exact closed effect request
  and immutable connector revision without contacting Notion.

## Compatibility

Existing 0.8 APIs remain available. Supabase is an optional extra and adds no
dependency to the base installation. This beta release adds public Supabase
protocols and models; no existing connector is removed or renamed.

## Install

```bash
uv pip install "zeocore==0.9.0"
```

Install only the provider extras you use, for example:

```bash
uv pip install "zeocore[notion,supabase]==0.9.0"
```

The public repository, issues, documentation and changelog are at
[github.com/profrodai/zeocore](https://github.com/profrodai/zeocore).
