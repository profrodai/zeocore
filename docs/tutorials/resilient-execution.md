# Bounded retries and explicit fallback

`invoke_sync` and `invoke_async` each make one capability invocation. Use the
separate `zeo_core.execution` runner when a host application needs a total
deadline, retry policy, cancellation, or an explicitly ordered fallback.

The separation is deliberate: a capability defines typed business behavior;
the host decides how many attempts it is authorized to make.

## A two-attempt read-only policy

```python
from zeo_core.execution import ExecutionPolicy, OperationMode, run_sync

policy = ExecutionPolicy(
    operation_mode=OperationMode.READ_ONLY,
    total_timeout_seconds=120,
    attempt_timeout_seconds=90,
    attempt_targets=("ollama-local", "openai-api"),
    backoff_seconds=(0.5,),
)

result = run_sync(
    policy,
    {
        "ollama-local": ollama_target,
        "openai-api": openai_target,
    },
)
```

This policy authorizes at most two calls. The first gets at most 90 seconds.
The second gets the smaller of 90 seconds and whatever remains from the single
120-second total budget. Merely placing another target in the mapping does not
authorize it: only IDs in `attempt_targets` can run.

Each `SyncExecutionTarget` callback receives an `AttemptContext` containing
the derived per-attempt timeout and remaining total budget. A network or
subprocess adapter must apply `context.timeout_seconds` to its own I/O. The
synchronous runner cannot safely kill arbitrary in-process Python code; its
timeout boundary is therefore cooperative. The asynchronous runner additionally
enforces the boundary with `asyncio.timeout`.

## Failure classification

Targets raise `AttemptError` with a normalized `FailureKind`. Provider error
text is not copied into results or attempt records.

```python
from zeo_core.execution import AttemptError, FailureKind, SyncExecutionTarget


def call_model(context):
    try:
        return client.complete(timeout=context.timeout_seconds)
    except ProviderTimeout as error:
        raise AttemptError(FailureKind.TIMEOUT) from error


ollama_target = SyncExecutionTarget(
    target_id="ollama-local",
    response_type=str,
    invoke=call_model,
    internal_max_attempts=1,
)
```

Timeout, transient, and rate-limit failures are retryable by the default
classification, but only if another attempt appears in the explicit plan.
Validation, authorization, authentication, and permanent failures can never
be configured as retryable. Use `preflight_failure` when credentials or
authority are known to be absent before dispatch; the runner then makes zero
provider calls.

The target's `internal_max_attempts` must be exactly one. This prevents a
three-attempt client hidden beneath a two-attempt runner from making six calls.

## Results are evidence, not exceptions

`ResilientExecutionResult` has one terminal outcome:

- `SUCCEEDED`: includes the value, actual selected target, execution mode, and
  every attempt;
- `EXHAUSTED`: the explicit attempt plan or total budget was exhausted;
- `FAILED_SAFE`: a non-retryable failure ended without a success claim;
- `REFUSED`: policy, authorization, validation, or target configuration barred
  execution; or
- `CANCELLED`: cancellation was observed before a call or during a wait.

Every started attempt produces an immutable `AttemptRecord`. Records contain
normalized machine codes and timing, never raw exception or provider text.
Persist the returned records in the host's audit store when durability is
required.

## Cancellation and simulation

Pass a `CancellationToken` whose `is_cancelled()` method reflects host state.
Cancellation is checked before the first call, before each subsequent call,
and in bounded slices during backoff.

Simulated targets are refused unless `allow_simulated=True`. Even when allowed,
their successful result is labeled `ExecutionMode.SIMULATED`; it can never be
reported as live execution.

## Current safety boundary

This first public runner supports `READ_ONLY` and `ADVISORY` policies. It
refuses `EFFECTFUL` before making a call. Retrying an effect after an uncertain
timeout requires durable `DISPATCH_STARTED` state, idempotency evidence, and
reconciliation. Those mechanics cannot be emulated safely by an in-memory
retry loop.

`sync_capability_target` and `async_capability_target` adapt an existing
`BoundCapability` only when its declared effects are exactly `READ`. They keep
`invoke_sync` and `invoke_async` as one-attempt leaves and make the resilient
runner the sole retry owner.

## Hard timeouts for subprocess providers

Use `subprocess_target` when a synchronous provider can hang and must be stopped
by the host rather than trusted to observe a cooperative timeout:

```python
import json
import sys

from pydantic import BaseModel
from zeo_core.execution import SubprocessInvocation, subprocess_target


class Reply(BaseModel):
    proposed_units: int


provider = subprocess_target(
    "local-provider",
    SubprocessInvocation(
        argv=(sys.executable, "-m", "my_provider"),
        input_bytes=json.dumps(assignment).encode(),
    ),
    response_type=Reply,
    parse_stdout=Reply.model_validate_json,
)
```

