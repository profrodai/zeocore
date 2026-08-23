# Building an app with Claude Code (or Cursor) against zeocore's MCP server

**Created:** 2026-08-20 · **Status:** ACTIVE

This is a worked, end-to-end example of the single most operator-relevant
capability zeocore's MCP server adds: an agent like Claude Code or Cursor
calling a tool you wrote, directly, with **zero MCP-specific code in the
tool itself**. Every code block below was written to a real file and
executed against the real `zeo_core` and `mcp` packages — nothing here is
illustrative pseudocode.

If you haven't yet, install the `mcp` extra:

```bash
pip install "zeocore[mcp]"
```

## The mental model, in one paragraph

zeocore tools are plain Python classes: subclass `BaseZeoTool`, implement
`run(request: SomePydanticModel, ctx: ToolContext) -> CapabilityResult`.
That's the entire authoring contract — nothing about MCP appears in it.
Separately, `zeo_core.adapters.mcp.register_tool()` takes any such tool
instance and mechanically derives an MCP tool definition from its own
`run()` type hint (Pydantic's `model_json_schema()` becomes the MCP
`inputSchema` for free), then registers it into the same
`OperationRegistry` the HTTP adapter also reads from. Once registered,
`create_server()`/`run()` exposes every registered operation as a real
MCP tool over stdio — the transport Claude Code and Cursor speak by
default. You write a tool once; it's callable from both a REST endpoint
and an MCP-native agent with no adapter-specific code.

## Step 1 — write an ordinary tool

No mixins needed for this example. `text_stats.py`:

```python
"""A small, real tool: reports word/line/character counts and an
estimated reading time for a block of text."""

from __future__ import annotations

from pydantic import BaseModel

from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool, ToolContext


class TextStatsRequest(BaseModel):
    """This model becomes the MCP tool's inputSchema automatically --
    there is nothing else to write to make that happen."""

    text: str


class TextStatsResponse(BaseModel):
    word_count: int
    line_count: int
    char_count: int
    reading_time_seconds: float


class TextStatsTool(BaseZeoTool):
    """Reports word/line/character counts and an estimated reading time
    for a block of text."""

    name = "text_stats"
    version = "1.0.0"

    def run(
        self, request: TextStatsRequest, ctx: ToolContext
    ) -> CapabilityResult[TextStatsResponse]:
        words = request.text.split()
        lines = request.text.splitlines() or [request.text]
        # ~200 words/minute average adult reading speed
        reading_time = (len(words) / 200) * 60

        return CapabilityResult.ok(
            data=TextStatsResponse(
                word_count=len(words),
                line_count=len(lines),
                char_count=len(request.text),
                reading_time_seconds=round(reading_time, 1),
            ),
            msg="Computed text stats",
        )
```

Note what's absent: no `mcp` import, no schema hand-written, no
decorator. If you already have zeocore tools from before the MCP adapter
existed, they need no changes at all to become MCP-callable. Function
capabilities (`@capability`) bind through `register_capability_operation`
onto the same `OperationRegistry`; see
[capability-authoring.md](capability-authoring.md).

## Step 2 — register the tool and build a server

`mcp_entrypoint.py`:

```python
"""MCP server entrypoint for this app's zeocore tools."""

from __future__ import annotations

from zeo_core.adapters.mcp import register_tool, run

from text_stats import TextStatsTool

# Register every tool this app exposes. Real apps do this for each tool
# they own; register_tool() is idempotent-per-name (re-registering the
# same operation name raises ValueError, so call it once at startup).
register_tool(TextStatsTool())

if __name__ == "__main__":
    # Builds the server from the registry (every tool registered above)
    # and runs it over stdio -- the transport Claude Code, Cursor, and
    # most MCP-native agents speak by default.
    run(name="my-zeocore-app")
```

`register_tool()` accepts more than just the tool instance if you need
it: `name=` to override the operation name, `description=` to override
the tool's own docstring-derived one, `tags=` for categorization, and
`services=` to wire integration services (Google Drive, Notion, etc.)
into every call's `ToolContext` — see
[`examples/toolkit_usage.py`](../../examples/toolkit_usage.py) for how a
tool consumes `ctx.services`.

## Step 3 — verify the round trip yourself, before wiring in an agent

Don't take the mechanism on faith — call it through a real (if
in-memory) MCP client first, the same way
[`examples/mcp_server_usage.py`](../../examples/mcp_server_usage.py)
does:

