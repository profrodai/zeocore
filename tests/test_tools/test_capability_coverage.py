"""Extra coverage for registry, catalog wrappers, invoke, and authoring."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from zeo_core.adapters.llm_tools import project_openai_tool
from zeo_core.adapters.llm_tools.openai import openai_function_name
from zeo_core.contracts import (
    CapabilityExample,
    CapabilityManifest,
    CapabilityOutcome,
    CapabilityResult,
    EffectKind,
)
from zeo_core.core.registry import OperationRegistry, invoke_operation
from zeo_core.tools import (
    BaseZeoTool,
    BoundCapability,
    CapabilityRegistry,
    CapabilityRegistryError,
    ToolContext,
    bound_capability_of,
    capability,
    get_capability_registry,
    invoke_async,
    invoke_sync,
    register_capability_operation,
    reset_capability_registry,
    tool_to_capability,
)
from zeo_core.tools.adapter import ToolAdapterError
from zeo_core.tools.authoring import CapabilityAuthoringError
from zeo_core.tools.catalog import (
    CalendarCreateRequest,
    FileChecksumRequest,
    GithubFileReadRequest,
    PandocDocxRequest,
    add,
    calendar_create,
    file_checksum,
    github_file_read,
    markdown_to_docx,
)
from zeo_core.tools.compat.sovereign_style import sovereign_style_capability
from zeo_core.tools.services import SERVICE_ARTIFACTS, RecordingArtifactSink


def _ctx(**services: object) -> ToolContext:
    return ToolContext(
        run_id="cov-run",
        tool_name="cov",
        tool_version="1.0.0",
        logger=logging.getLogger("cov"),
        fs=services.pop("fs", object()),
        work_dir=".",
        output_dir=".",
        services=services,
    )


class EchoRequest(BaseModel):
    text: str


class EchoResponse(BaseModel):
    text: str


@capability(
    id="cov.echo@1.0.0",
    description="Coverage echo.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(request={"text": "hi"}, response={"text": "hi"}),),
)
def cov_echo(request: EchoRequest, ctx: ToolContext) -> CapabilityResult[EchoResponse]:
    _ = ctx
    return CapabilityResult.ok(data=EchoResponse(text=request.text))


def test_registry_resolve_provenance_and_global() -> None:
    v1 = bound_capability_of(cov_echo)
    registry = CapabilityRegistry()
    registry.register(v1)
    assert registry.resolve("cov.echo") is v1
    assert registry.resolve("cov.echo", version="1.0.0") is v1
    assert registry.resolve("missing") is None
    assert registry.get("cov.echo") is v1
    ident = v1.definition.id
    assert registry.resolve_compatible(ident) is v1
    assert registry.provenance_of("cov.echo@1.0.0") is not None
    with pytest.raises(CapabilityRegistryError):
        registry.get("no.such@1.0.0")
    with pytest.raises(CapabilityRegistryError):
        registry.get("totally.missing")

    reset_capability_registry()
    global_reg = get_capability_registry()
    global_reg.register(v1)
    assert get_capability_registry().get("cov.echo@1.0.0") is v1
    reset_capability_registry()


def test_registry_entry_points() -> None:
    class EP:
        name = "cov_echo"

        def load(self) -> object:
            return cov_echo

    class EPs:
        def select(self, group: str) -> list[EP]:
            _ = group
            return [EP()]

    registry = CapabilityRegistry()
    with patch("zeo_core.tools.registry.entry_points", return_value=EPs()):
        loaded = registry.load_entry_points()
    assert loaded == ["cov.echo@1.0.0"]

    class BadEP:
        name = "bad"

        def load(self) -> object:
            return object()

    class BadEPs:
        def select(self, group: str) -> list[BadEP]:
            _ = group
            return [BadEP()]

    with (
        patch("zeo_core.tools.registry.entry_points", return_value=BadEPs()),
        pytest.raises(CapabilityRegistryError),
    ):
        CapabilityRegistry().load_entry_points()


def test_github_and_pandoc_and_checksum_paths() -> None:
    class Gh:
        def get_repository_file_content(
            self, repo: str, path: str, ref: str | None
        ) -> tuple[str, str]:
            return ("hello", "abc")

    cap = bound_capability_of(github_file_read)
    ok = invoke_sync(
        cap,
        GithubFileReadRequest(repo="o/r", path="a.txt"),
        _ctx(github=Gh()),
    )
    assert ok.data is not None
    assert ok.data.content == "hello"

    class Boom:
        def get_repository_file_content(
            self, repo: str, path: str, ref: str | None
        ) -> tuple[str, str]:
            raise RuntimeError("net")

    failed = invoke_sync(
        cap,
        GithubFileReadRequest(repo="o/r", path="a.txt"),
        _ctx(github=Boom()),
    )
    assert failed.outcome == CapabilityOutcome.integration_failure

    class FsBare:
        pass

    checksum = invoke_sync(
        bound_capability_of(file_checksum),
        FileChecksumRequest(path="a.txt"),
        _ctx(fs=FsBare()),
    )
    assert checksum.outcome == CapabilityOutcome.unavailable

    class Pandoc:
        def markdown_to_docx(self, src: str, dest: str) -> object:
            class Result:
                success = True
                content = type("C", (), {"output_size": 12})()
                error = None

            return Result()

    sink = RecordingArtifactSink()
    converted = invoke_sync(
        bound_capability_of(markdown_to_docx),
        PandocDocxRequest(markdown_path="a.md", output_path="a.docx"),
        _ctx(pandoc=Pandoc(), **{SERVICE_ARTIFACTS: sink}),
    )
    assert converted.status.value == "success"
    assert sink.refs

    class CalNoCreate:
        pass

    missing_create = invoke_sync(
        bound_capability_of(calendar_create),
        CalendarCreateRequest.model_validate(
            {
                "calendar_id": "primary",
                "summary": "A",
                "start": {"dateTime": "2026-01-01T09:00:00Z"},
                "end": {"dateTime": "2026-01-01T09:15:00Z"},
            }
        ),
        _ctx(**{"google.calendar": CalNoCreate()}),
    )
    assert missing_create.outcome == CapabilityOutcome.unavailable


def test_invoke_helpers_and_context_accessors() -> None:
    cap = bound_capability_of(cov_echo)
    ctx = _ctx()
    assert ctx.get_clock() is None
    assert ctx.get_cancellation() is None
    assert ctx.get_artifact_sink() is None
    sync_via_protocol = cap.invoke(EchoRequest(text="z"), ctx)
    assert isinstance(sync_via_protocol, CapabilityResult)
    assert sync_via_protocol.data is not None

    class Other(BaseModel):
        n: int

    rejected = invoke_sync(cap, Other(n=1), ctx)
    assert rejected.outcome == CapabilityOutcome.guard_rejected

    async_result = asyncio.run(invoke_async(cap, EchoRequest(text="a"), ctx))
    assert async_result.data is not None

    class Flip:
        def __init__(self) -> None:
            self.n = 0

        def is_cancelled(self) -> bool:
            self.n += 1
            return self.n > 1

        def deadline(self) -> datetime | None:
            return None

    cancelled_after = invoke_sync(
        cap, EchoRequest(text="a"), _ctx(**{"cancellation": Flip()})
    )
    assert cancelled_after.outcome == CapabilityOutcome.cancelled


def test_authoring_errors_and_register_to() -> None:
    registry = CapabilityRegistry()

    @capability(
        id="cov.reg@1.0.0",
        description="Register to instance.",
        effects={EffectKind.READ},
        examples=(CapabilityExample(request={"text": "hi"}, response={"text": "hi"}),),
        register_to=registry,
    )
    def registered(
        request: EchoRequest, ctx: ToolContext
    ) -> CapabilityResult[EchoResponse]:
        return CapabilityResult.ok(data=EchoResponse(text=request.text))

    assert registry.get("cov.reg@1.0.0").definition.id.name == "reg"

    with pytest.raises(CapabilityAuthoringError):
        bound_capability_of(lambda: None)

    with pytest.raises(CapabilityAuthoringError):

        @capability(
            id="cov.ctx@1.0.0",
            description="Bad ctx.",
            effects={EffectKind.READ},
            examples=(
                CapabilityExample(request={"text": "x"}, response={"text": "x"}),
            ),
            register_to=object(),
        )
        def bad_reg(
            request: EchoRequest, ctx: ToolContext
        ) -> CapabilityResult[EchoResponse]:
            return CapabilityResult.ok(data=EchoResponse(text="x"))


def test_class_adapter_errors_and_openai_refusal() -> None:
    class NoExamples(BaseZeoTool):
        name = "none"
        capability_description = "Has description."

        def run(
            self, request: EchoRequest, ctx: ToolContext
        ) -> CapabilityResult[EchoResponse]:
            return CapabilityResult.ok(data=EchoResponse(text=request.text))

    with pytest.raises(ToolAdapterError):
        tool_to_capability(NoExamples())

    cap = bound_capability_of(add)
    manifest = CapabilityManifest.from_definition(cap.definition)
    named = manifest.model_copy(update={"projection_name": "custom_add"})
    assert openai_function_name(named) == "custom_add"
    illegal = manifest.model_copy(update={"projection_name": "bad.name"})
    refused = project_openai_tool(illegal)
    assert not refused.ok
    typed = manifest.model_copy(
        update={
            "request_schema": {
                "type": "object",
                "properties": {"x": {"type": "foobar"}},
            }
        }
    )
    assert not project_openai_tool(typed).ok
    nested_list = manifest.model_copy(
        update={
            "request_schema": {
                "type": "object",
                "anyOf": [{"type": "string"}, {"type": "mystery"}],
            }
        }
    )
    assert not project_openai_tool(nested_list).ok


def test_sovereign_style_scalar_and_ctx() -> None:
    @sovereign_style_capability(
        capability_id="compat.scalar@1.0.0",
        description="Scalar wrap.",
        effects=(EffectKind.READ,),
        examples=(CapabilityExample(request={"n": 1}, response={"value": 1}),),
    )
    def scalar(n: int, ctx: ToolContext) -> int:
        _ = ctx
        return n

    result = invoke_sync(scalar, scalar.request_model(n=3), _ctx())
    assert result.status.value == "success"


def test_operation_context_factory_must_return_tool_context() -> None:
    ops = OperationRegistry()
    cap = bound_capability_of(cov_echo)

    def factory(_cap: BoundCapability) -> object:
        return object()

    name = register_capability_operation(
        cap, registry=ops, context_factory=factory, name="cov.echo"
    )
    with pytest.raises(TypeError):
        asyncio.run(invoke_operation(ops.get_or_error(name), {"text": "hi"}))
