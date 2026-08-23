# zeocore 0.5.0

This file is the short release announcement. Full history is in
[CHANGELOG.md](CHANGELOG.md) (Keep a Changelog).

Capability consolidation: ZeoCore is the canonical capability-authoring and
capability-contract library for the Zero Employee ecosystem. Sovereign Agent
is not moved into this package. Existing `BaseZeoTool`, HTTP, and MCP callers
keep working.

## Adopter path

1. `pip install zeocore` (Python 3.13+).
2. Run [`examples/capability_authoring.py`](examples/capability_authoring.py).
3. Read [GET-STARTED.md — Capabilities](GET-STARTED.md#capabilities).
4. Bind HTTP (`examples/http_adapter_usage.py`, extra `zeocore[http]`) or
   MCP (`examples/mcp_server_usage.py`, extra `zeocore[mcp]`). Project to
   OpenAI function tools with `examples/llm_tools_usage.py`.

## Ownership

ZeoCore defines capabilities. Sovereign Agent invokes and supervises them.
Zero Employee authorizes and evaluates their use. Effect metadata is a
declaration, not a grant.

## What landed

- Namespaced `CapabilityId` (`namespace.name@version`) and immutable
  `CapabilityDefinition` generated from Pydantic JSON Schema.
- `@capability` function authoring, `CapabilityRegistry`, request guards,
  sync/async invocation with `CapabilityOutcome`.
- OpenAI function-tool projection that refuses unsupported schema instead of
  silently weakening it.
- Invocation records with digests and redaction (not execution receipts).
- Contract pack for a later Sovereign Agent replacement audit. **No Sovereign
  Agent tool API was deleted.**

## Python

ZeoCore remains `>=3.13`. Forthcoming ecosystem releases should align on 3.13
rather than restoring ZeoCore 3.12 CI.

## Compatibility

`CapabilityResult` still branches on success / skipped / error. New `outcome`
defaults from those statuses for existing constructors.
