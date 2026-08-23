"""Project a CapabilityManifest to an OpenAI function tool (or refuse)."""

from __future__ import annotations

from pydantic import BaseModel

from zeo_core.adapters.llm_tools import project_openai_tool
from zeo_core.contracts import (
    CapabilityExample,
    CapabilityManifest,
    CapabilityResult,
    EffectKind,
)
from zeo_core.tools import ToolContext, bound_capability_of, capability


class GreetRequest(BaseModel):
    name: str


class GreetResponse(BaseModel):
    message: str


@capability(
    id="demo.greet@1.0.0",
    description="Greet a person by name.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            request={"name": "World"},
            response={"message": "Hello, World!"},
        ),
    ),
)
def greet(request: GreetRequest, ctx: ToolContext) -> CapabilityResult[GreetResponse]:
    _ = ctx
    return CapabilityResult.ok(data=GreetResponse(message=f"Hello, {request.name}!"))


def main() -> None:
    cap = bound_capability_of(greet)
    manifest = CapabilityManifest.from_definition(cap.definition)
    projected = project_openai_tool(manifest)
    if projected.ok and projected.tool is not None:
        fn = projected.tool.function
        print("projected name:", fn["name"])
        print("description:", fn["description"])
        print("required:", fn["parameters"].get("required"))
        print("properties:", sorted(fn["parameters"].get("properties", {})))
    else:
        print("incompatible:", projected.incompatibility)

    # Unsupported JSON Schema keywords are refused, not silently stripped.
    bad = manifest.model_copy(
        update={"request_schema": {"type": "object", "not": {"type": "string"}}}
    )
    refused = project_openai_tool(bad)
    print("refusal ok:", refused.ok)
    if refused.incompatibility is not None:
        print("refusal reason:", refused.incompatibility.reason)


if __name__ == "__main__":
    main()
