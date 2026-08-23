"""Declared examples, effects, requirements, and deprecation metadata."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zeo_core.contracts.common.enums import ConcurrencyMode, EffectKind

JsonValue = Any


def assert_json_safe(value: object, path: str = "$") -> None:
    """Raise ValueError if value cannot be represented as JSON."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for i, item in enumerate(value):
            assert_json_safe(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"JSON object keys must be strings at {path}")
            assert_json_safe(item, f"{path}.{key}")
        return
    raise ValueError(f"non-JSON-safe value at {path}: {type(value).__name__}")


class CapabilityExample(BaseModel):
    """A declared request/response example. Authors must supply at least one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str | None = None
    request: dict[str, Any]
    response: dict[str, Any] | None = None
    description: str | None = None

    @field_validator("request", "response")
    @classmethod
    def _json_safe_payload(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            assert_json_safe(value)
        return value

    def request_fingerprint(self) -> str:
        return json.dumps(self.request, sort_keys=True, separators=(",", ":"))


class CapabilityEffects(BaseModel):
    """Side-effect and concurrency declarations. Not permission grants."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kinds: frozenset[EffectKind]
    concurrency: ConcurrencyMode = ConcurrencyMode.PARALLEL_SAFE
    resource_key_fields: tuple[str, ...] = ()

    @field_validator("kinds")
    @classmethod
    def _non_empty_kinds(cls, value: frozenset[EffectKind]) -> frozenset[EffectKind]:
        if not value:
            raise ValueError("effects.kinds must declare at least one EffectKind")
        return value

    @model_validator(mode="after")
    def _resource_keys_match_mode(self) -> CapabilityEffects:
        if (
            self.concurrency == ConcurrencyMode.SERIAL_PER_RESOURCE
            and not self.resource_key_fields
        ):
            raise ValueError(
                "SERIAL_PER_RESOURCE requires resource_key_fields over validated input"
            )
        if (
            self.concurrency != ConcurrencyMode.SERIAL_PER_RESOURCE
            and self.resource_key_fields
        ):
            raise ValueError(
                "resource_key_fields are only valid with SERIAL_PER_RESOURCE"
            )
        return self


class NetworkRequirement(BaseModel):
    """Network need without host secrets or ambient probing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    required: bool = False
    hosts: frozenset[str] = frozenset()


class FilesystemRequirement(BaseModel):
    """Filesystem need declared as roles, not ambient host paths."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    read: bool = False
    write: bool = False
    roles: tuple[str, ...] = ()


class CapabilityRequirements(BaseModel):
    """Inspectable dependencies. Credential names only — never secret values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    services: frozenset[str] = frozenset()
    credentials: frozenset[str] = frozenset()
    binaries: frozenset[str] = frozenset()
    network: NetworkRequirement = Field(default_factory=NetworkRequirement)
    filesystem: FilesystemRequirement = Field(default_factory=FilesystemRequirement)


class CapabilityDeprecation(BaseModel):
    """Optional deprecation status on a definition/manifest."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    deprecated: bool = False
    successor: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _successor_only_when_deprecated(self) -> CapabilityDeprecation:
        if not self.deprecated and (self.successor or self.note):
            raise ValueError("successor/note require deprecated=True")
        return self


def unique_examples(
    examples: tuple[CapabilityExample, ...],
) -> tuple[CapabilityExample, ...]:
    if not examples:
        raise ValueError("at least one example is required")
    seen: set[str] = set()
    for example in examples:
        key = example.request_fingerprint()
        if key in seen:
            raise ValueError("duplicate capability examples are forbidden")
        seen.add(key)
    return examples


def validate_json_schema(schema: dict[str, Any], *, label: str) -> dict[str, Any]:
    if not isinstance(schema, dict) or not schema:
        raise ValueError(f"{label} must be a non-empty JSON Schema object")
    if not any(
        key in schema for key in ("type", "$ref", "$defs", "properties", "items")
    ):
        raise ValueError(f"{label} is not a recognizable JSON Schema object")
    assert_json_safe(schema, label)
    return schema
