# Sovereign Agent capability-replacement readiness

> Maintainer / ecosystem document — not end-user documentation. See
> [docs/README.md](../README.md).


**ZeoCore release:** 0.5.0 (`zeo_core.__version__`)
**Contracts:** `CONTRACTS_VERSION` 1.1.0, manifest schema 1.0
**Python ruling:** ZeoCore stays `>=3.13`; forthcoming ecosystem releases
align on 3.13. Sovereign Agent's floor remains `>=3.12` until a separate SA
change.
**This document does not authorize deletion of any Sovereign Agent API.**

Symbol-level dispositions are in
[capability-symbol-audit.md](capability-symbol-audit.md). Classification
below is for the *next* SA SOW after a compatibility audit with running
contract tests.

## Test receipts (ZeoCore)

Recorded 2026-08-23 in this repository (Python 3.13.11):

- `pytest tests --cov=zeo_core --cov-fail-under=90`: **2490 passed**, 4 skipped,
  coverage **90.07%**
- Focused capability suites also pass:
  `tests/test_contracts/test_capability_definition.py`,
  `tests/test_tools/test_capability_consolidation.py`,
  `tests/test_tools/test_capability_coverage.py`,
  `tests/contract_pack`
- `mypy src tests` (strict config in `pyproject.toml`): clean
- `lint-imports`: five contracts kept, including no `sovereign_agent` /
  `zero_employee` imports

The contract pack version is `zeo_core.contract_pack.PACK_VERSION` (`1.0.0`).
It does not import `sovereign_agent`.

## Per-symbol classification (Sovereign Agent)

| Symbol | Class | Notes |
|--------|-------|-------|
| `ToolResult` | adapt to ZeoCore | Map to `CapabilityResult`; drop `requires_human_approval` |
| `requires_human_approval` | retain as runtime-owned | HITL stays in SA |
| `_RegisteredTool` | adapt to ZeoCore | `CapabilityDefinition` + `BoundCapability` |
| `register_tool` | deprecate | Replace with `@capability` + optional registry; keep SA decorator during a compatibility window |
| `ToolRegistry` | adapt to ZeoCore | `CapabilityRegistry`; SA may wrap for sessions |
| `global_registry` | deprecate | Convenience only; not required production state |
| `_build_*_schema` / `_ann_to_schema` | remove after compatibility window | Pydantic schemas are canonical |
| `verify_args` | adapt to ZeoCore | `RequestGuard` |
| `parallel_safe` | adapt to ZeoCore | `ConcurrencyMode` declaration; SA keeps locks |
| `DiscoverySchema` (kind=tool) | adapt to ZeoCore | `CapabilityManifest` |
| `DiscoverySchema` other kinds | retain as runtime-owned | planners/executors/memory/half |
| `validate_schema` / `discover_all` (tools) | adapt to ZeoCore | definition validators + registry listing |
| `discoverable` | retain as runtime-owned | non-capability extensions |
| `_registry_to_openai_tools` | adapt to ZeoCore | `project_openai_tool` |
| `_dispatch_tool_calls` / `_invoke_tool` / parallelism policy | retain as runtime-owned | scheduling |
| `DefaultExecutor` / `ExecutorResult` | retain as runtime-owned | |
| `resume_from_approval` | retain as runtime-owned | |
| `executor.tool_called` traces | adapt to ZeoCore | persist `CapabilityInvocationRecord` plus SA session fields |
| `TraceEvent` / session JSONL | retain as runtime-owned | storage |
| `Ticket` / `create_ticket` | retain as runtime-owned | |
| `Manifest` / `OutputRecord` | retain as runtime-owned | extract artifact vocabulary already in `ArtifactRef` |
| `make_builtin_registry` and session builtins | retain as runtime-owned | session filesystem policy |
| `SovereignError` hierarchy | retain as runtime-owned | map codes at the adapter; do not copy into ZeoCore |
| structured-half / handoff / complete_task | retain as runtime-owned | |

Unresolved until SA runs the contract pack against real sessions: serialized
session compatibility, ticket layout, and public SA decorator deprecation
timeline.

## Gate

Sovereign Agent v0.5 tool removal must not start from this document alone.
A follow-up audit must prove equivalent success and failure behavior on
the released ZeoCore APIs, then a separate SA SOW may deprecate or delete.
