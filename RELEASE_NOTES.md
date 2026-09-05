# zeocore 0.7.0

This file is the short release announcement. Full history is in
[CHANGELOG.md](CHANGELOG.md).

**Durable effects, bounded provider resilience, and credential-safe results.**

ZeoCore 0.7.0 adds two execution paths with deliberately different safety
rules. Read-only and advisory operations can use explicit retry and fallback
plans. Effectful operations use durable state, one dispatch, and reconciliation
instead of treating a timeout as permission to try the effect again.

Python 3.14 or newer remains required.

## Durable effect orchestration

`zeo_core.connections` now includes:

- pure connection, authorization, execution, receipt and evidence contracts;
- macOS Keychain custody using opaque `SecretRef` handles;
- an organization-scoped SQLite store with immutable connector revisions,
  monotonic execution history, replay nonces and composite idempotency;
- fail-closed connector admission for origins, methods, paths, closed request
  schemas, request size, secret bindings and reconciliation declarations;
- exact authorization checks against independently supplied trusted intent,
  including required audience, issuer and injected signature verification; and
- an effect orchestrator that persists `DISPATCH_STARTED` before provider entry,
  calls the provider once, preserves `AMBIGUOUS` after uncertain outcomes, and
  reconciles without blind redispatch.

A direct or reconciled `SUCCEEDED` receipt requires positive confirmation
evidence. A provider exception cannot silently become success or safe failure.

The library supplies the enforcement boundary, not an issuer-specific signing
scheme. Applications must inject their concrete signature verifier and trust
roots; there is no permissive default.

## Read-only and advisory resilience

`zeo_core.execution` provides bounded total budgets, explicit attempt plans,
typed retry/fallback evidence, cancellation and a hard subprocess boundary.
Timeout terminates the process group rather than only its parent. Child input,
environment values, raw stdout/stderr and provider exception text are excluded
from public execution evidence.

LLM adapters expose one provider attempt so the outer policy owns every retry.
Structured status codes drive classification; provider prose cannot grant
itself retry authority.

## Credentials are not result data

Authentication results no longer have a token field. Supplying token-shaped
constructor data is rejected, which is stronger than redacting a value that the
object still carries. Keychain resolution uses a one-use lease and supplies raw
material only inside the provider callback boundary.

No release credential is stored in this repository. Publishing uses GitHub OIDC
trusted publishing, bound to `profrodai/zeocore` and `publish.yml`.

## Install

```bash
uv pip install "zeocore==0.7.0"
```

Install only the provider extras you use, for example:

```bash
uv pip install "zeocore[bluesky,llms]==0.7.0"
```

The public repository, issues, documentation and changelog are at
[github.com/profrodai/zeocore](https://github.com/profrodai/zeocore).
