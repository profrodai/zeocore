# Tutorial: author a capability, register it, invoke it, project it

This is the 0.5.0 path. Copy-paste the runnable scripts under `examples/`
rather than treating the snippets here as a second source of truth.

## 1. Define and invoke

Write a Pydantic request/response pair and a `@capability` function with
id `namespace.name@semver`, declared `effects`, and at least one
`CapabilityExample`. Call `invoke_sync` (or `invoke_async`) with a
`ToolContext` the runner builds.

See [`examples/capability_authoring.py`](../../examples/capability_authoring.py).

Class tools: subclass `BaseZeoTool`, then `tool_to_capability`.
See [`examples/tool_to_capability.py`](../../examples/tool_to_capability.py).

## 2. Register

```python
from zeo_core.tools import CapabilityRegistry, bound_capability_of

registry = CapabilityRegistry()
registry.register(bound_capability_of(greet))
```

Third-party packages can publish the `zeo_core.capabilities` entry-point
group; `CapabilityRegistry.load_entry_points()` loads them.

## 3. Guard policy (optional)

Pydantic checks shape. A `RequestGuard` checks policy before the handler
runs. See [`examples/capability_guards.py`](../../examples/capability_guards.py).

## 4. Project to an LLM function tool

```python
from zeo_core.adapters.llm_tools import project_openai_tool
from zeo_core.contracts import CapabilityManifest

manifest = CapabilityManifest.from_definition(cap.definition)
projected = project_openai_tool(manifest)
```

Unsupported JSON Schema is refused, not silently weakened.
See [`examples/llm_tools_usage.py`](../../examples/llm_tools_usage.py).

## 5. Bind HTTP or MCP

`register_capability_operation` puts the capability on
`OperationRegistry`. HTTP (`zeocore[http]`) and MCP (`zeocore[mcp]`) both
read that registry.

- HTTP: [`examples/http_adapter_usage.py`](../../examples/http_adapter_usage.py)
- MCP: [`examples/mcp_server_usage.py`](../../examples/mcp_server_usage.py)
  (class-tool `register_tool` path; same registry)

## Ownership

ZeoCore defines capabilities. A runner invokes and supervises them.
Authorization is not this package's job. `effects` are declarations, not
grants.

Full narrative: [GET-STARTED.md — Capabilities](../../GET-STARTED.md#capabilities).
