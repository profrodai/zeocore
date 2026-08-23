"""Optional @capability decorator for typed function authoring."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, ParamSpec, TypeVar, get_args, get_origin, get_type_hints

from pydantic import BaseModel, ValidationError

from zeo_core.contracts import (
    CapabilityDeprecation,
    CapabilityExample,
    CapabilityRequirements,
    CapabilityResult,
    ConcurrencyMode,
    EffectKind,
    RequestGuard,
)
from zeo_core.contracts.capabilities.metadata import JsonValue
from zeo_core.tools.context import ToolContext
from zeo_core.tools.definition_builder import build_definition
from zeo_core.tools.invoke import BoundCapability

P = ParamSpec("P")
R = TypeVar("R")


class CapabilityAuthoringError(TypeError):
    """Raised when a @capability signature or contract is invalid."""


def _response_model_from_return(hint: object) -> type[BaseModel]:
    origin = get_origin(hint)
    args = get_args(hint)
    if origin is None and isinstance(hint, type):
        meta = getattr(hint, "__pydantic_generic_metadata__", None)
        if isinstance(meta, dict) and meta.get("origin") is CapabilityResult:
            origin = CapabilityResult
            args = tuple(meta.get("args") or ())
        elif issubclass(hint, CapabilityResult):
            origin = CapabilityResult
    if origin is CapabilityResult:
        if not args:
            raise CapabilityAuthoringError(
                "return annotation must be CapabilityResult[ResponseModel]"
            )
        inner = args[0]
        if isinstance(inner, type) and issubclass(inner, BaseModel):
            return inner
        raise CapabilityAuthoringError(
            "CapabilityResult type parameter must be a Pydantic BaseModel"
        )
    if hint is CapabilityResult:
        raise CapabilityAuthoringError(
            "return annotation must be CapabilityResult[ResponseModel]"
        )
    raise CapabilityAuthoringError(
        "canonical @capability functions must return CapabilityResult[ResponseModel]"
    )


def _validate_signature(
    fn: Callable[..., Any],
) -> tuple[type[BaseModel], type[BaseModel]]:
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
        raise CapabilityAuthoringError(
            "untyped **kwargs are not a canonical capability contract"
        )
    if any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params):
        raise CapabilityAuthoringError("*args is not a canonical capability contract")

    # Drop self if present (bound methods are not the intended surface).
    if params and params[0].name in {"self", "cls"}:
        params = params[1:]

    if len(params) != 2:
        raise CapabilityAuthoringError(
            "canonical signature is (request: RequestModel, ctx: ToolContext)"
        )

    request_param, ctx_param = params
    hints = get_type_hints(fn)
    request_hint = hints.get(request_param.name)
    ctx_hint = hints.get(ctx_param.name)
    return_hint = hints.get("return")

    if request_hint is None or not (
        isinstance(request_hint, type) and issubclass(request_hint, BaseModel)
    ):
        raise CapabilityAuthoringError(
            "request parameter must be annotated with a Pydantic BaseModel"
        )
    if ctx_hint is not None and ctx_hint is not ToolContext:
        # Allow string/forward refs already resolved; require ToolContext.
        if not (isinstance(ctx_hint, type) and issubclass(ctx_hint, ToolContext)):
            raise CapabilityAuthoringError(
                "ctx parameter must be annotated ToolContext"
            )
    if return_hint is None:
        raise CapabilityAuthoringError("return annotation is required")

    return request_hint, _response_model_from_return(return_hint)


def capability(
    *,
    id: str,  # noqa: A002 -- canonical keyword matches CapabilityId string form
    description: str,
    effects: Iterable[EffectKind],
    examples: Sequence[CapabilityExample],
    error_codes: Sequence[str] | frozenset[str] = (),
    concurrency: ConcurrencyMode = ConcurrencyMode.PARALLEL_SAFE,
    resource_key_fields: tuple[str, ...] = (),
    requirements: CapabilityRequirements | None = None,
    tags: Sequence[str] | frozenset[str] = (),
    metadata: Mapping[str, JsonValue] | None = None,
    deprecation: CapabilityDeprecation | None = None,
    projection_name: str | None = None,
    guards: Sequence[RequestGuard] = (),
    register_to: object | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Wrap a typed function as a BoundCapability.

    Does not register globally unless ``register_to`` is an explicit registry.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        request_model, response_model = _validate_signature(fn)
        try:
            definition = build_definition(
                capability_id=id,
                description=description,
                request_model=request_model,
                response_model=response_model,
                effects=effects,
                examples=examples,
                error_codes=error_codes,
                concurrency=concurrency,
                resource_key_fields=resource_key_fields,
                requirements=requirements,
                tags=tags,
                metadata=metadata,
                deprecation=deprecation,
                projection_name=projection_name,
            )
        except (ValidationError, ValueError) as exc:
            raise CapabilityAuthoringError(str(exc)) from exc
        bound = BoundCapability(
            definition=definition,
            fn=fn,  # type: ignore[arg-type]
            request_model=request_model,
            guards=guards,
            is_async=inspect.iscoroutinefunction(fn),
        )
        wrapped = functools.wraps(fn)(fn)
        wrapped.__zeo_capability__ = bound  # type: ignore[attr-defined]
        if register_to is not None:
            register = getattr(register_to, "register", None)
            if not callable(register):
                raise CapabilityAuthoringError(
                    "register_to must be a CapabilityRegistry"
                )
            register(bound)
        return wrapped

    return decorator


def bound_capability_of(fn: Callable[..., Any]) -> BoundCapability:
    bound = getattr(fn, "__zeo_capability__", None)
    if not isinstance(bound, BoundCapability):
        raise CapabilityAuthoringError(f"{fn!r} is not a @capability function")
    return bound
