"""ZC-10: contract pack runnable in ZeoCore CI without installing Sovereign Agent."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from pydantic import BaseModel

from zeo_core.adapters.llm_tools import project_openai_tool
from zeo_core.contract_pack import PACK_VERSION
from zeo_core.contracts import (
    CapabilityExample,
    CapabilityManifest,
    CapabilityOutcome,
    CapabilityResult,
    EffectKind,
)
from zeo_core.tools import (
    CapabilityRegistry,
    RecordingArtifactSink,
    ToolContext,
    bound_capability_of,
    capability,
    invocation_record,
    invoke_async,
    invoke_sync,
    resource_coordination_key,
)
from zeo_core.tools.catalog import (
    AddRequest,
    CalendarCreateRequest,
    add,
    calendar_create,
)
from zeo_core.tools.services import SERVICE_ARTIFACTS


def _ctx(**services: object) -> ToolContext:
    return ToolContext(
        run_id="pack-run",
        tool_name="pack",
        tool_version="1.0.0",
        logger=logging.getLogger("pack"),
        fs=object(),
        work_dir=".",
        output_dir=".",
        services=services,
    )


class PingRequest(BaseModel):
    n: int


class PingResponse(BaseModel):
    n: int


@capability(
    id="pack.ping@1.0.0",
    description="Async ping for the contract pack.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(request={"n": 1}, response={"n": 1}),),
)
async def ping(
    request: PingRequest, ctx: ToolContext
) -> CapabilityResult[PingResponse]:
    _ = ctx
    return CapabilityResult.ok(data=PingResponse(n=request.n))


def test_pack_version_and_registry_lookup() -> None:
    assert PACK_VERSION == "1.0.0"
    registry = CapabilityRegistry()
    cap = bound_capability_of(add)
    registry.register(cap)
    listed = registry.list_all()
    assert listed[0].definition.id.canonical() == "math.add@1.0.0"
    assert registry.get("math.add@1.0.0") is cap
    manifests = registry.manifests()
    assert manifests[0].id.name == "add"


def test_pack_manifest_projection_and_validated_invoke() -> None:
    cap = bound_capability_of(add)
    manifest = CapabilityManifest.from_definition(cap.definition)
    projected = project_openai_tool(manifest)
    assert projected.ok
    result = invoke_sync(cap, AddRequest(left="2", right="3"), _ctx())
    assert result.outcome == CapabilityOutcome.success
    assert result.data is not None


def test_pack_guard_rejection_and_async() -> None:
    cap = bound_capability_of(add)
    rejected = invoke_sync(cap, AddRequest(left="incompatible", right="pair"), _ctx())
    assert rejected.outcome == CapabilityOutcome.guard_rejected
    ping_cap = bound_capability_of(ping)
    import asyncio

    result = asyncio.run(invoke_async(ping_cap, PingRequest(n=7), _ctx()))
    assert result.data is not None
    assert result.data.n == 7


def test_pack_artifact_record_concurrency_availability() -> None:
    class Event:
        id = "e1"
        html_link = None

    class Cal:
        def create_event(self, **kwargs: object) -> object:
            class Result:
                success = True
                content = Event()
                error = None

            return Result()

    sink = RecordingArtifactSink()
    cap = bound_capability_of(calendar_create)
    req = CalendarCreateRequest.model_validate(
        {
            "calendar_id": "primary",
            "summary": "A",
            "start": {"dateTime": "2026-01-01T09:00:00Z"},
            "end": {"dateTime": "2026-01-01T09:15:00Z"},
        }
    )
    result = invoke_sync(
        cap, req, _ctx(**{"google.calendar": Cal(), SERVICE_ARTIFACTS: sink})
    )
    record = invocation_record(
        capability=cap,
        request=req,
        result=result,
        ctx=_ctx(**{SERVICE_ARTIFACTS: sink}),
        invocation_id="pack-inv",
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    assert record.artifact_refs
    assert resource_coordination_key(cap, req) == "primary"
    missing = invoke_sync(cap, req, _ctx())
    assert missing.outcome == CapabilityOutcome.unavailable
    assert "token" not in record.model_dump_json()
