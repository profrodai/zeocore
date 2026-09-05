"""Admitted, reconcilable ``notion.page.upsert`` business operation."""

from __future__ import annotations

import hashlib
import json
import string
from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zeo_core.connections.orchestration import (
    DispatchDisposition,
    EffectDispatchRequest,
    EffectDispatchResult,
    ReconciliationDisposition,
    ReconciliationResult,
)
from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections import (
    BusinessOperation,
    ConnectorId,
    ConnectorRevision,
    ConnectorRevisionId,
    IdempotencyMode,
    NormalizedError,
    NormalizedErrorCode,
    OperationId,
    RiskClass,
)

from .client import NotionClient, NotionOperation

NOTION_PAGE_UPSERT_OPERATION_ID = OperationId(value="notion.page.upsert")
NOTION_PAGE_UPSERT_REVISION_ID = ConnectorRevisionId(value="notion.page-upsert@1")
_MARKER_PREFIX = "zeo-notion-upsert:v1:"
_TITLE_PROPERTY = "Name"
_MARKER_PROPERTY = "ZEO Idempotency"
_HEX_SHA256 = r"^[0-9a-f]{64}$"
_NOTION_ID = r"^[0-9A-Fa-f-]{32,36}$"


class CitedText(BaseModel):
    """One interpreted statement with durable source-span citations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(..., min_length=1, max_length=20_000)
    source_citations: tuple[str, ...] = Field(..., min_length=1, max_length=100)

    @field_validator("source_citations")
    @classmethod
    def _citations_are_bounded_and_nonempty(
        cls, citations: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not item.strip() or len(item) > 500 for item in citations):
            raise ValueError("source citations must be non-empty and at most 500 chars")
        return citations


class NotionPageUpsertRequest(BaseModel):
    """Closed business request authorized before any Notion call is made."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meeting_id: str = Field(..., min_length=1, max_length=200)
    meeting_artifact_sha256: str = Field(..., pattern=_HEX_SHA256)
    interpretation_id: str = Field(..., min_length=1, max_length=200)
    interpretation_sha256: str = Field(..., pattern=_HEX_SHA256)
    destination_parent_id: str = Field(..., pattern=_NOTION_ID)
    title: str = Field(..., min_length=1, max_length=200)
    summary: CitedText
    decisions: tuple[CitedText, ...] = Field(default_factory=tuple, max_length=200)
    actions: tuple[CitedText, ...] = Field(default_factory=tuple, max_length=200)
    open_questions: tuple[CitedText, ...] = Field(default_factory=tuple, max_length=200)
    full_transcript: str | None = Field(default=None, max_length=400_000)
    idempotency_marker: str = Field(..., pattern=rf"^{_MARKER_PREFIX}[0-9a-f]{{64}}$")

    @field_validator("destination_parent_id")
    @classmethod
    def _destination_is_a_notion_id(cls, value: str) -> str:
        if not _is_notion_id(value):
            raise ValueError("destination_parent_id must be a Notion UUID")
        return value

    @staticmethod
    def marker_for(*, meeting_artifact_sha256: str, destination_parent_id: str) -> str:
        bound = f"{meeting_artifact_sha256}\n{destination_parent_id}".encode()
        return _MARKER_PREFIX + hashlib.sha256(bound).hexdigest()

    @model_validator(mode="after")
    def _marker_binds_artifact_and_destination(self) -> NotionPageUpsertRequest:
        expected = self.marker_for(
            meeting_artifact_sha256=self.meeting_artifact_sha256,
            destination_parent_id=self.destination_parent_id,
        )
        if self.idempotency_marker != expected:
            raise ValueError(
                "idempotency_marker must bind meeting artifact and destination"
            )
        return self

    def canonical_markdown(self) -> str:
        sections = [
            f"# {self.title}",
            f"<!-- {self.idempotency_marker} -->",
            "## Summary",
            _render_cited(self.summary),
            _render_group("Decisions", self.decisions),
            _render_group("Actions", self.actions),
            _render_group("Open questions", self.open_questions),
        ]
        if self.full_transcript is not None:
            sections.extend(("## Full transcript", self.full_transcript))
        return "\n\n".join(item for item in sections if item) + "\n"