The executable path must be absolute, `shell=False` is fixed, and the request
travels on stdin rather than in process-list-visible arguments. The child does
not inherit the host environment by default; pass a deliberately minimized
`env` mapping only when the child needs non-secret configuration. On timeout or
cancellation, ZeoCore terminates the whole child process group and escalates to
a kill after the configured grace period. Child stdout, stderr, request bytes,
and exception text are not copied into attempt evidence; only successfully
parsed typed output becomes the result value.

This boundary addresses a different problem from `run_sync` alone. The runner
owns the policy and total budget; the subprocess target makes that budget a
hard operating-system boundary for a blocking child.

## One-attempt LLM clients

Legacy `LLMClient.chat()` retains its provider-level retry behavior for
compatibility. New resilient call sites use `chat_once()` through
`llm_chat_target`, so the outer `ExecutionPolicy` is the only retry owner:

```python
from zeo_core.integrations.llms import OllamaClient, llm_chat_target

client = OllamaClient(model="qwen3:latest", timeout=90)
ollama_target = llm_chat_target("ollama-local", client, messages)
```

The adapter classifies only structured HTTP status codes. It never guesses an
authentication, rate-limit, or transient condition from provider prose, and it
does not retain that prose in execution evidence. Streaming callbacks are not
accepted by this adapter because retrying after partial streamed output is not
replay-safe. For a hard deadline around an LLM implemented as a separate
process, use `subprocess_target`; an in-process SDK remains cooperative with its
own configured network timeout.

## Effectful calls use durable orchestration

Do not put a write, post, payment, or delete operation into the read-only retry
runner. An effect can succeed at the provider while its response is lost; a
second attempt could duplicate it. Use `zeo_core.connections.EffectOrchestrator`
with an admitted connection, immutable connector revision, exact
`EffectAuthorization`, and provider-specific `EffectDispatcher` and
`EffectReconciler` implementations.

The orchestrator performs these steps in order:

1. Hash the request and compare the trusted organization, connection, connector
   revision, operation, request digest, audience, trusted issuer, expiry, replay
   identity, and an injected cryptographic signature verdict against the
   authorization. A refusal makes zero provider calls. The verifier has no
   permissive default: its trust roots and signature verifier are required at
   construction.
2. Load the active connection and its pinned immutable revision, and confirm the
   effectful business operation is exposed and the request is within its bound.
3. Persist `CREATED`, `AUTHORIZATION_VERIFIED`, `PREPARED`, and then
   `DISPATCH_STARTED`. Provider code is not entered until the last write commits.
4. Call `dispatcher.dispatch(...)` exactly once. A direct `CONFIRMED` result must
   carry a SHA-256 confirmation digest; a `FAILED_SAFE` result must prove no
   effect and carry a normalized error.
5. Treat every exception or lost result after dispatch as `AMBIGUOUS`. Persist
   that receipt first, then call `reconciler.reconcile(...)`—never dispatch the
   effect again. A resolution appends a new receipt pointing to the original
   ambiguity; an unresolved attempt appends evidence while current state remains
   `AMBIGUOUS`.

`SQLiteConnectionStore` makes each outcome transition, its append-only receipt,
and optional sanitized confirmation evidence one transaction. Confirmation
records store only a lowercase SHA-256 digest behind a kernel-minted
`ConfirmationEvidenceRef`; raw responses and provider exception text are not
durable inputs. The database is created with mode `0600`, enforces
organization-scoped reads, immutable revisions and execution identity,
monotonic transitions, idempotency uniqueness, and one-use authorization
nonces.

The provider call remains provider-specific engineering.
`KeychainEffectDispatcher` resolves the connection's opaque `SecretRef` into a
one-shot, expiring lease and supplies material only to the provider callback
inside that custody window. The callback must return `EffectDispatchResult`;
its exceptions are replaced with a sanitized custody error, which the
orchestrator records as post-dispatch ambiguity. Do not put credentials in the
request, an `Execution`, a receipt, confirmation evidence, argv, or environment
variables.

Connector admission happens before any of this. `validate_connector_revision`
rejects non-HTTPS or unlisted origins, redirects, unconstrained paths, open
request schemas, caller-controlled transport fields, undeclared secret
bindings, and effectful operations without reconciliation. Runtime request
admission accepts only top-level fields declared by the closed request schema;
provider URL, path, headers, cookies, authorization, redirects, and callback
targets never come from request JSON.
