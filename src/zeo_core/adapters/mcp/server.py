"""
MCP server that exposes zeo_core.core.registry.OperationRegistry as MCP tools.

Mirrors adapters/http/routes/operations.py's own list-and-invoke shape:
that route lists registered operations at GET /ops and invokes one at
POST /ops/{op_name}; this module lists them via MCP's list_tools and
invokes one via MCP's call_tool. Both read the SAME OperationRegistry --
no parallel registration mechanism, per the operator's own directive.

Like adapters/http, the registry this server reads is empty by default.
Register operations into it first (directly via
zeo_core.core.registry.OperationRegistry.register, or mechanically for any
BaseZeoTool via zeo_core.adapters.mcp.register_tool) before create_server()
has anything to expose.
"""

from __future__ import annotations

import inspect
from typing import Any

from mcp.server import MCPServer
from pydantic import ValidationError

from zeo_core.core.logging import get_logger
from zeo_core.core.registry import (
    Operation,
    OperationRegistry,
    get_registry,
    invoke_operation,
)

logger = get_logger(__name__)


def _make_tool_function(
    op: Operation[Any, Any],
) -> Any:  # noqa: ANN401 -- genuinely dynamic: returns a runtime-built callable whose signature is derived per-operation, mcp's own add_tool() accepts exactly this shape
    """
    Build a plain Python function whose signature mirrors op.request_model's
    own fields, so MCP derives an inputSchema that matches the operation's
    real parameters (op_a=1, op_b=2) rather than a single opaque 'request'
    object -- the same flattening a human-written MCP tool would do by hand.
    """

    async def _tool_fn(**kwargs: Any) -> dict[str, Any]:  # noqa: ANN401 -- genuinely dynamic: kwargs are per-operation, shaped by op.request_model's own fields at runtime, no fixed signature exists to write here
        try:
            result = await invoke_operation(op, kwargs)
        except ValidationError as e:
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": e.errors(),
                },
            }
        except Exception as e:  # noqa: BLE001 -- mirrors adapters/http/routes/operations.py's own catch-all OPERATION_FAILED shape
            return {
                "success": False,
                "error": {
                    "code": "OPERATION_FAILED",
                    "message": f"Operation execution failed: {e}",
                    "details": {
                        "op_name": op.name,
                        "error_type": type(e).__name__,
                    },
                },
            }
        return {"success": True, "data": result}

    params = []
    for field_name, field_info in op.request_model.model_fields.items():
        default = (
            inspect.Parameter.empty if field_info.is_required() else field_info.default
        )
        params.append(
            inspect.Parameter(
                field_name,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=field_info.annotation,
            )
        )
    _tool_fn.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
    _tool_fn.__name__ = op.name.replace(".", "_")
    _tool_fn.__doc__ = op.description or f"Invoke the '{op.name}' zeocore operation."
    return _tool_fn


def create_server(
    registry: OperationRegistry | None = None,
    *,
    name: str = "zeocore",
    version: str = "0.1.0",
) -> MCPServer:
    """
    Create an MCP server exposing every operation currently in the registry.

    Args:
        registry: Registry to expose. Defaults to the global registry
            (get_registry()), same default adapters/http uses.
        name: MCP server name advertised to clients.
        version: MCP server version advertised to clients.

    Returns:
        A configured MCPServer with one MCP tool per registered operation,
        named after the operation (dots replaced with underscores, since
        MCP tool names are conventionally identifier-shaped).

    Note:
        This snapshots the registry's operations at call time. Register
        operations (directly, or via adapters.mcp.register_tool) BEFORE
        calling create_server(), the same ordering adapters/http's
        create_app() -> lifespan requires for its own registry read.
    """
    reg = registry if registry is not None else get_registry()
    server: MCPServer = MCPServer(name, version=version)

    for op_name in reg.list_operations():
        op = reg.get_or_error(op_name)
        server.add_tool(
            _make_tool_function(op),
            name=op.name.replace(".", "_"),
            description=op.description or f"Invoke the '{op.name}' zeocore operation.",
        )

    logger.info(
        f"MCP server '{name}' created with {len(reg.list_operations())} tool(s)"
    )
    return server


def run(
    registry: OperationRegistry | None = None,
    *,
    name: str = "zeocore",
    version: str = "0.1.0",
) -> None:
    """
    Create a server from the registry and run it over stdio.

    stdio is the transport Claude Code, Cursor, and most MCP-native coding
    agents speak by default -- this is the zero-config path for "point an
    agent at zeocore's tools". For HTTP/SSE transports, build the server
    with create_server() and call its own run_streamable_http_async() /
    run_sse_async() directly; this convenience wrapper only covers stdio.
    """
    server = create_server(registry, name=name, version=version)
    server.run()
