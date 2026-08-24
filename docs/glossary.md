# Glossary

**Adapter**  
A boundary that exposes a canonical capability through another interface, such
as HTTP, MCP, or an LLM function-tool schema.

**Artifact**  
A file or other durable output referenced by an invocation. The runner owns
artifact collection and retention; a capability may use an injected artifact
sink.

**`BaseZeoTool`**  
The base class for class-based tools. Subclasses define immutable name/version
identity and implement `run(request, ctx)`.

**Bound capability (`BoundCapability`)**  
An executable capability: its immutable definition plus its handler, request
model, guards, availability check, and sync/async mode.

**Capability**  
A typed, reusable operation described independently of any transport or
runner.

**`@capability`**  
The decorator that validates a typed function and attaches a bound capability.
It does not register globally unless given an explicit registry.

**Capability definition (`CapabilityDefinition`)**  
The immutable source contract: ID, description, request/response schemas,
examples, effects, requirements, error codes, and other metadata.

**Capability example (`CapabilityExample`)**  
A JSON-safe sample request and optional response. Every registered canonical
capability declares at least one.

**Capability ID (`CapabilityId`)**  
A stable identity in `namespace.name@semantic-version` form, such as
`demo.greet@1.0.0`.

**Capability manifest (`CapabilityManifest`)**  
A serializable, transport-neutral view of a capability definition used for
discovery and adapter projection.

**Capability outcome (`CapabilityOutcome`)**  
The precise invocation result, such as `success`, `policy_skipped`,
`unavailable`, `guard_rejected`, `integration_failure`, `invalid_return`,
`unexpected_exception`, or `cancelled`.

**Capability result (`CapabilityResult[T]`)**  
The standard envelope returned by every capability. It carries status,
outcome, optional typed data, human and machine messages, errors, logs, and
metadata.

**Capability status (`CapabilityStatus`)**  
The broad machine branch: `success`, `skipped`, or `error`.

**Canonical import**  
A supported public import path, primarily `zeo_core.tools`,
`zeo_core.contracts`, `zeo_core.config`, `zeo_core.core.errors`, and
`zeo_core.core.fs`, rather than their internal implementation modules.

**Context (`ToolContext`)**  
The immutable, runner-created dependency bundle supplied to a capability. It
contains run/tool identity, logger, filesystem, directories, optional
services, and JSON-safe metadata.

**Effect (`EffectKind`)**  
A declaration that an invocation may read, write, delete, communicate
externally, perform a financial action, or do security-sensitive work. An
effect is not permission.

**Entry point**  
Python package metadata used for explicit plugin discovery. Capability
packages can publish the `zeo_core.capabilities` group.

**Filesystem service (`FileSystemService`)**  
The public sandbox-aware API for file operations. Its methods return typed
operation results with `.ok` and structured error information.

**Guard (`RequestGuard`)**  
A policy check applied to an already typed request before the handler runs.
A rejection becomes a structured error result.

**Handler**  
The function that accepts `(request, ctx)` and returns
`CapabilityResult[ResponseModel]`.

**Human message**  
A result explanation intended for logs, command lines, and user interfaces.

**Integration**  
Code that talks to an external service such as GitHub, Google Calendar, or
Notion. A runner injects integration service instances through context.

**Invocation**  
One execution attempt of a bound capability with a request and context.

**Machine message**  
A stable result code used for programmatic branching. New codes should use
`ZEO_<AREA>_<DETAIL>`; `ZC_` and legacy `QC_` are also accepted.

**Metadata**  
Additional JSON-safe context on a definition, result, or `ToolContext`.
Metadata should not contain secret values.

**Pydantic model**  
The typed `BaseModel` used as a capability's request and response. ZeoCore
derives JSON Schema from these models.

**Projection**  
Conversion of a capability manifest into a provider format. Projection must
refuse an incompatible schema rather than silently weaken it.

**Registry (`CapabilityRegistry`)**  
An explicit in-process catalog of bound capabilities keyed by canonical ID.
Duplicate IDs are rejected.

**Requirement (`CapabilityRequirements`)**  
An inspectable declaration of needed services, credential names, binaries,
network access, or filesystem roles. It describes dependencies, not secret
values.

**Runner**  
The application that selects capabilities, builds context, enforces policy,
coordinates execution, and persists records or outputs. ZeoCore is the
authoring framework, not the runner.

**Skip**  
An intentional non-error result, normally a policy decision. It has status
`skipped` and outcome `policy_skipped`.

**Tool**  
A concrete class-based implementation, usually a `BaseZeoTool`. It can be
adapted to the canonical capability pipeline with `tool_to_capability`.

**Unavailable**  
A non-error inability to run because a declared dependency is missing. It has
status `skipped` and outcome `unavailable`.

**`ZeoError`**  
The base typed exception for exceptional configuration, validation, I/O,
plugin, authentication, and integration conditions outside ordinary
capability-result branching.

Continue with [ZeoCore concepts](concepts.md) or
[Author your first capability](tutorials/capability-authoring.md).
