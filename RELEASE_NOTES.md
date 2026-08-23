# zeocore 0.5.0

Capability consolidation: ZeoCore is the canonical capability-authoring and
capability-contract library for the Zero Employee ecosystem. Sovereign Agent
is not moved into this package. Existing `BaseZeoTool`, HTTP, and MCP callers
keep working.

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