class NotionPageSnapshot(BaseModel):
    """Bounded read-back used for direct confirmation and reconciliation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    page_id: str = Field(..., pattern=_NOTION_ID)
    title: str = Field(..., min_length=1, max_length=200)
    idempotency_marker: str = Field(..., min_length=1, max_length=128)
    markdown: str = Field(..., max_length=500_000)

    @field_validator("page_id")
    @classmethod
    def _page_is_a_notion_id(cls, value: str) -> str:
        if not _is_notion_id(value):
            raise ValueError("page_id must be a Notion UUID")
        return value


class NotionPageUpsertProvider(Protocol):
    """Small provider surface; no raw endpoint or credential is caller-controlled."""

    def find_by_marker(
        self, *, destination_parent_id: str, idempotency_marker: str
    ) -> tuple[NotionPageSnapshot, ...]: ...

    def create(self, request: NotionPageUpsertRequest) -> NotionPageSnapshot: ...

    def replace_content(
        self, *, page_id: str, request: NotionPageUpsertRequest
    ) -> NotionPageSnapshot: ...


class NotionClientPageUpsertProvider:
    """Current Notion API implementation of the narrow upsert surface."""

    def __init__(self, client: NotionClient) -> None:
        self._client = client

    def find_by_marker(
        self, *, destination_parent_id: str, idempotency_marker: str
    ) -> tuple[NotionPageSnapshot, ...]:
        pages, _ = self._client.query_data_source(
            destination_parent_id,
            filter={
                "property": _MARKER_PROPERTY,
                "rich_text": {"equals": idempotency_marker},
            },
            page_size=100,
        )
        return tuple(self._snapshot(page.id) for page in pages)

    def create(self, request: NotionPageUpsertRequest) -> NotionPageSnapshot:
        created = self._client.execute(
            NotionOperation.PAGE_CREATE,
            parent={
                "type": "data_source_id",
                "data_source_id": request.destination_parent_id,
            },
            properties={
                _TITLE_PROPERTY: _rich_text("title", request.title),
                _MARKER_PROPERTY: _rich_text("rich_text", request.idempotency_marker),
            },
            markdown=request.canonical_markdown(),
        )
        page_id = created.get("id")
        if not isinstance(page_id, str):
            raise RuntimeError("Notion create omitted the page identifier")
        return self._snapshot(page_id)

    def replace_content(
        self, *, page_id: str, request: NotionPageUpsertRequest
    ) -> NotionPageSnapshot:
        self._client.execute(
            NotionOperation.PAGE_UPDATE_MARKDOWN,
            page_id=page_id,
            type="replace_content",
            replace_content={"new_str": request.canonical_markdown()},
        )
        return self._snapshot(page_id)

    def _snapshot(self, page_id: str) -> NotionPageSnapshot:
        page = self._client.get_page(page_id)
        markdown = self._client.execute(
            NotionOperation.PAGE_RETRIEVE_MARKDOWN, page_id=page_id
        ).get("markdown")
        if not isinstance(markdown, str):
            raise RuntimeError("Notion read-back omitted markdown")
        return NotionPageSnapshot(
            page_id=page.id,
            title=_property_text(page.properties.get(_TITLE_PROPERTY), "title"),
            idempotency_marker=_property_text(
                page.properties.get(_MARKER_PROPERTY), "rich_text"
            ),
            markdown=markdown,
        )


class NotionPageUpsertDispatcher:
    """Credential-scoped callable for ``KeychainEffectDispatcher``."""

    def __init__(
        self,
        provider_factory: Callable[[str], NotionPageUpsertProvider] | None = None,
    ) -> None:
        self._provider_factory = provider_factory or _default_provider

    def __call__(
        self, material: str, dispatch: EffectDispatchRequest
    ) -> EffectDispatchResult:
        request = _parse_request(dispatch)
        if request is None:
            return _failed_safe("Notion upsert request failed semantic validation")
        provider = self._provider_factory(material)
        try:
            matches = provider.find_by_marker(
                destination_parent_id=request.destination_parent_id,
                idempotency_marker=request.idempotency_marker,
            )
        except Exception:
            return _failed_safe("Notion destination could not be inspected")
        if len(matches) > 1:
            return _failed_safe("Notion idempotency marker is not unique")
        try:
            if not matches:
                observed = provider.create(request)
            elif _matches(matches[0], request):
                observed = matches[0]
            elif matches[0].title != request.title:
                return _failed_safe("Notion upsert title conflicts with existing page")
            else:
                observed = provider.replace_content(
                    page_id=matches[0].page_id, request=request
                )
        except Exception:
            raise RuntimeError(
                "Notion upsert outcome requires reconciliation"
            ) from None
        if not _matches(observed, request):
            raise RuntimeError("Notion upsert read-back requires reconciliation")
        return EffectDispatchResult(
            disposition=DispatchDisposition.CONFIRMED,
            confirmation_digest=_confirmation_digest(observed, dispatch),
        )


class NotionPageUpsertReconciler:
    """Read-only marker lookup; it never creates or updates a page."""

    def __init__(
        self,
        provider_factory: Callable[[str], NotionPageUpsertProvider] | None = None,
    ) -> None:
        self._provider_factory = provider_factory or _default_provider

    def __call__(
        self, material: str, dispatch: EffectDispatchRequest
    ) -> ReconciliationResult:
        request = _parse_request(dispatch)
        if request is None:
            return _unresolved("invalid-request", ())
        try:
            matches = self._provider_factory(material).find_by_marker(
                destination_parent_id=request.destination_parent_id,
                idempotency_marker=request.idempotency_marker,
            )
        except Exception:
            return _unresolved("provider-unavailable", ())
        if len(matches) == 1 and _matches(matches[0], request):
            return ReconciliationResult(
                disposition=ReconciliationDisposition.CONFIRMED,
                evidence_digest=_reconciliation_digest("confirmed", matches),
                confirmation_digest=_confirmation_digest(matches[0], dispatch),
            )
        status = "absent" if not matches else "conflict"
        return _unresolved(status, matches)


def notion_page_upsert_revision() -> ConnectorRevision:
    """Immutable admitted connector revision for the business operation."""

    return ConnectorRevision(
        connector_id=ConnectorId(value="notion"),
        revision_id=NOTION_PAGE_UPSERT_REVISION_ID,
        provider="notion",
        authentication_profile="oauth-or-internal-token",
        permitted_upstream_origins=("https://api.notion.com",),
        external_account_identity_probe="user.me",
        health_probe="user.me",
        operations=(
            BusinessOperation(
                operation_id=NOTION_PAGE_UPSERT_OPERATION_ID,
                effect=EffectKind.WRITE,
                request_schema=NotionPageUpsertRequest.model_json_schema(),
                response_schema={
                    "type": "object",
                    "properties": {
                        "confirmation_digest": {"type": "string"},
                    },
                    "required": ["confirmation_digest"],
                    "additionalProperties": False,
                },
                allowed_origin="https://api.notion.com",
                method="POST",
                path_template="/v1/pages",
                secret_bindings=("notion-access-token",),
                redaction_paths=("authorization", "provider_response"),
                idempotency_mode=IdempotencyMode.KERNEL_MANAGED,
                reconciliation_strategy="query_marker_then_verify_markdown",
            ),
        ),
        request_size_limit_bytes=500_000,
        response_size_limit_bytes=500_000,
        timeout_seconds=60.0,
        credential_injection_point="authorization-header",
        redaction_policy="drop-provider-payload-keep-digests",
        risk_class=RiskClass.HIGH,
        reconciliation_method="query_marker_then_verify_markdown",
        provider_error_mapping_version="notion-2026-03-11-v1",
        conformance_fixture_ids=("notion-page-upsert-v1",),
    )


def _default_provider(material: str) -> NotionPageUpsertProvider:
    # Mutation retries belong to the durable orchestrator. An SDK retry of
    # POST /pages after a lost response could duplicate the effect before
    # marker reconciliation observes the first attempt.
    return NotionClientPageUpsertProvider(NotionClient(material, max_retries=0))


def _parse_request(
    dispatch: EffectDispatchRequest,
) -> NotionPageUpsertRequest | None:
    if dispatch.operation_id != NOTION_PAGE_UPSERT_OPERATION_ID:
        return None
    try:
        return NotionPageUpsertRequest.model_validate_json(dispatch.request_body)
    except Exception:
        return None


def _failed_safe(message: str) -> EffectDispatchResult:
    return EffectDispatchResult(
        disposition=DispatchDisposition.FAILED_SAFE,
        normalized_error=NormalizedError(
            code=NormalizedErrorCode.REQUEST_REFUSED,
            message=message,
        ),
    )


def _unresolved(
    status: str, matches: tuple[NotionPageSnapshot, ...]
) -> ReconciliationResult:
    return ReconciliationResult(
        disposition=ReconciliationDisposition.UNRESOLVED,
        evidence_digest=_reconciliation_digest(status, matches),
    )


def _matches(snapshot: NotionPageSnapshot, request: NotionPageUpsertRequest) -> bool:
    return (
        snapshot.title == request.title
        and snapshot.idempotency_marker == request.idempotency_marker
        and snapshot.markdown == request.canonical_markdown()
    )


def _confirmation_digest(
    snapshot: NotionPageSnapshot, dispatch: EffectDispatchRequest
) -> str:
    evidence = {
        "page_id": snapshot.page_id,
        "request_digest": dispatch.request_digest,
        "content_sha256": hashlib.sha256(snapshot.markdown.encode()).hexdigest(),
    }
    return hashlib.sha256(_canonical_json(evidence)).hexdigest()


def _reconciliation_digest(status: str, matches: tuple[NotionPageSnapshot, ...]) -> str:
    evidence = {"status": status, "page_ids": sorted(item.page_id for item in matches)}
    return hashlib.sha256(_canonical_json(evidence)).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _is_notion_id(value: str) -> bool:
    compact = value.replace("-", "")
    return len(compact) == 32 and all(char in string.hexdigits for char in compact)


def _rich_text(kind: str, value: str) -> dict[str, object]:
    return {kind: [{"type": "text", "text": {"content": value}}]}


def _property_text(value: object, kind: str) -> str:
    if not isinstance(value, dict):
        return ""
    parts = value.get(kind)
    if not isinstance(parts, list):
        return ""
    return "".join(
        str(item.get("plain_text", "")) for item in parts if isinstance(item, dict)
    )


def _render_cited(item: CitedText) -> str:
    citations = ", ".join(f"`{citation}`" for citation in item.source_citations)
    return f"{item.text}\n\nSources: {citations}"


def _render_group(title: str, items: tuple[CitedText, ...]) -> str:
    if not items:
        return f"## {title}\n\nNone recorded."
    rendered = "\n\n".join(f"- {_render_cited(item)}" for item in items)
    return f"## {title}\n\n{rendered}"


__all__ = [
    "CitedText",
    "NOTION_PAGE_UPSERT_OPERATION_ID",
    "NOTION_PAGE_UPSERT_REVISION_ID",
    "NotionClientPageUpsertProvider",
    "NotionPageSnapshot",
    "NotionPageUpsertDispatcher",
    "NotionPageUpsertProvider",
    "NotionPageUpsertReconciler",
    "NotionPageUpsertRequest",
    "notion_page_upsert_revision",
]
