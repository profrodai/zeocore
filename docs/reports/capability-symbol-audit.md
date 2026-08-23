# ZC-1 — Capability symbol-level audit

**Source:** `zeroemployeeorg/sovereign-agent` (inspected locally, not imported).
**Target:** `zeroemployeeorg/zeocore` 0.5.0 capability consolidation.
**Rule:** no source symbol is moved or copied without a recorded disposition.

Dispositions match the SOW matrix. Semantic differences and migration risk are
for the later Sovereign Agent replacement audit (ZC-12); this table is the
pre-implementation gate.

## sovereign_agent.tools

| Symbol | Behavior | Consumers | ZeoCore target | Disposition | Semantic differences | Migration risk | Test evidence |
|--------|----------|-----------|----------------|-------------|----------------------|----------------|---------------|
| `ToolResult` | Dataclass envelope: success, output dict, summary, error, `requires_human_approval` | Executor, traces, HITL, builtins | `CapabilityResult` + `CapabilityOutcome` | Do not copy | Approval flag is runtime policy; output is untyped dict | High if SA callers expect HITL on the result | `tests/unit/test_tools.py` |
| `ToolResult.to_dict` | JSON-ish serialization for LLM tool messages | Executor | `CapabilityResult.model_dump` | Map | Strict codes (`ZEO_*`) vs `SA_*` | Medium | same |
| `ToolResult.requires_human_approval` | Pauses ReAct loop | Executor HITL | none | Reject from result | Approval is Sovereign Agent | High if copied | `tests/unit/test_approval.py` |
| `_RegisteredTool` | Identity, schemas, examples, error_codes, `parallel_safe`, `verify_args`, fn | `ToolRegistry` | `CapabilityDefinition` + runtime `ZeoCapability` | Absorb by redesign | Namespaced `CapabilityId`; Pydantic schemas not annotation inference | Medium | `test_tools.py` |
| `_RegisteredTool.discover` | Builds `DiscoverySchema`; auto-fills dummy example | Discovery | `CapabilityManifest` | Absorb | ZeoCore **rejects** empty examples | Low | `test_discovery.py` |
| `_RegisteredTool.execute` | verify_args then sync/async fn; exception wrap; dict/scalar wrap | Executor | `invoke_capability` | Absorb | Canonical body must return `CapabilityResult`; wrap is compat-only | Medium | `test_parallelism.py` |
| `_RegisteredTool.parallel_safe` | Bool scheduler hint | Executor batching | `ConcurrencyMode` on effects | Absorb as declaration | Explicit modes replace bool | Low | `test_parallelism.py` |
| `_RegisteredTool.verify_args` | `(dict) -> (ok, reason)` | execute | `RequestGuard` | Absorb typed | Context-free, structured `GuardResult`, no external I/O | Medium | `test_parallelism.py` |
| `_RegisteredTool.parameters_schema` | Shallow JSON Schema from annotations | OpenAI projection, discovery | Pydantic `model_json_schema` on request model | Reject shallow builder as canonical | Richer nested models | Medium for untyped SA tools | `test_tools.py` |
| `_RegisteredTool.returns_schema` | Annotation schema | Discovery only | response model JSON Schema | Absorb | OpenAI projection still omits returns | Low | `test_discovery.py` |
| `_RegisteredTool.error_codes` / `examples` | Declared lists | Discovery | definition fields | Absorb | Examples required; no placeholder | Low | `test_discovery.py` |
| `_short` | Truncate repr for summaries | execute wrap | none | Reject | Authoring convenience | None | n/a |
| `ToolRegistry` | Register/get/list/discover_all; duplicate raise | Executor, decorator | `CapabilityRegistry` | Reconcile | Identity is `CapabilityId`; version resolve | Medium | `test_tools.py` |
| `global_registry` | Process singleton for decorator | `@register_tool` | Optional resettable convenience registry | Absorb as adapter | Must not be required production state | Medium | tests reset patterns |
| `register_tool` | Decorator; implicit global register; docstring description | User tools, README | `@capability` | Absorb as optional authoring | No implicit register unless `register_to=`; typed request model required | High for SA keyword functions | `test_tools.py` |
| `_build_params_schema` / `_build_returns_schema` / `_ann_to_schema` / `_json_safe` | Shallow annotation → JSON Schema | decorator | none (Pydantic) | Reject as canonical | Transitional adapter may keep a similar helper | Low | `test_tools.py` |
| `make_builtin_registry` | Session-scoped closures (read/write/list/handoff/complete) | Session boot | none | Leave in SA | Runtime/session policy | High if moved | builtin tests |
| Builtin `read_file` / `write_file` / `list_files` | Session-root filesystem | Agents | none as builtins | Leave in SA | Catalog may have generic fs checksum/read over `ToolContext.fs` | Medium | builtin tests |
| Builtin `handoff_to_structured` / `complete_task` | Agent control plane | Executor | none | Leave in SA | Not reusable capabilities | n/a | executor tests |

