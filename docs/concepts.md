# ZeoCore concepts

ZeoCore is a Python 3.13+ framework for defining typed capabilities. It owns
the contracts and authoring surface; a separate runner owns execution policy
and the runtime environment.

## Capability lifecycle

A typical capability moves through these stages:

1. **Author:** Pydantic request and response models define the data contract.
   `@capability` or `tool_to_capability` builds an immutable definition.
2. **Discover:** an explicit `CapabilityRegistry` registers a
   `BoundCapability`, or loads package entry points.
3. **Prepare:** the runner chooses a capability and constructs an immutable
   `ToolContext` with identity, directories, logger, filesystem, and optional
   services.
4. **Validate:** `invoke_sync` or `invoke_async` validates the request, checks
   cancellation, runs request guards, and checks declared requirements.
5. **Execute:** the handler performs its operation and returns
   `CapabilityResult`.
6. **Normalize:** invalid returns and escaping exceptions become structured
   error results. Status and fine-grained outcome let the runner branch.
7. **Record or expose:** a runner can create invocation records and adapters
   can expose the same manifest through another protocol.

The registry does not invoke automatically, and importing a module does not
implicitly load configuration or services.

## Ownership boundaries

The capability author owns:

- typed request and response models;
- a stable namespaced ID and semantic version;
- description, examples, effects, requirements, and error codes;
- business behavior and structured results.

The runner owns:

- selecting and invoking capabilities;
- constructing `ToolContext`;
- credentials, services, filesystem roots, and configuration wiring;
- authorization, approval, cancellation, retries, concurrency, and locks;
- output persistence, audit records, and artifact retention.

ZeoCore adapters own transport translation. An HTTP, MCP, or LLM adapter does
not become the source of truth for the capability contract.

## `@capability` or `BaseZeoTool`?

Prefer `@capability` for a focused typed operation:

```python
@capability(...)
def greet(
    request: GreetRequest,
    ctx: ToolContext,
) -> CapabilityResult[GreetResponse]:
    ...
```

It is the direct canonical authoring path and produces a bound capability
without a class.

Use `BaseZeoTool` when the implementation naturally has class state, needs the
optional `initialize()` or `is_available()` hooks, or already uses lifecycle
mixins:

```python
class WordCountTool(BaseZeoTool):
    name = "word_count"
    version = "1.0.0"

    def run(
        self,
        request: WordCountRequest,
        ctx: ToolContext,
    ) -> CapabilityResult[WordCountResponse]:
        ...
```

Direct `run()` remains valid. To participate in the canonical registry and
adapter pipeline, call `tool_to_capability(tool)`. Adapting requires typed
Pydantic request/response models, a description, and at least one example.
Declare effects explicitly when possible; the adapter defaults to `READ` when
the class and call supply none. See
[`examples/tool_to_capability.py`](../examples/tool_to_capability.py).

## Effects and requirements

Effects declare what an invocation may do:

- `READ`
- `WRITE`
- `DELETE`
- `EXTERNAL_COMMUNICATION`
- `FINANCIAL`
- `SECURITY_SENSITIVE`

They are inspectable facts, not authorization. The runner decides whether an
effect is allowed. Concurrency metadata can additionally declare parallel,
per-capability, per-resource, or exclusive coordination; the runner owns the
actual locks.

Requirements describe dependencies such as service names, credential names,
binaries, network hosts, and filesystem roles. They do not contain secret
values. Invocation returns an unavailable result when a required injected
service or filesystem dependency is missing.

## Results and exceptions

Every capability returns `CapabilityResult`: success, intentional skip,
unavailability, or structured failure. `status` provides broad
success/skipped/error branching; `outcome` preserves the precise reason.

`ZeoError` is the typed exception hierarchy for APIs where an exception is the
appropriate contract. Invocation catches exceptions that escape a capability
handler and normalizes them into an error result. See
[Results and errors](tutorials/results-and-errors.md).

## Registry and adapters

`CapabilityRegistry` is an explicit in-process catalog keyed by canonical ID.
It rejects duplicate identities, lists deterministically, resolves versions,
and can load the `zeo_core.capabilities` entry-point group. A process-global
registry exists as a convenience, but runners do not have to use it.

A registered capability has one canonical definition. Adapters consume that
definition or its `CapabilityManifest`:

- LLM projection turns a compatible request schema into an OpenAI-style
  function tool and refuses schemas it cannot preserve;
- HTTP and MCP bindings expose operations through their transports;
- class tools enter the same path through `tool_to_capability`.

Adapters project or bind the contract; they should not weaken, duplicate, or
silently reinterpret it.

Start with [Author your first capability](tutorials/capability-authoring.md),
then use the [glossary](glossary.md) when terminology is unfamiliar.
