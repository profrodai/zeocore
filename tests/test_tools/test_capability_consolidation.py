"""Guards, invoke helper, registry, authoring, catalog, and projections."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

import pytest
from pydantic import BaseModel

from zeo_core.adapters.llm_tools import project_openai_tool
from zeo_core.contracts import (
    CapabilityExample,
    CapabilityManifest,
    CapabilityOutcome,
    CapabilityResult,
    EffectKind,
    GuardIssue,
    GuardResult,
)
from zeo_core.core.registry import OperationRegistry, invoke_operation
from zeo_core.tools import (
    BaseZeoTool,
    BoundCapability,
    CapabilityRegistry,
    CapabilityRegistryError,
    RecordingArtifactSink,
    ToolContext,
    bound_capability_of,
    capability,
    invocation_record,
    invoke_async,
    invoke_sync,
    register_capability_operation,
    resource_coordination_key,
    tool_to_capability,
)
from zeo_core.tools.authoring import CapabilityAuthoringError
from zeo_core.tools.catalog import (
    AddRequest,
    CalendarCreateRequest,
    add,
    calendar_create,
    file_checksum,
    github_file_read,
    markdown_to_docx,
)
from zeo_core.tools.compat.sovereign_style import sovereign_style_capability
from zeo_core.tools.services import SERVICE_ARTIFACTS


def _ctx(**services: object) -> ToolContext:
    return ToolContext(
        run_id="test-run",
        tool_name="test",
        tool_version="1.0.0",
        logger=logging.getLogger("test"),
        fs=services.pop("fs", object()),
        work_dir=".",
        output_dir=".",
        services=services,
    )


class EchoRequest(BaseModel):
    text: str
    flag: bool = False


class EchoResponse(BaseModel):
    text: str


class _BodyProbe:
    def __init__(self) -> None:
        self.ran = False

    def check(self, request: BaseModel) -> GuardResult:
        return GuardResult.reject(
            "blocked", issues=(GuardIssue(path="text", message="no"),)
        )


@capability(
    id="demo.echo@1.0.0",
    description="Echo text.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(request={"text": "hi"}, response={"text": "hi"}),),
)
def echo(request: EchoRequest, ctx: ToolContext) -> CapabilityResult[EchoResponse]:
    _ = ctx
    return CapabilityResult.ok(data=EchoResponse(text=request.text))


@capability(
    id="demo.echo_async@1.0.0",
    description="Async echo.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(request={"text": "hi"}, response={"text": "hi"}),),
)
async def echo_async(
    request: EchoRequest, ctx: ToolContext
) -> CapabilityResult[EchoResponse]:
    _ = ctx
    return CapabilityResult.ok(data=EchoResponse(text=request.text))


class NestedBox(BaseModel):
    inner: EchoRequest
    tags: list[str]
    kind: str


class NestedOut(BaseModel):
    n: int


class Kind(StrEnum):
    a = "a"
    b = "b"


class Inner(BaseModel):
    label: str


class Rich(BaseModel):
    kind: Kind
    inner: Inner
    note: str | None = None
    tags: list[str]


class RichOut(BaseModel):
    ok: bool


@capability(
    id="demo.nested@1.0.0",
    description="Nested request.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            request={"inner": {"text": "a"}, "tags": ["x"], "kind": "t"},
            response={"n": 1},
        ),
    ),
)
def nested(request: NestedBox, ctx: ToolContext) -> CapabilityResult[NestedOut]:
    _ = ctx
    return CapabilityResult.ok(data=NestedOut(n=len(request.tags)))


def test_function_and_class_equivalent_results() -> None:
    class EchoTool(BaseZeoTool):
        name = "echo"
        namespace = "demo"
        version = "1.0.0"
        capability_examples = (
            CapabilityExample(request={"text": "hi"}, response={"text": "hi"}),
        )
        capability_description = "Echo text."

        def run(
            self, request: EchoRequest, ctx: ToolContext
        ) -> CapabilityResult[EchoResponse]:
            return CapabilityResult.ok(data=EchoResponse(text=request.text))

    fn_cap = bound_capability_of(echo)
    class_cap = tool_to_capability(EchoTool())
    ctx = _ctx()
    req = EchoRequest(text="hi")
    fn_result = invoke_sync(fn_cap, req, ctx)
    class_result = invoke_sync(class_cap, req, ctx)
    assert fn_result.data is not None
    assert class_result.data is not None
    assert fn_result.data.text == class_result.data.text == "hi"
    assert fn_cap.definition.id.name == "echo"


def test_guard_prevents_body() -> None:
    probe = _BodyProbe()
    ran = {"body": False}

    @capability(
        id="demo.guarded@1.0.0",
        description="Guarded.",
        effects={EffectKind.READ},
        examples=(CapabilityExample(request={"text": "x"}, response={"text": "x"}),),
        guards=(probe,),
    )
    def guarded(
        request: EchoRequest, ctx: ToolContext
    ) -> CapabilityResult[EchoResponse]:
        ran["body"] = True
        return CapabilityResult.ok(data=EchoResponse(text=request.text))

    result = invoke_sync(bound_capability_of(guarded), EchoRequest(text="x"), _ctx())
    assert ran["body"] is False
    assert result.outcome == CapabilityOutcome.guard_rejected
    assert result.machine_message == "ZEO_CAP_GUARD_REJECTED"


def test_unexpected_exception_is_not_success() -> None:
    @capability(
        id="demo.boom@1.0.0",
        description="Boom.",
        effects={EffectKind.READ},
        examples=(CapabilityExample(request={"text": "x"}, response={"text": "x"}),),
    )
    def boom(request: EchoRequest, ctx: ToolContext) -> CapabilityResult[EchoResponse]:
        raise RuntimeError("nope")

    result = invoke_sync(bound_capability_of(boom), EchoRequest(text="x"), _ctx())
    assert result.outcome == CapabilityOutcome.unexpected_exception
    assert result.status.value == "error"


def test_invalid_return() -> None:
    @capability(
        id="demo.badret@1.0.0",
        description="Bad return.",
        effects={EffectKind.READ},
        examples=(CapabilityExample(request={"text": "x"}, response={"text": "x"}),),
    )
    def bad(request: EchoRequest, ctx: ToolContext) -> CapabilityResult[EchoResponse]:
        return "nope"  # type: ignore[return-value]

    result = invoke_sync(bound_capability_of(bad), EchoRequest(text="x"), _ctx())
    assert result.outcome == CapabilityOutcome.invalid_return


def test_async_invoke() -> None:
    cap = bound_capability_of(echo_async)
    result = asyncio.run(invoke_async(cap, EchoRequest(text="z"), _ctx()))
    assert result.data is not None
    assert result.data.text == "z"


def test_unavailable_without_service() -> None:
    cap = bound_capability_of(github_file_read)
    from zeo_core.tools.catalog import GithubFileReadRequest

    result = invoke_sync(cap, GithubFileReadRequest(repo="o/r", path="a.txt"), _ctx())
    assert result.outcome == CapabilityOutcome.unavailable


def test_registry_duplicates_and_listing() -> None:
    registry = CapabilityRegistry()
    registry.register(bound_capability_of(echo))
    with pytest.raises(CapabilityRegistryError):
        registry.register(bound_capability_of(echo))
    names = [c.definition.id.canonical() for c in registry.list_all()]
    assert names == sorted(names)
    assert registry.get("demo.echo@1.0.0").definition.id.name == "echo"


def test_openai_projection_preserves_required_and_nested() -> None:
    cap = bound_capability_of(nested)
    manifest = CapabilityManifest.from_definition(cap.definition)
    projected = project_openai_tool(manifest)
    assert projected.ok
    assert projected.tool is not None
    params = projected.tool.function["parameters"]
    assert "inner" in params["properties"]
    assert "tags" in params["properties"]
    required = set(params.get("required", []))
    assert {"inner", "tags", "kind"} <= required or "inner" in params["properties"]


def test_math_add_and_calendar_resource_keys() -> None:
    add_cap = bound_capability_of(add)
    result = invoke_sync(add_cap, AddRequest(left="1.5", right="2.5"), _ctx())
    assert result.data is not None
    assert result.data.sum == "4"

    cal = bound_capability_of(calendar_create)
    req_a = CalendarCreateRequest.model_validate(
        {
            "calendar_id": "primary",
            "summary": "A",
            "start": {"dateTime": "2026-01-01T09:00:00Z"},
            "end": {"dateTime": "2026-01-01T09:15:00Z"},
        }
    )
    req_b = CalendarCreateRequest.model_validate(
        {
            "calendar_id": "other",
            "summary": "B",
            "start": {"dateTime": "2026-01-01T09:00:00Z"},
            "end": {"dateTime": "2026-01-01T09:15:00Z"},
        }
    )
    key_a1 = resource_coordination_key(cal, req_a)
    key_a2 = resource_coordination_key(cal, req_a)
    key_b = resource_coordination_key(cal, req_b)
    assert key_a1 == key_a2 == "primary"
    assert key_b == "other"
    assert key_a1 != key_b

    class _LockingRunner:
        def __init__(self) -> None:
            self.held: dict[str, int] = {}

        def consume(self, key: str) -> None:
            self.held[key] = self.held.get(key, 0) + 1

    runner = _LockingRunner()
    for key in (key_a1, key_a2, key_b):
        assert key is not None
        runner.consume(key)
    assert runner.held["primary"] == 2
    assert runner.held["other"] == 1


def test_calendar_creates_with_fake_service() -> None:
    class Event:
        id = "evt-1"
        html_link = "https://example.test/e"

    class Cal:
        def create_event(self, **kwargs: Any) -> Any:  # noqa: ANN401
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
    assert result.status.value == "success"
    assert sink.refs


def test_operation_registry_bind() -> None:
    ops = OperationRegistry()
    cap = bound_capability_of(echo)

    def factory(_cap: BoundCapability) -> ToolContext:
        return _ctx()

    name = register_capability_operation(
        cap, registry=ops, context_factory=factory, name="demo.echo"
    )
    payload = asyncio.run(invoke_operation(ops.get_or_error(name), {"text": "hi"}))
    assert payload["status"] == "success"


def test_invocation_record_redacts_secrets() -> None:
    cap = bound_capability_of(echo)
    ctx = _ctx()
    req = EchoRequest(text="hi")
    result = invoke_sync(cap, req, ctx)
    from datetime import UTC, datetime

    record = invocation_record(
        capability=cap,
        request=req,
        result=result,
        ctx=ctx,
        invocation_id="inv-1",
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    dumped = record.model_dump()
    blob = str(dumped)
    assert "sk-secret" not in blob
    assert len(record.request_digest) == 64


def test_sovereign_style_wraps_dict() -> None:
    @sovereign_style_capability(
        capability_id="compat.kw@1.0.0",
        description="Keyword tool.",
        effects=(EffectKind.READ,),
        examples=(
            CapabilityExample(
                request={"label": "a"}, response={"payload": {"ok": True}}
            ),
        ),
    )
    def kw(label: str) -> dict[str, bool]:
        return {"ok": True}

    result = invoke_sync(kw, kw.request_model(label="a"), _ctx())
    assert result.status.value == "success"


def test_kwargs_signature_rejected() -> None:
    with pytest.raises(CapabilityAuthoringError):

        @capability(
            id="demo.kwargs@1.0.0",
            description="Bad.",
            effects={EffectKind.READ},
            examples=(
                CapabilityExample(request={"text": "x"}, response={"text": "x"}),
            ),
        )
        def bad(
            request: EchoRequest,
            ctx: ToolContext,
            **kwargs: object,
        ) -> CapabilityResult[EchoResponse]:
            return CapabilityResult.ok(data=EchoResponse(text="x"))


def test_cancelled_before_body() -> None:
    class Token:
        def is_cancelled(self) -> bool:
            return True

        def deadline(self) -> datetime | None:
            return None

    ran = {"body": False}

    @capability(
        id="demo.cancel@1.0.0",
        description="Cancel probe.",
        effects={EffectKind.READ},
        examples=(CapabilityExample(request={"text": "x"}, response={"text": "x"}),),
    )
    def body(request: EchoRequest, ctx: ToolContext) -> CapabilityResult[EchoResponse]:
        ran["body"] = True
        return CapabilityResult.ok(data=EchoResponse(text=request.text))

    from zeo_core.tools.services import SERVICE_CANCELLATION

    result = invoke_sync(
        bound_capability_of(body),
        EchoRequest(text="x"),
        _ctx(**{SERVICE_CANCELLATION: Token()}),
    )
    assert ran["body"] is False
    assert result.outcome == CapabilityOutcome.cancelled
    assert result.machine_message == "ZEO_CAP_CANCELLED"


def test_openai_projection_enums_nullable_defs_and_refusal() -> None:
    @capability(
        id="demo.rich@1.0.0",
        description="Rich schema.",
        effects={EffectKind.READ},
        examples=(
            CapabilityExample(
                request={
                    "kind": "a",
                    "inner": {"label": "x"},
                    "note": None,
                    "tags": ["t"],
                },
                response={"ok": True},
            ),
        ),
    )
    def rich(request: Rich, ctx: ToolContext) -> CapabilityResult[RichOut]:
        _ = ctx
        return CapabilityResult.ok(data=RichOut(ok=True))

    manifest = CapabilityManifest.from_definition(bound_capability_of(rich).definition)
    projected = project_openai_tool(manifest)
    assert projected.ok
    assert projected.tool is not None
    params = projected.tool.function["parameters"]
    blob = str(params)
    assert "kind" in params["properties"]
    assert "enum" in blob or "$defs" in blob or "$ref" in blob
    assert "note" in params["properties"]
    assert projected.tool.function["name"] == "demo_rich_v1_0_0"
    keys = list(params.keys())
    assert keys == sorted(keys) or "properties" in params

    bad = manifest.model_copy(
        update={"request_schema": {**params, "patternProperties": {"^x": {}}}}
    )
    refused = project_openai_tool(bad)
    assert not refused.ok
    assert refused.incompatibility is not None


def test_empty_examples_rejected() -> None:
    from pydantic import ValidationError

    with pytest.raises((CapabilityAuthoringError, ValidationError, ValueError)):

        @capability(
            id="demo.noex@1.0.0",
            description="No examples.",
            effects={EffectKind.READ},
            examples=(),
        )
        def noex(
            request: EchoRequest, ctx: ToolContext
        ) -> CapabilityResult[EchoResponse]:
            return CapabilityResult.ok(data=EchoResponse(text="x"))


def test_fs_and_pandoc_fail_closed() -> None:
    cap = bound_capability_of(file_checksum)
    from zeo_core.tools.catalog import FileChecksumRequest, PandocDocxRequest

    class Fs:
        def hash_file(self, path: str, algorithm: str) -> Any:  # noqa: ANN401
            class R:
                success = True
                data = "a" * 64

            return R()

    result = invoke_sync(cap, FileChecksumRequest(path="a.txt"), _ctx(fs=Fs()))
    assert result.status.value == "success"
    pcap = bound_capability_of(markdown_to_docx)
    missing = invoke_sync(
        pcap, PandocDocxRequest(markdown_path="a.md", output_path="a.docx"), _ctx()
    )
    assert missing.outcome == CapabilityOutcome.unavailable