## sovereign_agent.discovery (tool-related)

| Symbol | Behavior | Consumers | ZeoCore target | Disposition | Semantic differences | Migration risk | Test evidence |
|--------|----------|-----------|----------------|-------------|----------------------|----------------|---------------|
| `DiscoverySchema` | TypedDict: name, kind, description, parameters, returns, error_codes, examples, version, metadata | Tools and non-tool extensions | `CapabilityManifest` (tools only) | Absorb and strongly type | No `kind` for planner/executor/memory; provider-neutral | Medium if SA used one schema for all extensions | `test_discovery.py` |
| `Discoverable` | Protocol with `discover()` | Registry, voice | `ZeoCapability.definition` / manifest export | Absorb for capabilities | Non-capability discoverables stay in SA | Low | `test_discovery.py` |
| `validate_schema` | Requires examples ≥ 1; shape check only | `discover_all` | definition validators | Absorb | Fail at registration, not call time; real JSON Schema | Low | `test_discovery.py` |
| `discover_all` | Batch validate | Runtime | `CapabilityRegistry.manifests()` | Absorb | Deterministic listing | Low | `test_discovery.py` |
| `discoverable` | Class decorator for non-tool extensions | Planners etc. | none | Leave in SA | Not a capability | n/a | discovery tests |
| `kind` values planner/executor/memory/half/observability/channel | Runtime extension taxonomy | SA discovery | none | Leave in SA | Non-capability | n/a | `test_discovery.py` |

## sovereign_agent.executor (tool dispatch / projection)

| Symbol | Behavior | Consumers | ZeoCore target | Disposition | Semantic differences | Migration risk | Test evidence |
|--------|----------|-----------|----------------|-------------|----------------------|----------------|---------------|
| `DefaultExecutor` / `Executor` / `ExecutorResult` | ReAct loop, turns, handoff, HITL | Sessions | none | Leave in SA | Runtime supervision | n/a | `test_executor.py` |
| `_dispatch_tool_calls` / `_invoke_tool` | Parallelism policy, unknown-tool failure, trace append | Executor | none | Leave in SA | Scheduling | n/a | `test_parallelism.py` |
| `_is_parallel_safe` | Unknown tools treated unsafe | Executor | Consumers of `ConcurrencyMode` | Leave lookup in SA | ZeoCore only declares | Low | `test_parallelism.py` |
| `_registry_to_openai_tools` | `{type:function, function:{name,description,parameters}}` | chat tools param | `adapters.llm_tools` | Absorb as adapter | Canonical ID is not a legal OpenAI name; alias required; must not strip input schema | Medium | new ZeoCore projection tests |
| `parallelism_policy` | respect_tool_flags / never / always | Executor | none | Leave in SA | Policy not declaration | n/a | `test_parallelism.py` |
| `resume_from_approval` | HITL resume | Sessions | none | Leave in SA | Governance/runtime | n/a | `test_approval.py` |
| `ToolCall` (`_internal.llm_client`) | Provider tool-call parse | Executor | none | Leave in SA | Provider session | n/a | provider tests |

## sovereign_agent.observability (tool events)

