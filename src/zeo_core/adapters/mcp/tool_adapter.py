"""
Generic BaseZeoTool -> OperationRegistry bridge.

This is the "zeotools are MCP-native by default" half of the MCP adapter:
any tool built on zeo_core's own tool-authoring surface (BaseZeoTool,
subclassed per examples/minimal_tool.py and examples/toolkit_usage.py)
can be exposed as an MCP tool with ZERO extra code from the tool author.

The mechanism is mechanical introspection, not a second, parallel
registration path:

1. ``typing.get_type_hints(tool.run)`` resolves the concrete Pydantic
   request model a tool's own ``run(request, ctx)`` declares -- the same
   type hint every tool author already writes for their own type checker.
2. That model's ``.model_json_schema()` / ``model_fields`` is real JSON
   Schema for free (Pydantic's own contract, already used everywhere in
   zeo_core.contracts).
3. ``register_tool`` wraps ``tool.run`` into the plain
   ``Callable[[TRequest], TResponse]`` shape
   ``zeo_core.core.registry.Operation`` expects, closing over a
   ``ToolContext`` built the same way examples/minimal_tool.py's own
   ``main()`` builds one, and calls ``registry.register(...)``.

Once registered, the tool is reachable from *every* adapter that reads
OperationRegistry -- today that's adapters/http and adapters/mcp, with no
adapter-specific code required per tool. This mirrors adapters/http's own
pattern (a generic shell over a registry) rather than inventing a second,
MCP-only tool-registration mechanism.
"""

from __future__ import annotations

import inspect
import typing
import uuid
from typing import Any

from pydantic import BaseModel

from zeo_core.contracts import CapabilityResult
from zeo_core.core.errors.base import ZeoError
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.core.logging import get_logger
from zeo_core.core.registry import OperationRegistry, get_registry
from zeo_core.tools.base import BaseZeoTool
from zeo_core.tools.context import ToolContext

# NOTE: typed against the concrete BaseZeoTool, not the structural
# ZeoToolProtocol -- ZeoToolProtocol.name: str | None (accurate for the
# pre-__init__ window BaseZeoTool itself documents) does not structurally
# match a concrete subclass's own narrowed `name = "my_tool"` class
# attribute under mypy strict Protocol variance. BaseZeoTool is also just
# a more honest type here: every real call site constructs a BaseZeoTool
# subclass, not a bare ZeoToolProtocol-satisfying duck type.


class ToolAdapterError(ZeoError):
    """Raised when a BaseZeoTool cannot be mechanically adapted into an Operation."""


def _resolve_request_model(tool: BaseZeoTool) -> type[BaseModel]:
    """
    Resolve the concrete Pydantic request model a tool's run() declares.

    Uses typing.get_type_hints() on the BOUND method so forward references
    resolve against the tool's own module globals (not BaseZeoTool's, whose
    abstract run() has no concrete request type to resolve).

    Raises:
        ToolAdapterError: If run() has no resolvable 'request' type hint,
            or that hint is not a BaseModel subclass. Both are tool-authoring
            bugs the adapter cannot paper over -- MCP's inputSchema has to
            come from *somewhere* real.
    """
    run = tool.run
    try:
        hints = typing.get_type_hints(run)
    except NameError as e:
        raise ToolAdapterError(
            f"Could not resolve type hints on {type(tool).__name__}.run(): {e}. "
            "MCP tool derivation requires run(request: <PydanticModel>, ctx) "
            "with a resolvable, imported (not TYPE_CHECKING-only) request type."
        ) from e

    request_type = hints.get("request")
    if request_type is None:
        raise ToolAdapterError(
            f"{type(tool).__name__}.run() has no type hint on its 'request' "
            "parameter. MCP tool derivation needs a concrete Pydantic model "
            "there, e.g. def run(self, request: MyRequest, ctx: ToolContext)."
        )

    if not (isinstance(request_type, type) and issubclass(request_type, BaseModel)):
        raise ToolAdapterError(
            f"{type(tool).__name__}.run()'s 'request' hint is "
            f"{request_type!r}, not a pydantic.BaseModel subclass. MCP tool "
            "derivation requires a Pydantic request model to derive a JSON "
            "Schema from."
        )

    return request_type


