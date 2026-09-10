"""Prepare a provider catalogue and canonical request offline.

Requires an editable source install with the runtime-host extra. No Runtime
session, admission, handler invocation or provider effect is created.
"""

from __future__ import annotations

from pydantic import BaseModel

from zeo_core.adapters.runtime_host.canonical import (
    canonical_bytes,
    digest,
    manifest_inventory,
)
from zeo_core.adapters.runtime_host.host import prepare_request
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.contracts.runtime import InvocationRequest
from zeo_core.tools import (
    CapabilityRegistry,
    ToolContext,
    bound_capability_of,
    capability,
)


class GreetingRequest(BaseModel):
    name: str = "World"


class GreetingResponse(BaseModel):
    message: str


@capability(
    id="demo.greet@1.0.0",
    description="Greet a person by name.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(request={}, response={"message": "Hello, World!"}),),
)
def greet(
    request: GreetingRequest, ctx: ToolContext
) -> CapabilityResult[GreetingResponse]:
    return CapabilityResult.ok(data=GreetingResponse(message=f"Hello, {request.name}!"))


def build_registry() -> CapabilityRegistry:
    """A provider factory: construct a fresh explicit catalogue without I/O."""
    registry = CapabilityRegistry()
    registry.register(bound_capability_of(greet))
    return registry


def main() -> None:
    registry = build_registry()
    inventory = manifest_inventory(registry.manifests())
    request = InvocationRequest(
        protocol_version=1, capability_id="demo.greet@1.0.0", arguments={}
    )
    validated = prepare_request(bound_capability_of(greet), request)
    bound_request = {
        "capability_id": request.capability_id,
        "arguments": validated.model_dump(mode="json"),
    }
    print(f"Capability: {request.capability_id}")
    print(f"Catalogue entries: {len(inventory)}")
    print(f"Normalized request: {canonical_bytes(bound_request).decode()}")
    print(f"Request digest: {digest(bound_request)}")
    print("PREPARATION ONLY: no Runtime admission, handler invocation or provider call")


if __name__ == "__main__":
    main()
