# Runtime-supervised capability host

The host invokes an explicitly admitted Python capability provider through the
existing `CapabilityRegistry` and typed invocation helper. Install
`zeocore[runtime-host]` and run `zeo-capability` (or
`python -m zeo_core.adapters.runtime_host`). It does not install providers,
discover arbitrary entry points, load login profiles or authorize itself.

**Protocol status:** implementation candidate version 1. The Python models and
tests are executable. Joint Runtime/ZEOconnect wire review, the Go adapter and the
real Creator/Newsroom/agent/effect proofs remain required before interoperability
or deployment acceptance. A test IPC peer is not that acceptance proof.

## Install and prepare a provider

This API is available from 0.11.0 and requires Python 3.14+. Run the example
from the matching `v0.11.0` checkout:

```bash
uv pip install "zeocore[runtime-host]==0.11.0"
python examples/runtime_host_catalogue_v1.py
```

The [complete offline example](../../examples/runtime_host_catalogue_v1.py)
exports a real provider factory, builds its catalogue and prints a normalized
request and digest. It does not invoke a handler or manufacture launch authority.
The [registration guide](provider-registration.md) explains how to package the
factory and how this differs from legacy plugin loading. `runtime-host` is a
separate extra, not included by `zeocore[all]`; `make setup` includes it for tests.

The inherited Unix socket/descriptor protocol is supported by the exercised
macOS and Linux Python 3.14 environments. A Windows launcher is not provided.
A trusted Runtime supervisor is still required for every host invocation.

## Ownership and launcher prerequisites

Runtime owns organizational admission, durable operation and logical-effect IDs,
attempt fencing, resource reservations, total budgets, cancellation, artifact
storage/retrieval and the agent facade. The host owns Python provider validation
and invocation. ZEOconnect owns credential custody and exact authorized provider
dispatch. Applications retain their business logic and persistent service jobs.

The **trusted launcher** must:

1. Select an exact interpreter, installed distribution version, factory and
   immutable environment digest. Independently verify the environment/image
   against that digest. The host checks installed version and interpreter; a
   string in a context document cannot measure an environment's integrity.
2. Create a fresh private connected Unix stream socket pair. Retain the Runtime
   endpoint and pass only the child's endpoint to that host, normally FD 4.
   Never accept a model-selected socket address or reusable device credential.
3. Supply `LaunchContext` on a private inherited FD (normally 3). Close its write
   end after writing bounded UTF-8 JSON. Send `InvocationRequest` on stdin.
4. Strip ambient credentials, enforce the admitted workspace/egress policy and
   supervise the owned process group with a deadline and shutdown grace. The
   process, factory allowlist and SDK routing guards are not a Python sandbox.
5. Bind the retained channel to the actual child process/session and atomically
   redeem its bootstrap ID. Refuse reuse from a second child or an old attempt.
   The child-generated nonce is a reply correlation value, not authentication.

Pure Python composition remains inside an admitted invocation. Every protected
service effect must enter the Runtime service port. The host sets an irreversible
process-local managed-mode latch before importing a provider; the member/device
HTTP transport refuses in that mode, including connection listing and artifact
retrieval. Existing standalone programs retain their normal member path.

## Static discovery

These commands read `ProviderBinding` from the inherited binding FD. They validate
the inventory without importing its factory, reading credentials or making a
network request:

```text
zeo-capability describe --json --binding-fd 3
zeo-capability doctor --json --binding-fd 3
zeo-capability capabilities list --limit 20 --offset 0 --json --binding-fd 3
zeo-capability capabilities describe creator.plan_content_portfolio@1.0.0 --json --binding-fd 3
```

An empty inventory is valid. Missing metadata, duplicate canonical IDs,
projection collisions, invalid examples, external schema references and manifest
digest mismatch refuse. Pagination is deterministic and limited to 100 entries
per page; the overall message is limited to 1 MiB. Static readiness is explicitly
not availability or authority. Runtime filters catalogue visibility by scope and
applies per-account consent separately. Canonical IDs stay data arguments in the
preferred search/describe/run facade.

## Invocation and Runtime IPC

```text
zeo-capability invoke --request - --context-fd 3 --runtime-fd 4
```

`InvocationRequest` contains only version, exact canonical capability ID and
arguments. Context contains the admitted provider inventory, organization,
project, stable seat, runtime binding, packet, operation, attempt/fence, manifest
and normalized request digests, scope, deadline, workspace and bounds. These
claims gain authority only through the retained Runtime channel.

Each IPC message is one **4-byte unsigned big-endian length** followed by UTF-8
JSON. Both directions reject empty or over-limit messages. The limit is at most
1 MiB; each exchange has a total deadline of at most 30 seconds, further bounded
by the operation deadline. There is no transport retry. A broken exchange poisons
the session. Runtime must enforce equivalent bounds on its endpoint.

Every request carries `protocol_version`, monotonic `sequence`, `host_nonce`, the
full `AttemptBinding`, `method` and `payload`. Every reply carries the same
correlation fields, the exact canonical digest of that request, a state and data.
The host rejects a mismatched nonce, sequence, attempt or digest. Runtime must
also reject unexpected sequence, changed launch context and stale fencing.

