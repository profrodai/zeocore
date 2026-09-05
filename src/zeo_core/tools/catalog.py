"""Representative in-tree capabilities (integrations remain leaves)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from zeo_core.contracts import (
    ArtifactKind,
    ArtifactRef,
    CapabilityExample,
    CapabilityRequirements,
    CapabilityResult,
    ConcurrencyMode,
    EffectKind,
    FilesystemRequirement,
    GuardIssue,
    GuardResult,
    NetworkRequirement,
    StorageRef,
    StorageScheme,
)
from zeo_core.tools.authoring import bound_capability_of, capability
from zeo_core.tools.context import ToolContext
from zeo_core.tools.services import SERVICE_ARTIFACTS, RecordingArtifactSink


class AddRequest(BaseModel):
    left: str
    right: str


class AddResponse(BaseModel):
    sum: str


class IncompatibleAddGuard:
    def check(self, request: BaseModel) -> GuardResult:
        if not isinstance(request, AddRequest):
            return GuardResult.reject("unexpected request type")
        if request.left == "incompatible" and request.right == "pair":
            return GuardResult.reject(
                "left and right are mutually incompatible",
                issues=(GuardIssue(path="left", message="conflicts with right"),),
            )
        return GuardResult.accept()


@capability(
    id="math.add@1.0.0",
    description="Add two decimal numbers as strings.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="simple",
            request={"left": "1.5", "right": "2.5"},
            response={"sum": "4.0"},
        ),
    ),
    error_codes=frozenset({"ZEO_CAP_GUARD_REJECTED"}),
    guards=(IncompatibleAddGuard(),),
)
def add(request: AddRequest, ctx: ToolContext) -> CapabilityResult[AddResponse]:
    _ = ctx
    try:
        total = float(request.left) + float(request.right)
    except ValueError as exc:
        return CapabilityResult.fail(
            msg="Operands are not decimal numbers",
            code="ZEO_VAL_INVALID",
            exception=exc,
        )
    return CapabilityResult.ok(data=AddResponse(sum=format(total, "g")))


class FileChecksumRequest(BaseModel):
    path: str


class FileChecksumResponse(BaseModel):
    path: str
    sha256: str


@capability(
    id="fs.file.checksum@1.0.0",
    description="SHA-256 checksum via the runner filesystem service.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="readme",
            request={"path": "README.md"},
            response={"path": "README.md", "sha256": "abc"},
        ),
    ),
    requirements=CapabilityRequirements(
        filesystem=FilesystemRequirement(read=True, roles=("path",)),
    ),
)
def file_checksum(
    request: FileChecksumRequest, ctx: ToolContext
) -> CapabilityResult[FileChecksumResponse]:
    fs = ctx.require_fs()
    hasher = getattr(fs, "hash_file", None)
    if hasher is None:
        return CapabilityResult.unavailable("Filesystem service cannot hash files")
    result = hasher(request.path, "sha256")
    success = getattr(result, "success", getattr(result, "ok", False))
    data = getattr(result, "data", getattr(result, "value", None))
    if not success or not isinstance(data, str):
        return CapabilityResult.fail(
            msg=getattr(result, "error", None) and str(result.error) or "hash failed",
            code="ZEO_IO_ERROR",
        )
    return CapabilityResult.ok(
        data=FileChecksumResponse(path=request.path, sha256=data)
    )


class GithubFileReadRequest(BaseModel):
    repo: str
    path: str
    ref: str | None = None


class GithubFileReadResponse(BaseModel):
    repo: str
    path: str
    content: str
    sha: str


@capability(
    id="github.repository.file.read@1.1.0",
    description="Read a file from a GitHub repository (read-only API).",
    effects={EffectKind.READ, EffectKind.EXTERNAL_COMMUNICATION},
    examples=(
        CapabilityExample(
            name="readme",
            request={"repo": "profrodai/zeocore", "path": "README.md"},
            response={
                "repo": "profrodai/zeocore",
                "path": "README.md",
                "content": "#",
                "sha": "0",
            },
        ),
    ),
    requirements=CapabilityRequirements(
        services=frozenset({"github"}),
        credentials=frozenset({"github_token"}),
        network=NetworkRequirement(required=True, hosts=frozenset({"api.github.com"})),
    ),
)
def github_file_read(
    request: GithubFileReadRequest, ctx: ToolContext
) -> CapabilityResult[GithubFileReadResponse]:
    service = ctx.get_service("github")
    if service is None:
        return CapabilityResult.unavailable("github service was not supplied")
    reader = getattr(service, "get_repository_file_content", None)
    client = getattr(service, "client", None)
    if reader is None and client is not None:
        reader = getattr(client, "get_repository_file_content", None)
    if reader is None:
        return CapabilityResult.unavailable("github service cannot read files")
    try:
        content, sha = reader(request.repo, request.path, request.ref)
    except Exception as exc:  # noqa: BLE001
        return CapabilityResult.fail(
            msg=str(exc),
            code="ZEO_NET_ERROR",
            exception=exc,
        )
    return CapabilityResult.ok(
        data=GithubFileReadResponse(
            repo=request.repo, path=request.path, content=content, sha=sha
        )
    )


class CalendarEventTime(BaseModel):
    date_time: str | None = Field(default=None, alias="dateTime")
    date: str | None = None
    time_zone: str | None = Field(default=None, alias="timeZone")

    model_config = {"populate_by_name": True}


class CalendarCreateRequest(BaseModel):
    calendar_id: str
    summary: str
    start: CalendarEventTime
    end: CalendarEventTime
    description: str | None = None


class CalendarCreateResponse(BaseModel):
    event_id: str
    summary: str
    html_link: str | None = None


@capability(
    id="google.calendar.event.create@1.0.0",
    description="Create a Google Calendar event.",
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    concurrency=ConcurrencyMode.SERIAL_PER_RESOURCE,
    resource_key_fields=("calendar_id",),
    examples=(
        CapabilityExample(
            name="standup",
            request={
                "calendar_id": "primary",
                "summary": "Standup",
                "start": {"dateTime": "2026-01-01T09:00:00Z"},
                "end": {"dateTime": "2026-01-01T09:15:00Z"},
            },
            response={"event_id": "abc", "summary": "Standup", "html_link": None},
        ),
    ),
    requirements=CapabilityRequirements(
        services=frozenset({"google.calendar"}),
        credentials=frozenset({"google_oauth"}),
        network=NetworkRequirement(
            required=True, hosts=frozenset({"www.googleapis.com"})
        ),
    ),
)
def calendar_create(
    request: CalendarCreateRequest, ctx: ToolContext
) -> CapabilityResult[CalendarCreateResponse]:
    service = ctx.get_service("google.calendar")
    if service is None:
        return CapabilityResult.unavailable("google.calendar service was not supplied")
    create = getattr(service, "create_event", None)
    if create is None:
        return CapabilityResult.unavailable("calendar service cannot create events")
    start = request.start.model_dump(by_alias=True, exclude_none=True)
    end = request.end.model_dump(by_alias=True, exclude_none=True)
    result = create(
        summary=request.summary,
        start=start,
        end=end,
        calendar_id=request.calendar_id,
        description=request.description,
    )
    success = getattr(result, "success", False)
    content = getattr(result, "content", None)
    if not success or content is None:
        return CapabilityResult.fail(
            msg=getattr(result, "error", None) or "calendar create failed",
            code="ZEO_NET_ERROR",
        )
    event_id = getattr(content, "id", None) or getattr(content, "event_id", "")
    html_link = getattr(content, "html_link", None)
    artifact_sink = ctx.get_service(SERVICE_ARTIFACTS)
    if isinstance(artifact_sink, RecordingArtifactSink):
        artifact_sink.emit(
            ArtifactRef(
                role="calendar_event",
                kind=ArtifactKind.final,
                content_type="application/json",
                storage=StorageRef(
                    scheme=StorageScheme.custom,
                    scheme_custom="calendar",
                    uri=f"calendar://{request.calendar_id}/{event_id}",
                ),
            )
        )
    return CapabilityResult.ok(
        data=CalendarCreateResponse(
            event_id=str(event_id),
            summary=request.summary,
            html_link=html_link,
        )
    )


class PandocDocxRequest(BaseModel):
    markdown_path: str
    output_path: str


class PandocDocxResponse(BaseModel):
    output_path: str
    size_bytes: int | None = None


@capability(
    id="media.document.markdown_to_docx@1.0.0",
    description="Convert markdown to DOCX via a runner-supplied pandoc service.",
    effects={EffectKind.WRITE},
    examples=(
        CapabilityExample(
            name="notes",
            request={"markdown_path": "notes.md", "output_path": "notes.docx"},
            response={"output_path": "notes.docx", "size_bytes": 12},
        ),
    ),
    requirements=CapabilityRequirements(
        services=frozenset({"pandoc"}),
        binaries=frozenset({"pandoc"}),
        filesystem=FilesystemRequirement(
            read=True, write=True, roles=("markdown_path", "output_path")
        ),
    ),
)
def markdown_to_docx(
    request: PandocDocxRequest, ctx: ToolContext
) -> CapabilityResult[PandocDocxResponse]:
    service = ctx.get_service("pandoc")
    if service is None:
        return CapabilityResult.unavailable("pandoc service was not supplied")
    convert = getattr(service, "markdown_to_docx", None)
    if convert is None:
        return CapabilityResult.unavailable("pandoc service cannot convert markdown")
    result = convert(request.markdown_path, request.output_path)
    success = getattr(result, "success", False)
    if not success:
        return CapabilityResult.fail(
            msg=getattr(result, "error", None) or "pandoc conversion failed",
            code="ZEO_IO_ERROR",
        )
    content = getattr(result, "content", None)
    size = getattr(content, "output_size", None) if content is not None else None
    sink = ctx.get_service(SERVICE_ARTIFACTS)
    if isinstance(sink, RecordingArtifactSink):
        sink.emit(
            ArtifactRef(
                role="docx",
                kind=ArtifactKind.final,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                storage=StorageRef(
                    scheme=StorageScheme.local,
                    uri=f"file://{request.output_path}",
                ),
            )
        )
    return CapabilityResult.ok(
        data=PandocDocxResponse(output_path=request.output_path, size_bytes=size)
    )


CATALOG = (
    bound_capability_of(add),
    bound_capability_of(file_checksum),
    bound_capability_of(github_file_read),
    bound_capability_of(calendar_create),
    bound_capability_of(markdown_to_docx),
)
