"""Helpers to build CapabilityDefinition from Pydantic models."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel

from zeo_core.contracts import (
    CapabilityDefinition,
    CapabilityDeprecation,
    CapabilityEffects,
    CapabilityExample,
    CapabilityId,
    CapabilityRequirements,
    ConcurrencyMode,
    EffectKind,
    schemas_from_models,
)
from zeo_core.contracts.capabilities.metadata import JsonValue


def build_definition(
    *,
    capability_id: str | CapabilityId,
    description: str,
    request_model: type[BaseModel],
    response_model: type[BaseModel],
    effects: Iterable[EffectKind],
    examples: Sequence[CapabilityExample],
    error_codes: Iterable[str] = (),
    concurrency: ConcurrencyMode = ConcurrencyMode.PARALLEL_SAFE,
    resource_key_fields: tuple[str, ...] = (),
    requirements: CapabilityRequirements | None = None,
    tags: Sequence[str] | frozenset[str] = (),
    metadata: Mapping[str, JsonValue] | None = None,
    deprecation: CapabilityDeprecation | None = None,
    projection_name: str | None = None,
) -> CapabilityDefinition:
    ident = (
        capability_id
        if isinstance(capability_id, CapabilityId)
        else CapabilityId.parse(capability_id)
    )
    request_schema, response_schema = schemas_from_models(request_model, response_model)
    return CapabilityDefinition(
        id=ident,
        description=description,
        request_schema=request_schema,
        response_schema=response_schema,
        examples=tuple(examples),
        error_codes=frozenset(error_codes),
        effects=CapabilityEffects(
            kinds=frozenset(effects),
            concurrency=concurrency,
            resource_key_fields=resource_key_fields,
        ),
        requirements=requirements or CapabilityRequirements(),
        tags=frozenset(tags),
        metadata=dict(metadata or {}),
        deprecation=deprecation or CapabilityDeprecation(),
        projection_name=projection_name,
    )


def lookup_path(data: Mapping[str, Any], dotted: str) -> object:
    current: object = data
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(dotted)
        current = current[part]
    return current


def coordination_key(request: BaseModel, fields: tuple[str, ...]) -> str | None:
    """Deterministic resource key. ZeoCore does not create locks."""
    if not fields:
        return None
    dumped = request.model_dump(mode="json")
    parts = [str(lookup_path(dumped, field)) for field in fields]
    return "|".join(parts)
