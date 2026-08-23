"""Function-capability authoring example (canonical @capability surface)."""

from __future__ import annotations

import logging
from tempfile import TemporaryDirectory

from pydantic import BaseModel

from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.tools import (
    CapabilityRegistry,
    ToolContext,
    bound_capability_of,
    capability,
    invoke_sync,
)


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
    logger = ctx.require_logger()
    logger.info("greeting %s", request.name)
    return CapabilityResult.ok(data=GreetResponse(message=f"Hello, {request.name}!"))


def main() -> None:
    with TemporaryDirectory(prefix="zeo_capability_") as tmp:
        ctx = ToolContext(
            run_id="greet-001",
            tool_name="greet",
            tool_version="1.0.0",
            logger=logging.getLogger("greet"),
            fs=get_fs_service(),
            work_dir=tmp,
            output_dir=tmp,
        )
        cap = bound_capability_of(greet)
        registry = CapabilityRegistry()
        registry.register(cap)
        result = invoke_sync(cap, GreetRequest(name="World"), ctx)
        print(result.data.message if result.data else result.human_message)


if __name__ == "__main__":
    main()
