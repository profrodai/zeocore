"""Provider-neutral discovery manifest generated from CapabilityDefinition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from zeo_core.contracts.capabilities.definition import CapabilityDefinition
from zeo_core.contracts.capabilities.identity import CapabilityId
from zeo_core.contracts.capabilities.metadata import (
    CapabilityDeprecation,
    CapabilityEffects,
    CapabilityExample,
    CapabilityRequirements,
    JsonValue,
)
from zeo_core.contracts.common.versions import CAPABILITY_MANIFEST_SCHEMA_VERSION


class CapabilityManifest(BaseModel):
    """
    Discovery document for a capability.

    Availability is evaluated against runner-supplied context and is never a
    permanent property of this manifest.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = CAPABILITY_MANIFEST_SCHEMA_VERSION
    id: CapabilityId
    description: str
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]
    examples: tuple[CapabilityExample, ...]
    error_codes: frozenset[str]
    effects: CapabilityEffects
    requirements: CapabilityRequirements
    tags: frozenset[str]
    metadata: Mapping[str, JsonValue]
    deprecation: CapabilityDeprecation
    projection_name: str | None = None

    @classmethod
    def from_definition(cls, definition: CapabilityDefinition) -> CapabilityManifest:
        return cls(
            schema_version=CAPABILITY_MANIFEST_SCHEMA_VERSION,
            id=definition.id,
            description=definition.description,
            request_schema=definition.request_schema,
            response_schema=definition.response_schema,
            examples=definition.examples,
            error_codes=definition.error_codes,
            effects=definition.effects,
            requirements=definition.requirements,
            tags=definition.tags,
            metadata=dict(definition.metadata),
            deprecation=definition.deprecation,
            projection_name=definition.projection_name,
        )
