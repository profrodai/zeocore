"""Bind a BoundCapability into OperationRegistry for HTTP/MCP adapters."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from zeo_core.core.registry import OperationRegistry
from zeo_core.tools.context import ToolContext
from zeo_core.tools.invoke import BoundCapability, invoke_async, invoke_sync


def register_capability_operation(
    capability: BoundCapability,
    *,
    registry: OperationRegistry,
    context_factory: Any,  # noqa: ANN401 -- runner-supplied ToolContext factory
    name: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """
    Expose one capability as an Operation.

    The request model is the capability's Pydantic model — not a second
    handwritten schema. HTTP and MCP both read OperationRegistry.
    """
    op_name = name or capability.definition.id.canonical()
    request_model = capability.request_model

    async def _invoke(request: BaseModel) -> dict[str, Any]:
        ctx = context_factory(capability)
        if not isinstance(ctx, ToolContext):
            raise TypeError("context_factory must return ToolContext")
        if capability.is_async:
            result = await invoke_async(capability, request, ctx)
        else:
            result = invoke_sync(capability, request, ctx)
        return result.model_dump(mode="json")

    registry.register(
        name=op_name,
        callable_=_invoke,
        request_model=request_model,
        response_model=None,
        description=description or capability.definition.description,
        tags=tags or sorted(capability.definition.tags),
    )
    return op_name