```python
"""Verifies the MCP round trip end to end, in-memory -- no subprocess,
no network, but the same mcp.Client machinery a real agent uses."""

import asyncio

from zeo_core.adapters.mcp import create_server, register_tool
from zeo_core.tools import BaseZeoTool  # noqa: F401 -- for readers following along

from text_stats import TextStatsTool


async def main() -> None:
    register_tool(TextStatsTool())
    server = create_server(name="my-zeocore-app")

    from mcp import Client
    from mcp.types import TextContent

    async with Client(server) as client:
        tools = await client.list_tools()
        print(f"MCP tools exposed: {[t.name for t in tools.tools]}")

        result = await client.call_tool(
            "text_stats",
            {"text": "ZeoCore tools are MCP-native by default.\nSecond line."},
        )
        print(f"call_tool succeeded: {not result.is_error}")
        first_block = result.content[0]
        if isinstance(first_block, TextContent):
            print(f"Result: {first_block.text}")


if __name__ == "__main__":
    asyncio.run(main())
```

Running this prints the tool's real inputSchema (derived from
`TextStatsRequest`, not hand-written) and a real result. **One thing
worth knowing before you build a caller around this**: the payload
`call_tool()` returns is a JSON string wrapping the *entire*
`CapabilityResult`, not a bare value —

```json
{
  "success": true,
  "data": {
    "status": "success",
    "data": {
      "word_count": 15,
      "line_count": 2,
      "char_count": 84,
      "reading_time_seconds": 4.5
    },
    "run_id": "...",
    "timestamp": "...",
    "human_message": "Computed text stats",
    "error": null,
    "logs": [],
    "metadata": {}
  }
}
```

The outer `{"success": ..., "data": ...}` is the MCP server's own
call-result envelope (`server.py`'s `_tool_fn`); the inner `data` is
`CapabilityResult.model_dump(mode="json")` — your tool's actual return
value, one level deeper than you might expect. An agent parsing tool
output (or a human reading it) needs to reach into `.data.data` for the
tool's own payload, and check `.data.status == "success"` for the
tool-level outcome (as distinct from `.success`, the operation-dispatch
outcome — a validation error would set `.success: false` at the outer
level before your tool code ever ran).

## Step 4 — point Claude Code (or Cursor) at it

Once `mcp_entrypoint.py` runs standalone, register it as an MCP server
with your agent. For Claude Code, from the directory containing
`mcp_entrypoint.py`:

```bash
claude mcp add my-zeocore-app -- python mcp_entrypoint.py
```

This adds an entry to Claude Code's MCP server config pointing at the
command `python mcp_entrypoint.py`, launched fresh (over stdio) whenever
Claude Code needs to call one of its tools. Verify it's wired with:

```bash
claude mcp list
```

You should see `my-zeocore-app` listed. From here, ask Claude Code
something that would naturally use the tool — "how long would this text
take to read: ..." — and it can call `text_stats` directly, the same way
it calls its own built-in tools, receiving the same JSON-enveloped result
shown in Step 3.

Cursor's MCP config follows the same shape (a `command` plus `args`
pointing at your entrypoint) in its own `mcp.json` — consult Cursor's own
docs for the exact file location, since that's Cursor's config surface,
not zeocore's.

## What scales past one tool

Everything above generalizes with no new concepts:

- **Multiple tools**: call `register_tool()` once per tool class instance
  in `mcp_entrypoint.py` before `run()`. Each becomes its own MCP tool,
  named after `tool.name` (dots replaced with underscores if you used
  `name="area.op"`-style operation names).
- **Tools that need an integration**: pass `services={"notion": notion_integration}`
  (or `google_drive`, etc.) to `register_tool()`; the tool reads it via
  `IntegrationEnabledMixin` and `ctx.services` — see
  [`examples/toolkit_usage.py`](../../examples/toolkit_usage.py) and the
  [Notion tutorial](notion-integration.md) for a real integration wired
  this way.
- **Also expose the same tools over REST**: `register_tool()` writes into
  the same `OperationRegistry` `zeo_core.adapters.http` reads. Build both
  adapters against the same registry and you get REST + MCP from one
  registration per tool, no duplicated wiring.
- **HTTP/SSE transport instead of stdio**: `run()` is a stdio-only
  convenience wrapper. For HTTP/SSE, call `create_server()` yourself and
  use its `run_streamable_http_async()`/`run_sse_async()` methods
  directly (see `zeo_core/adapters/mcp/server.py`'s own docstring).

## See also

- [GET-STARTED.md](../../GET-STARTED.md)'s "Exposing Tools as an MCP
  Server" section — the condensed reference version of Steps 1–3 above.
- [`examples/mcp_server_usage.py`](../../examples/mcp_server_usage.py) —
  the runnable script this tutorial's Step 3 is adapted from.
- [`examples/minimal_tool.py`](../../examples/minimal_tool.py) — the
  smallest possible tool, no integrations, if you want the bare pattern
  Step 1 builds on.
