"""RequestGuard example: reject a request before the capability body runs."""

from __future__ import annotations

import logging
from tempfile import TemporaryDirectory

from pydantic import BaseModel

from zeo_core.contracts import (
    CapabilityExample,
    CapabilityResult,
    EffectKind,
    GuardIssue,
    GuardResult,
)
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.tools import ToolContext, bound_capability_of, capability, invoke_sync


class RenameRequest(BaseModel):
    name: str


class RenameResponse(BaseModel):
    slug: str


class NonEmptyNameGuard:
    """Pydantic already typed ``name`` as str; this guard adds a policy check."""

    def check(self, request: BaseModel) -> GuardResult:
        if not isinstance(request, RenameRequest):
            return GuardResult.reject("unexpected request type")
        if not request.name.strip():
            return GuardResult.reject(
                "name must not be blank",
                issues=(GuardIssue(path="name", message="blank"),),
            )
        return GuardResult.accept()


@capability(
    id="demo.rename@1.0.0",
    description="Turn a display name into a slug.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            request={"name": "Hello World"},
            response={"slug": "hello-world"},
        ),
    ),
    guards=(NonEmptyNameGuard(),),
)
def rename(
    request: RenameRequest, ctx: ToolContext
) -> CapabilityResult[RenameResponse]:
    ctx.require_logger().info("slugifying %r", request.name)
    slug = "-".join(request.name.strip().lower().split())
    return CapabilityResult.ok(data=RenameResponse(slug=slug))


def _ctx(tmp: str) -> ToolContext:
    return ToolContext(
        run_id="guard-001",
        tool_name="rename",
        tool_version="1.0.0",
        logger=logging.getLogger("rename"),
        fs=get_fs_service(),
        work_dir=tmp,
        output_dir=tmp,
    )


def main() -> None:
    cap = bound_capability_of(rename)
    with TemporaryDirectory(prefix="zeo_guards_") as tmp:
        ctx = _ctx(tmp)
        ok = invoke_sync(cap, RenameRequest(name="Hello World"), ctx)
        print("accepted:", ok.data.slug if ok.data else ok.human_message)

        blocked = invoke_sync(cap, RenameRequest(name="   "), ctx)
        print("rejected outcome:", blocked.outcome)
        print("rejected code:", blocked.machine_message)
        print("rejected has data:", blocked.data is not None)


if __name__ == "__main__":
    main()
