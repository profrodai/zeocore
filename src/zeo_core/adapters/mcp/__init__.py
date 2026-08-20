"""
MCP Adapter for zeo_core.

Optional Model Context Protocol (MCP) server that exposes ZeoCore _ops
via MCP tools -- the same protocol Claude Code, Cursor, and other MCP-native
coding agents use to call tools directly. Only available when the 'mcp'
extra is installed.

Two complementary things live here:

1. ``create_server`` / ``run`` -- an MCP server that walks
   ``zeo_core.core.registry.OperationRegistry`` (the same registry
   ``zeo_core.adapters.http`` reads from) and exposes every registered
   operation as an MCP tool. Mirrors ``adapters/http``'s
   list-and-invoke shape, MCP-shaped instead of REST-shaped.
2. ``register_tool`` -- takes any ``BaseZeoTool`` instance and registers it
   into ``OperationRegistry`` by introspecting its own ``run(request, ctx)``
   contract (the type hint on ``request`` becomes the operation's
   ``request_model``). A tool author writes zero MCP-specific code; once
   registered, the tool is reachable from both the HTTP and MCP adapters
   for free, because both read the same registry.
"""

from typing import Any

try:
    from .server import create_server, run
    from .tool_adapter import register_tool

    __all__ = ["create_server", "register_tool", "run"]
except ImportError:
    # mcp package not available - this is expected when the mcp extra is
    # not installed.
    # These stubs deliberately do not (and cannot) mirror the real
    # create_server/run/register_tool signatures -- the real ones live in
    # the modules that just failed to import, so their types are
    # unavailable here. Each stub's only job is to raise a clear,
    # actionable ImportError the moment it is used, never to be
    # call-compatible with the real implementation. This mirrors
    # adapters/http/__init__.py's own fallback-shim shape exactly.
    def create_server(  # type: ignore[misc]
        *args: Any,  # noqa: ANN401 -- genuinely dynamic: stub shim mirrors the real create_server's arbitrary signature, only ever raises
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
    ) -> None:
        raise ImportError(
            "MCP adapter requires the mcp package. "
            "Install with: pip install zeocore[mcp]"
        )

    def run(  # type: ignore[misc]
        *args: Any,  # noqa: ANN401 -- genuinely dynamic: stub shim mirrors the real run's arbitrary signature, only ever raises
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
    ) -> None:
        raise ImportError(
            "MCP adapter requires the mcp package. "
            "Install with: pip install zeocore[mcp]"
        )

    def register_tool(  # type: ignore[misc]
        *args: Any,  # noqa: ANN401 -- genuinely dynamic: stub shim mirrors the real register_tool's arbitrary signature, only ever raises
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
    ) -> None:
        raise ImportError(
            "MCP adapter requires the mcp package. "
            "Install with: pip install zeocore[mcp]"
        )

    __all__ = ["create_server", "register_tool", "run"]
