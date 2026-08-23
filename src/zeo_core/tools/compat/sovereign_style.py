"""Transitional Sovereign Agent-style keyword-function adapter. Not canonical."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Sequence
from typing import Any, get_type_hints

from pydantic import BaseModel, Field, create_model

from zeo_core.contracts import (
    CapabilityExample,
    CapabilityResult,
    ConcurrencyMode,
    EffectKind,
)
from zeo_core.tools.context import ToolContext
from zeo_core.tools.definition_builder import build_definition
from zeo_core.tools.invoke import BoundCapability

_ANN_TO_TYPE: dict[Any, type] = {
    str: str,
    int: int,
    float: float,
    bool: bool,
    list: list[Any],
    dict: dict[str, Any],
}


class ScalarWrapResponse(BaseModel):
    value: object


class DictWrapResponse(BaseModel):
    payload: dict[str, Any]


def sovereign_style_capability(  # noqa: C901 -- transitional keyword adapter
    *,
    capability_id: str,
    description: str,
    effects: Sequence[EffectKind],
    examples: Sequence[CapabilityExample],
    concurrency: ConcurrencyMode = ConcurrencyMode.PARALLEL_SAFE,
    error_codes: Sequence[str] = (),
) -> Callable[[Callable[..., Any]], BoundCapability]:
    """
    Wrap a keyword-argument function the way Sovereign Agent's @register_tool
    did. Canonical authors must use @capability with Pydantic request models.

    Dict/scalar returns are wrapped into CapabilityResult for migration only.
    """

    def decorator(fn: Callable[..., Any]) -> BoundCapability:
        hints = get_type_hints(fn)
        fields: dict[str, Any] = {}
        sig = inspect.signature(fn)
        for name, param in sig.parameters.items():
            if name in {"self", "ctx", "context"}:
                continue
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue
            ann = hints.get(name, str)
            py_type = _ANN_TO_TYPE.get(ann, ann if isinstance(ann, type) else Any)
            if param.default is inspect.Parameter.empty:
                fields[name] = (py_type, Field(...))
            else:
                fields[name] = (py_type, param.default)
        request_model = create_model(f"{fn.__name__.title()}CompatRequest", **fields)

        def _invoke(request: BaseModel, ctx: ToolContext) -> CapabilityResult[Any]:
            kwargs = request.model_dump()
            # Best-effort ctx injection if the function asked for it.
            if "ctx" in sig.parameters:
                kwargs["ctx"] = ctx
            result = fn(**kwargs)
            if inspect.isawaitable(result):
                raise TypeError(
                    "async sovereign-style tools must be awaited by a custom wrapper"
                )
            if isinstance(result, CapabilityResult):
                return result
            if isinstance(result, dict):
                return CapabilityResult.ok(data=DictWrapResponse(payload=result))
            return CapabilityResult.ok(data=ScalarWrapResponse(value=result))

        definition = build_definition(
            capability_id=capability_id,
            description=description,
            request_model=request_model,
            response_model=DictWrapResponse,
            effects=effects,
            examples=examples,
            error_codes=error_codes,
            concurrency=concurrency,
        )
        return BoundCapability(
            definition=definition,
            fn=_invoke,
            request_model=request_model,
            is_async=inspect.iscoroutinefunction(fn),
        )

    return decorator
