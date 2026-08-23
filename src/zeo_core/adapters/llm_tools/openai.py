"""Deterministic OpenAI-compatible function-tool projection."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict

from zeo_core.contracts import CapabilityManifest

_OPENAI_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_ALLOWED_KEYWORDS = {
    "type",
    "properties",
    "required",
    "items",
    "enum",
    "description",
    "title",
    "default",
    "anyOf",
    "oneOf",
    "allOf",
    "$ref",
    "$defs",
    "definitions",
    "additionalProperties",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minItems",
    "maxItems",
    "uniqueItems",
    "format",
    "const",
    "prefixItems",
    "unevaluatedProperties",
}
_FORBIDDEN_KEYWORDS = {
    "patternProperties",
    "if",
    "then",
    "else",
    "not",
    "dependentSchemas",
    "contentEncoding",
}


class ProjectionIncompatibility(BaseModel):
    """Typed refusal: the canonical schema cannot be projected without weakening."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str
    path: str


class OpenAIFunctionTool(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str = "function"
    function: dict[str, Any]


class OpenAIProjectionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: OpenAIFunctionTool | None = None
    incompatibility: ProjectionIncompatibility | None = None

    @property
    def ok(self) -> bool:
        return self.tool is not None and self.incompatibility is None


def openai_function_name(manifest: CapabilityManifest) -> str:
    if manifest.projection_name:
        return manifest.projection_name
    ident = manifest.id
    raw = f"{ident.namespace}_{ident.name}_v{ident.version.replace('.', '_')}"
    return re.sub(r"[^a-zA-Z0-9_-]", "_", raw)[:64]


def _walk_schema(node: object, path: str) -> ProjectionIncompatibility | None:
    if isinstance(node, dict):
        for key in node:
            if key in _FORBIDDEN_KEYWORDS:
                return ProjectionIncompatibility(
                    reason=(
                        f"unsupported JSON Schema keyword {key!r} cannot be preserved"
                    ),
                    path=f"{path}.{key}",
                )
        type_value = node.get("type")
        if isinstance(type_value, str) and type_value not in {
            "object",
            "array",
            "string",
            "number",
            "integer",
            "boolean",
            "null",
        }:
            return ProjectionIncompatibility(
                reason=f"unsupported JSON Schema type {type_value!r}",
                path=f"{path}.type",
            )
        for key, child in node.items():
            found = _walk_schema(child, f"{path}.{key}")
            if found is not None:
                return found
    elif isinstance(node, list):
        for i, child in enumerate(node):
            found = _walk_schema(child, f"{path}[{i}]")
            if found is not None:
                return found
    return None


def _stable_schema(schema: dict[str, Any]) -> dict[str, Any]:
    loaded: object = json.loads(json.dumps(schema, sort_keys=True))
    if not isinstance(loaded, dict):
        raise TypeError("JSON Schema object must be a dict")
    return loaded


def project_openai_tool(manifest: CapabilityManifest) -> OpenAIProjectionResult:
    """
    Project a manifest to OpenAI function-tool shape.

    Omits returns/examples/effects (provider limitation). Never drops
    required fields, $ref, enums, or nullability from the input schema.
    """
    name = openai_function_name(manifest)
    if not _OPENAI_NAME.match(name):
        return OpenAIProjectionResult(
            incompatibility=ProjectionIncompatibility(
                reason="projected function name is not OpenAI-legal",
                path="function.name",
            )
        )
    incompat = _walk_schema(manifest.request_schema, "request_schema")
    if incompat is not None:
        return OpenAIProjectionResult(incompatibility=incompat)

    parameters = _stable_schema(manifest.request_schema)
    tool = OpenAIFunctionTool(
        function={
            "name": name,
            "description": manifest.description,
            "parameters": parameters,
        }
    )
    return OpenAIProjectionResult(tool=tool)
