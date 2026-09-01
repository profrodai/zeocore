"""
Example: exposing a zeo_core.tools tool as an MCP server.

Requires the 'mcp' extra:

    uv pip install "zeocore[mcp]"

This example demonstrates the "zeotools are MCP-native by default" half of
zeo_core.adapters.mcp: WordCountTool below is a completely ordinary
BaseZeoTool -- no MCP-specific code, no decorators, nothing different from
examples/minimal_tool.py's own tool. register_tool() mechanically derives
an MCP tool definition from it by reading its own run(request, ctx) type
hint, and create_server() exposes the result as a real MCP server.

Two things are shown end to end:

1. Registering a tool and creating a server (create_server()).
2. Actually calling the resulting MCP tool through the real mcp SDK client,
   in-memory (no subprocess, no network) -- to prove the round trip works,
   not just that the server object constructs.

To run this as a real MCP server a coding agent (Claude Code, Cursor, etc.)
can connect to over stdio, call zeo_core.adapters.mcp.run() instead of the
in-memory Client demonstrated here:

    from zeo_core.adapters.mcp import run
    run(name="my-zeocore-app")

...after registering your own tools, and point the agent's MCP client
config at:

    python -m my_app.mcp_entrypoint

Run this file directly to see the full round trip:

    uv run examples/mcp_server_usage.py
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from zeo_core.adapters.mcp import create_server, register_tool
from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool, ToolContext


class WordCountRequest(BaseModel):
    """Request model for WordCountTool.run() -- this becomes the MCP tool's
    inputSchema, mechanically, with no separate schema to maintain."""

    text: str


class WordCountResponse(BaseModel):
    """Response payload carried inside CapabilityResult.data."""

    word_count: int
    char_count: int


class WordCountTool(BaseZeoTool):
    """
    Counts words and characters in a string.

    Identical in shape to examples/minimal_tool.py's WordCountTool -- the
    point of this example is that NOTHING about a tool changes to make it
    MCP-reachable. register_tool() does the adapting from the outside.
    """

    name = "word_count"
    version = "1.0.0"

    def run(
        self, request: WordCountRequest, ctx: ToolContext
    ) -> CapabilityResult[WordCountResponse]:
        words = request.text.split()
        return CapabilityResult.ok(
            data=WordCountResponse(
                word_count=len(words),
                char_count=len(request.text),
            ),
            msg="Word count completed",
        )


async def main() -> None:
    """
    Register a tool, build an MCP server, and call it end to end.

    Plays two roles: the "app author" wiring register_tool() at startup,
    and an "MCP client" (a stand-in for what Claude Code/Cursor would do)
    listing and calling the resulting tool.
    """
    op_name = register_tool(WordCountTool())
    print(f"Registered '{op_name}' as an MCP tool")

    server = create_server(name="zeocore-example")

    # mcp.Client can connect to a live server object directly, in-memory --
    # no subprocess or network involved. This is the same mechanism a real
    # MCP client uses over stdio/HTTP, just without the transport.
    from mcp import Client
    from mcp.types import TextContent

    async with Client(server) as client:
        tools = await client.list_tools()
        print(f"MCP tools exposed: {[t.name for t in tools.tools]}")

        result = await client.call_tool(
            "word_count", {"text": "ZeoCore tools are MCP-native by default."}
        )
        print(f"call_tool succeeded: {not result.is_error}")
        first_block = result.content[0]
        if isinstance(first_block, TextContent):
            print(f"Result: {first_block.text}")
        else:
            print(f"Result (non-text content block): {first_block!r}")


if __name__ == "__main__":
    asyncio.run(main())
