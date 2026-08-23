"""Adapt BaseZeoTool to BoundCapability without breaking existing run()."""

from __future__ import annotations

import inspect
from collections.abc import Sequence
from typing import Any, cast, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from zeo_core.contracts import (
    CapabilityExample,
    CapabilityOutcome,
    CapabilityRequirements,
    CapabilityResult,
    ConcurrencyMode,
    EffectKind,
    RequestGuard,
)
from zeo_core.tools.base import BaseZeoTool
from zeo_core.tools.context import ToolContext
from zeo_core.tools.definition_builder import build_definition
from zeo_core.tools.invoke import BoundCapability


class ToolAdapterError(TypeError):
    """A BaseZeoTool cannot be adapted into a canonical capability."""


def _hints_for_run(tool: BaseZeoTool) -> dict[str, Any]:
    return get_type_hints(tool.run)


def _request_and_response(
    tool: BaseZeoTool,
) -> tuple[type[BaseModel], type[BaseModel]]:
    hints = _hints_for_run(tool)
    request_type = hints.get("request")
    if not (isinstance(request_type, type) and issubclass(request_type, BaseModel)):
        raise ToolAdapterError(
            f"{type(tool).__name__}.run() must annotate request with a BaseModel"
        )
    return_type = hints.get("return")
    origin = get_origin(return_type)
    args = get_args(return_type)
    inner: object
    if origin is CapabilityResult:
        inner = args[0] if args else None
    elif isinstance(return_type, type):
        meta = getattr(return_type, "__pydantic_generic_metadata__", None)
        if isinstance(meta, dict) and meta.get("origin") is CapabilityResult:
            inner = (meta.get("args") or (None,))[0]
        else:
            inner = None
    else:
        inner = None
    if not (isinstance(inner, type) and issubclass(inner, BaseModel)):
        raise ToolAdapterError(
            f"{type(tool).__name__}.run() must return CapabilityResult[ResponseModel]"
        )
    return request_type, inner


def tool_to_capability(  # noqa: C901 -- adapter collects many optional class attrs
    tool: BaseZeoTool,
    *,
    examples: Sequence[CapabilityExample] | None = None,
    effects: Sequence[EffectKind] | None = None,
    error_codes: Sequence[str] = (),
    concurrency: ConcurrencyMode = ConcurrencyMode.PARALLEL_SAFE,
    resource_key_fields: tuple[str, ...] = (),
    requirements: CapabilityRequirements | None = None,
    guards: Sequence[RequestGuard] = (),
    description: str | None = None,
) -> BoundCapability:
    """
    Adapt a class tool. Existing run()/initialize()/lifecycle remain intact.

    Registration still requires at least one example (declared here or on the
    class as ``capability_examples``). Calling ``tool.run`` directly does not
    require a definition.
    """
    name = tool.name
    if not name:
        raise ToolAdapterError(f"{type(tool).__name__} has no name")
    namespace = getattr(tool, "namespace", "zeo") or "zeo"
    version = tool.version
    declared_id = getattr(tool, "capability_id", None)
    capability_id = declared_id or f"{namespace}.{name}@{version}"

    request_model, response_model = _request_and_response(tool)
    example_list = examples
    if example_list is None:
        example_list = tuple(getattr(tool, "capability_examples", ()) or ())
    if not example_list:
        raise ToolAdapterError(
            f"{type(tool).__name__} needs capability_examples (or examples=) "
            "to become a registered capability"
        )

    raw_doc = type(tool).__dict__.get("__doc__")
    resolved_description = (
        description
        or getattr(tool, "capability_description", None)
        or (inspect.cleandoc(raw_doc).splitlines()[0] if raw_doc else None)
    )
    if not resolved_description:
        raise ToolAdapterError(f"{type(tool).__name__} needs a description")

    declared_effects = effects or getattr(tool, "capability_effects", None)
    if not declared_effects:
        declared_effects = (EffectKind.READ,)

    definition = build_definition(
        capability_id=capability_id,
        description=resolved_description,
        request_model=request_model,
        response_model=response_model,
        effects=declared_effects,
        examples=example_list,
        error_codes=error_codes or getattr(tool, "capability_error_codes", ()),
        concurrency=getattr(tool, "capability_concurrency", concurrency),
        resource_key_fields=getattr(
            tool, "capability_resource_key_fields", resource_key_fields
        ),
        requirements=requirements or getattr(tool, "capability_requirements", None),
        tags=getattr(tool, "capability_tags", ()),
    )

    def _invoke(request: BaseModel, ctx: ToolContext) -> CapabilityResult[Any]:
        init_result = tool.initialize(ctx)
        if init_result.status != "success":
            return cast(CapabilityResult[Any], init_result)
        pre_run = getattr(tool, "pre_run", None)
        if callable(pre_run):
            pre_result = pre_run(request, ctx)
            if pre_result.status != "success":
                return cast(CapabilityResult[Any], pre_result)
        result = tool.run(request, ctx)
        post_run = getattr(tool, "post_run", None)
        if callable(post_run):
            result = post_run(request, result, ctx)
        if not isinstance(result, CapabilityResult):
            return CapabilityResult.fail(
                msg="Tool run() must return CapabilityResult",
                code="ZEO_CAP_INVALID_RETURN",
                outcome=CapabilityOutcome.invalid_return,
            )
        return result

    return BoundCapability(
        definition=definition,
        fn=_invoke,
        request_model=request_model,
        guards=guards or tuple(getattr(tool, "capability_guards", ()) or ()),
        is_async=inspect.iscoroutinefunction(tool.run),
        availability=tool.is_available,
    )
