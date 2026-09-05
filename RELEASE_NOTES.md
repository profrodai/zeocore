# zeocore 0.8.0

This file is the short release announcement. Full history is in
[CHANGELOG.md](CHANGELOG.md).

**Hosted-consumer seams, governed observations, and admitted Notion upsert.**

ZeoCore 0.8.0 keeps the local connector experience while making its execution
kernel substitutable by a private hosted connection service. Python 3.14 or
newer remains required.

## Durable reads and substitutable stores

`BrokerExecutionStore` now describes the complete persistence surface used by
effect orchestration. `SQLiteConnectionStore` is one conforming adapter rather
than part of the orchestrator's public type boundary.

Reads use a separate `ObservationOrchestrator`. It validates the immutable
connector revision, connection, operation, selected resource, exact arguments,
authorization, and idempotency before dispatch. Results are bounded and
sanitized, then stored inline or as a content-addressed artifact receipt.
Read timeouts fail safe; they do not inherit mutation ambiguity semantics.

## Notion page upsert is admitted

`notion.page.upsert` is now an immutable business operation with a closed
request model and deterministic marker. Its dispatcher creates once, recognizes
an exact replay, or replaces an existing page's content. Duplicate markers and
same-title conflicts fail before writing. If confirmation is lost after create,
the reconciler searches by marker and never blindly creates a second page.

Hosted refresh, introspection, and revocation can use organization-bound
`SecretRef` objects through a custody-internal dispatcher. The local environment
credential path remains available, but it is not the hosted multi-tenant path.

## Credential-free hosted profile

Google Drive and Docs now accept injected credential sources and API client
factories, so hosted custody can construct clients from broker-only memory
without writing token files. The selected-file profile requires explicit
`drive.file` scope.

`zeo_core.integrations.hosted` exposes a narrow authenticated transport and
protocol-compatible services for selected Drive downloads, Docs text reads,
and browser-confirmed Bluesky posts. It carries operation names, arguments,
immutable revision bindings, and idempotency keys—not provider credentials,
arbitrary URLs, methods, or headers. Downloaded artifacts are verified by size
and SHA-256 before ZeoCore writes them to a caller-local path.

Applications select `local` or `hosted` through `build_services`; when omitted,
the profile defaults from `ZEOCORE_CONNECTION_PROFILE` and remains `local` by
default. ZEOconnect owns the concrete authenticated HTTP transport, pairing,
tenant custody, OAuth UI, and hosted persistence.

## Trustworthy release gates

Coverage now has a literal two-decimal boundary with a paid meta-test: 89.99
fails and 90.00 passes. Notion unit tests no longer inherit ambient proxy state,
Google Workspace extras have clear family and connector aliases, and the async
callback and notebook-fixture warnings found during readiness review are fixed.

## Install

```bash
uv pip install "zeocore==0.8.0"
```

Install only the provider extras you use, for example:

```bash
uv pip install "zeocore[docs,drive,bluesky,notion]==0.8.0"
```

The public repository, issues, documentation and changelog are at
[github.com/profrodai/zeocore](https://github.com/profrodai/zeocore).