def build_tool_context(
    tool: BaseZeoTool,
    *,
    work_dir: str,
    output_dir: str,
    services: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> ToolContext:
    """
    Build a ToolContext for a mechanically-adapted tool call.

    Plays the same role examples/minimal_tool.py's own main() plays "for
    real" (a runner constructing context) -- not a mock, the same
    zeo_core.core.fs/logging services a production runner would provide.

    Args:
        tool: The tool instance the context is being built for (used for
            tool_name/tool_version identity).
        work_dir: Scratch working directory for this call.
        output_dir: Output directory for this call.
        services: Optional integration services to expose via
            ctx.services (e.g. {"google_drive": GoogleDriveService(...)}).
        metadata: Optional JSON-safe metadata to attach.
        run_id: Optional run id; a fresh uuid4 is generated if omitted.

    Returns:
        A real, runner-shaped ToolContext.
    """
    return ToolContext(
        run_id=run_id or str(uuid.uuid4()),
        tool_name=tool.name or type(tool).__name__,
        tool_version=tool.version,
        logger=get_logger(tool.name or type(tool).__name__),
        fs=get_fs_service(),
        work_dir=work_dir,
        output_dir=output_dir,
        services=services or {},
        metadata=metadata or {},
    )


def _capability_result_to_dict(result: CapabilityResult[Any]) -> dict[str, Any]:
    """
    Normalize a CapabilityResult into a JSON-serializable dict.

    invoke_operation() (zeo_core.core.registry) already normalizes dict
    results and validates JSON-serializability; this just gets a
    CapabilityResult (a pydantic BaseModel, not a dict) into dict shape
    first, the same way a hand-written Operation callable would.
    """
    return result.model_dump(mode="json")


def register_tool(
    tool: BaseZeoTool,
    *,
    registry: OperationRegistry | None = None,
    name: str | None = None,
    description: str = "",
    tags: list[str] | None = None,
    work_dir: str = ".",
    output_dir: str = ".",
    services: dict[str, Any] | None = None,
) -> str:
    """
    Register a BaseZeoTool as an Operation, mechanically.

    This is the entire "zero extra code" contract: pass any tool built on
    BaseZeoTool and it becomes callable through OperationRegistry -- which
    both adapters/http and adapters/mcp already read from -- with its
    request schema derived from the tool's own run() type hint, not
    hand-written twice.

    Args:
        tool: A BaseZeoTool instance to register.
        registry: Registry to register into. Defaults to the global
            registry (get_registry()), same default adapters/http uses.
        name: Operation name. Defaults to the tool's own .name.
        description: Human-readable description. Defaults to the tool's
            own docstring (first line) if present.
        tags: Categorization tags forwarded to Operation.
        work_dir: Working directory used to build each call's ToolContext.
        output_dir: Output directory used to build each call's ToolContext.
        services: Integration services to expose via ctx.services on every
            call made through this registration.

    Returns:
        The operation name the tool was registered under.

    Raises:
        ToolAdapterError: If the tool's run() signature cannot be
            mechanically introspected (see _resolve_request_model).
        ValueError: If the operation name is already registered
            (OperationRegistry.register's own contract).
    """
    reg = registry if registry is not None else get_registry()
    request_model = _resolve_request_model(tool)
    op_name = name or tool.name
    if not op_name:
        raise ToolAdapterError(
            f"{type(tool).__name__} has no usable name (tool.name is falsy) "
            "and no explicit name= was given to register_tool()."
        )

    # tool.__class__.__dict__ (NOT inspect.getdoc, which walks the MRO) --
    # a concrete tool with no docstring of its own must not silently
    # inherit BaseZeoTool's own class docstring as its description; an
    # honest empty string is correct there, not framework boilerplate
    # mislabeling the tool to whatever agent reads it over MCP.
    # inspect.cleandoc() still normalizes indentation/leading blank lines
    # (raw __doc__ typically starts "\n    text..." for a multi-line
    # docstring) -- only the MRO walk-up is what's being avoided here.
    raw_doc = tool.__class__.__dict__.get("__doc__")
    doc = inspect.cleandoc(raw_doc) if raw_doc else None
    resolved_description = description or (doc.splitlines()[0] if doc else "")

    def _invoke(request: BaseModel) -> dict[str, Any]:
        ctx = build_tool_context(
            tool,
            work_dir=work_dir,
            output_dir=output_dir,
            services=services,
        )
        init_result = tool.initialize(ctx)
        if init_result.status != "success":
            return _capability_result_to_dict(init_result)

        pre_run = getattr(tool, "pre_run", None)
        if callable(pre_run):
            pre_result = pre_run(request, ctx)
            if pre_result.status != "success":
                return _capability_result_to_dict(pre_result)

        result = tool.run(request, ctx)

        post_run = getattr(tool, "post_run", None)
        if callable(post_run):
            result = post_run(request, result, ctx)

        return _capability_result_to_dict(result)

    reg.register(
        name=op_name,
        callable_=_invoke,
        request_model=request_model,
        response_model=None,
        description=resolved_description,
        tags=tags or [],
    )
    return op_name