| Method | Payload and enforcing obligation |
| --- | --- |
| `bootstrap` | Bootstrap ID, child PID and canonical launch-context digest. Runtime consumes the ID against the actual supervised child/session and its recorded context. Multiple effects may subsequently use that session. |
| `invoke.admit` | Validated/default-materialized arguments. Runtime rechecks current authority, request/manifest binding, deadline, fence, requirements and resource reservation after provider loading and immediately before invocation. |
| `effect.request` | Stable logical effect ID, opaque connection reference, connector revision digest, exact operation and arguments. Runtime recovers or creates the durable logical effect, rejects changed-input reuse, allocates the total budget and authorizes the specific effect. ZEOconnect consumes it atomically against current revocation/fencing before dispatch. |
| `result.publish` | Validated business data and its canonical digest. Runtime checks the attempt/fence/deadline, stores an immutable scoped artifact and durably accepts the result before returning its artifact references and matching data digest. |

Runtime replies use `allowed`, `refused`, `cancelled`, `waiting_approval` or
`needs_reconciliation`. An allowed effect response must contain
`logical_effect_id`, `effect_request_digest`, `authorization_id`, `receipt_id` and
`effect_disposition: confirmed`. Only Runtime/ZEOconnect evidence can establish
that disposition. A refused/waiting/cancelled effect response asserts that this
request was not consumed; if consumption or dispatch is uncertain, return
`needs_reconciliation` instead. The protocol intentionally does not let the
worker possess connector credentials or directly consume an authorization.

Same-effect redelivery preserves identity and is not permission for another
upstream request. Runtime's persistent ledger, not the host's temporary budget
counter, governs recovery across a restarted host. A new provider call during
reconciliation requires appropriate current authority. Consumption before
cancellation can leave an unresolved effect; no exactly-once provider guarantee
is implied by a local transaction. Connection consent never expands with a new
provider generation, and selecting between accounts must be explicit.

The currently provided injected service is `ctx.require_service("runtime.effects")`.
It accepts a typed `EffectRequest`. Unsupported services or filesystem bindings
are reported unavailable; the host never creates ambient clients to satisfy
them. Application-specific service implementations require reviewed injection
bindings. Newsroom retains its independent persistent service adapter.

## Canonical bytes and validation

Managed digests use `sha256:` plus lowercase hex over RFC 8785 bytes. They do not
change existing redacted invocation/audit digests. Duplicate keys, non-finite
numbers, integers outside the safe JCS integer domain and lone Unicode surrogates
are rejected. Precision-sensitive amounts belong in decimal strings.

Manifest inventories are sorted by canonical ID. Only declared set fields are
sorted: `error_codes`, `tags`, `effects.kinds`, requirements
`services`/`credentials`/`binaries`, and `requirements.network.hosts`. Request
arrays, examples, resource-key fields and filesystem role tuples retain order.
The launch digest uses that same ordered manifest projection inside the provider
binding. Other launch arrays retain their supplied order and are bound exactly.

The authorization request digest covers exactly
`{"capability_id": ..., "arguments": ...}` after JSON Schema validation and
the capability's Pydantic validation/default materialization. Runtime must bind
those same bytes; hashing raw input before applying defaults is not equivalent.
Reference byte vectors and generated JSON Schemas accompany this contract.

## Result truth

The host builds the entire registry privately, compares its complete inventory
and executable request schemas with the admitted manifests, validates examples,
then publishes one generation. Failure cannot expose an intermediate candidate.
Cleanup uses generation identity so an old handle cannot delete a replacement.
After invocation, response data must validate against its declared schema.
Provider prints and native stdout/stderr writes are directed to a sink during
execution; the machine FD carries one bounded JSON result. Provider exception
messages and tracebacks are not exposed because they may contain credentials.

| Result state | Exit |
| --- | --- |
| `succeeded` | 0 |
| `invalid_request` | 2 |
| `refused` | 3 |
| `unavailable` | 4 |
| `failed` | 5 |
| `cancelled` | 6 |
| `timed_out` | 7 |
| `protocol_error` | 8 |
| `queued`, `running`, `waiting_approval`, `needs_reconciliation` | 10 |

Consumers parse and validate the envelope on **every exit code**, including
unexpected ones. Bind operation, attempt, request, schema and permitted state
transition against durable Runtime state. The Python `parse_result` helper
checks strict JSON, model coherence, exact attempt binding and exit agreement;
the durable state transition check belongs to Runtime. Protocol disagreement
never resolves toward the exit code or authorizes redispatch. A lost result can
mean Runtime already accepted an artifact: reconnect to the existing operation.
Unknown effects stay unknown. Correct digests do not grant artifact retrieval
permission; Runtime must independently enforce organization and scope.

## Verification boundary

Run `make verify` and the host tests in `tests/test_adapters/test_runtime_host.py`.
The tests use a labelled protocol simulator. Runtime must run the shared byte
vectors in Go and prove bootstrap replay/fencing with its durable store, total
dispatch accounting, controller restart, cancellation and artifact ownership.
The first acceptance path is its real Creator portfolio planner without a
connection; Newsroom, a real agent turn and a confirmed external effect follow.