| Symbol | Behavior | Consumers | ZeoCore target | Disposition | Semantic differences | Migration risk | Test evidence |
|--------|----------|-----------|----------------|-------------|----------------------|----------------|---------------|
| `TraceEvent` / `TraceReader` / `append_trace_event` | Session JSONL traces | Reports, judges | `CapabilityInvocationRecord` (model only) | Split | ZeoCore does not persist traces | Medium for correlation IDs | observability tests |
| `executor.tool_called` payload | tool, arguments, success, summary | Session logs | record fields + runner trace | Split | No seat/session in ZeoCore record | Medium | executor tests |
| `generate_session_report` / judges | Session scoring | Operators | none | Leave in SA | Runtime | n/a | report tests |

## sovereign_agent.tickets (artifact / output manifest)

| Symbol | Behavior | Consumers | ZeoCore target | Disposition | Semantic differences | Migration risk | Test evidence |
|--------|----------|-----------|----------------|-------------|----------------------|----------------|---------------|
| `Ticket` / `TicketState` / `create_ticket` | Runtime continuity | Executor | none | Leave in SA | Execution receipts | High if moved | ticket tests |
| `OutputRecord` | path, sha256, size, content_type | `Manifest.verify` | `ArtifactRef` + `Checksum` | Extract vocabulary only | URI/storage vs session Path | Medium | manifest tests |
| `Manifest` (ticket proof-of-work) | ticket_id, operation, timings, outputs, metrics | `ticket.succeed` | none as execution manifest | Leave in SA | Distinct from `RunManifest` / invocation record | High | manifest tests |
| Nested per-tool tickets (documented, not implemented) | Aspirational | docs | none | Leave in SA | Unimplemented | n/a | n/a |

## Corresponding ZeoCore symbols (pre-0.5.0)

| Symbol | Behavior | Consumers | Role after consolidation |
|--------|----------|-----------|--------------------------|
| `BaseZeoTool` name/version | Frozen identity, no namespace | Examples, MCP | Compatibility; synthesize `zeo.<name>@<version>` |
| `ZeoToolProtocol` | Structural `run` | Typing | Superset / alias beside `ZeoCapability` |
| `ToolContext` | Frozen runner context | All tools | Extended with generic services only |
| `CapabilityResult` | success/skipped/error | All tools, HTTP/MCP | Add `CapabilityOutcome`; keep three-way status |
| `CapabilityError` | `ZEO_`/`ZC_`/`QC_` codes | Results | Unchanged prefixes; new `ZEO_CAP_*` codes |
| `contracts.capabilities.contract` | Deprecated envelope shim | Old imports | Remains shim; not `CapabilityDefinition` |
| `EchoRequest` / demo `_impl` | Demo models / internal functions | Tests | Stay demo; not catalog |
| `ArtifactRef` / `RunManifest` | Artifact + run envelope | Runners | Keep; invocation record is separate evidence |
| `Operation` / `OperationRegistry` / `get_registry` | Adapter callable registry | HTTP, MCP, jobs | Adapter over `CapabilityRegistry`; not a second capability registry |
| `PluginRegistry` | Module plugins | Discovery | Unchanged (not capabilities) |
| `IntegrationRegistry` / `IntegrationResult` | Leaf integrations | Services | Unchanged; wrappers map to `CapabilityResult` |
| `adapters.mcp.register_tool` | Introspect `run()` → Operation | MCP/HTTP | Keep name; prefer definition schemas when present |
| `integrations.llms.OpenAIClient` | Chat completions | LLM extra | Not a tool-schema projection |

## Binding refusals (must not enter ZeoCore public model)

Seat instance, agent/provider session, execution queue, worker backend, organizational approval, runtime heartbeat, relay delivery, governed execution request, SOW satisfaction, execution receipt acceptance, `requires_human_approval` on results.

## Python floor

ZeoCore remains `>=3.13`. Sovereign Agent is `>=3.12`. Ecosystem ruling for forthcoming releases: align on 3.13 (recorded in this consolidation; SA floor change is out of scope here).
