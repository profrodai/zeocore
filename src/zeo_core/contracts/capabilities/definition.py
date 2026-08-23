"""Canonical capability definition generated from typed Pydantic contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zeo_core.contracts.capabilities.identity import CapabilityId
from zeo_core.contracts.capabilities.metadata import (
    CapabilityDeprecation,
    CapabilityEffects,
    CapabilityExample,
    CapabilityRequirements,
    JsonValue,
    assert_json_safe,
    unique_examples,
    validate_json_schema,
)


class CapabilityDefinition(BaseModel):
    """
    Immutable description of a reusable capability.

    Request/response JSON Schemas must come from Pydantic models, not shallow
    Python-annotation inference. Identity is frozen; malformed contracts fail
    here, not during an agent call.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: CapabilityId
    description: str
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]
    examples: tuple[CapabilityExample, ...]
    error_codes: frozenset[str] = frozenset()
    effects: CapabilityEffects
    requirements: CapabilityRequirements = Field(default_factory=CapabilityRequirements)
    tags: frozenset[str] = frozenset()
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)
    deprecation: CapabilityDeprecation = Field(default_factory=CapabilityDeprecation)
    projection_name: str | None = None

    @field_validator("description")
    @classmethod
    def _non_empty_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("description must be non-empty")
        return value.strip()

    @field_validator("request_schema")
    @classmethod
    def _request_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_json_schema(value, label="request_schema")

    @field_validator("response_schema")
    @classmethod
    def _response_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_json_schema(value, label="response_schema")

    @field_validator("examples")
    @classmethod
    def _examples(
        cls, value: tuple[CapabilityExample, ...]
    ) -> tuple[CapabilityExample, ...]:
        return unique_examples(value)

    @field_validator("error_codes")
    @classmethod
    def _error_codes(cls, value: frozenset[str]) -> frozenset[str]:
        for code in value:
            if not code.startswith(("ZEO_", "ZC_", "QC_")):
                raise ValueError(
                    f"error code must start with ZEO_, ZC_, or QC_, got {code!r}"
                )
        return value

    @field_validator("metadata")
    @classmethod
    def _metadata(cls, value: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        data = dict(value)
        assert_json_safe(data, "metadata")
        return data

    @field_validator("projection_name")
    @classmethod
    def _projection_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value or any(c for c in value if not (c.isalnum() or c in "_-")):
            raise ValueError(
                "projection_name must be a non-empty OpenAI-legal function name "
                "(letters, digits, underscore, hyphen)"
            )
        return value

    @model_validator(mode="after")
    def _frozen_ready(self) -> CapabilityDefinition:
        return self

    def canonical_id(self) -> str:
        return self.id.canonical()


def schemas_from_models(
    request_model: type[BaseModel],
    response_model: type[BaseModel],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate JSON Schemas from Pydantic models (source of truth)."""
    return (
        request_model.model_json_schema(),
        response_model.model_json_schema(),
    )
