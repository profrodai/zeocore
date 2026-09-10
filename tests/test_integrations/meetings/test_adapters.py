"""Provider-bound adapter tests with real HTTP serialization and no live effects."""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from pydantic import JsonValue, ValidationError

from zeo_core.integrations.meetings.adapters import (
    CalendarRead,
    DraftCreate,
    GmailDraftClient,
    MeetingAdapters,
    SheetsRead,
)
from zeo_core.integrations.meetings.runner import (
    AdapterAmbiguousError,
    AdapterRefusalError,
)
from zeo_core.integrations.notion.upsert import (
    CitedText,
    NotionPageSnapshot,
    NotionPageUpsertRequest,
)

from .test_runner import authorization


class Reads:
    def sheets_values(self, request: SheetsRead) -> JsonValue:
        return {"values": [[2, 3, 5]]}

    def calendar_events(self, request: CalendarRead) -> JsonValue:
        return []


class Gmail:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.raw = ""
        self.mode = "normal"

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/profile"):
            return httpx.Response(
                200,
                json={
                    "emailAddress": "other@example.com"
                    if self.mode == "wrong-account"
                    else "author@example.com"
                },
            )
        if path.endswith("/drafts") and request.method == "POST":
            self.raw = json.loads(request.content)["message"]["raw"]
            if self.mode == "timeout":
                raise httpx.ReadTimeout("SECRET-CANARY")
            return httpx.Response(
                200,
                json={
                    "id": "bad/id" if self.mode == "bad-create-id" else "draft-fixture"
                },
            )
        if path.endswith("/drafts"):
            count = {"absent": 0, "duplicate": 2}.get(self.mode, 1)
            assert request.url.params["maxResults"] == "2"
            assert request.url.params["q"].startswith("rfc822msgid:")
            return httpx.Response(
                200, json={"drafts": [{"id": "draft-fixture"}] * count}
            )
        if path.endswith("/drafts/draft-fixture"):
            value = self.raw
            if self.mode == "wrong-content":
                value = base64.urlsafe_b64encode(
                    b"Subject: changed\r\n\r\nchanged\r\n"
                ).decode()
            return httpx.Response(
                200,
                json={
                    "id": "other" if self.mode == "wrong-id" else "draft-fixture",
                    "message": {"raw": value},
                },
            )
        raise AssertionError("unapproved provider endpoint")


DRAFT: dict[str, JsonValue] = {
    "mailbox": "author@example.com",
    "to": ["reader@example.com"],
    "subject": "Meeting action",
    "body": "Please review the cited action.",
}


def invoke(
    adapters: MeetingAdapters,
    operation: str,
    payload: dict[str, JsonValue],
    resource: str,
) -> tuple[str, JsonValue]:
    return adapters.prepare(authorization(payload, operation, resource), payload)()


def test_sheets_and_calendar_are_bounded_reads() -> None:
    adapters = MeetingAdapters(reads=Reads())
    assert invoke(
        adapters,
        "sheets.values.read",
        {"spreadsheet_id": "sheet", "range_a1": "Sheet1!A1:C1"},
        "sheets:sheet:Sheet1!A1:C1",
    ) == ("", {"values": [[2, 3, 5]]})
    calendar: dict[str, JsonValue] = {
        "calendar_id": "calendar",
        "time_min": "2026-09-09T00:00:00Z",
        "time_max": "2026-09-10T00:00:00Z",
        "max_results": 10,
    }
    assert invoke(adapters, "calendar.events.list", calendar, "calendar:calendar") == (
        "",
        [],
    )
    with pytest.raises(AdapterRefusalError):
        invoke(adapters, "calendar.events.list", calendar, "calendar:other")
    with pytest.raises(AdapterRefusalError):
        invoke(MeetingAdapters(), "calendar.events.list", calendar, "calendar:calendar")
    for end in ("2026-09-09T00:00:00Z", "2026-11-09T00:00:00Z"):
        with pytest.raises(ValidationError):
            CalendarRead.model_validate({**calendar, "time_max": end})
    with pytest.raises(ValidationError):
        DraftCreate.model_validate({**DRAFT, "subject": "bad\nBcc: other@example.com"})
    with pytest.raises(ValidationError):
        DraftCreate.model_validate({**DRAFT, "to": ["reader@example.com"] * 2})


def test_gmail_draft_create_get_and_read_only_reconcile() -> None:
    boundary = Gmail()
    with httpx.Client(transport=httpx.MockTransport(boundary.handle)) as client:
        adapters = MeetingAdapters(gmail=GmailDraftClient(client))
        created = invoke(
            adapters, "gmail.draft.create", DRAFT, "gmail:author@example.com:drafts"
        )
        assert created[0] == "draft-fixture"
        fetched = invoke(
            adapters,
            "gmail.draft.get",
            {"mailbox": "author@example.com", "draft_id": "draft-fixture"},
            "gmail:author@example.com:draft:draft-fixture",
        )
        assert fetched[0] == created[0]
        reconciled = invoke(
            adapters,
            "gmail.draft.reconcile",
            {**DRAFT, "creation_idempotency_key": "once-fixture"},
            "gmail:author@example.com:drafts",
        )
        assert reconciled == created
        assert sum(method == "POST" for method, path in boundary.calls) == 1
        assert all("send" not in path for method, path in boundary.calls)
        for mode in ("absent", "duplicate", "wrong-id", "wrong-content"):
            boundary.mode = mode
            with pytest.raises(AdapterAmbiguousError):
                invoke(
                    adapters,
                    "gmail.draft.reconcile",
                    {**DRAFT, "creation_idempotency_key": "once-fixture"},
                    "gmail:author@example.com:drafts",
                )
        assert sum(method == "POST" for method, path in boundary.calls) == 1


@pytest.mark.parametrize(
    "mode,error",
    [
        ("wrong-account", AdapterRefusalError),
        ("bad-create-id", AdapterAmbiguousError),
        ("wrong-id", AdapterAmbiguousError),
        ("wrong-content", AdapterAmbiguousError),
        ("timeout", httpx.ReadTimeout),
    ],
)
def test_gmail_identity_and_ambiguity(mode: str, error: type[Exception]) -> None:
    boundary = Gmail()
    boundary.mode = mode
    with httpx.Client(transport=httpx.MockTransport(boundary.handle)) as client:
        adapters = MeetingAdapters(gmail=GmailDraftClient(client))
        with pytest.raises(error):
            invoke(
                adapters, "gmail.draft.create", DRAFT, "gmail:author@example.com:drafts"
            )
        assert sum(method == "POST" for method, path in boundary.calls) == (
            0 if mode == "wrong-account" else 1
        )
    with pytest.raises(AdapterRefusalError):
        invoke(
            MeetingAdapters(),
            "gmail.draft.create",
            DRAFT,
            "gmail:author@example.com:drafts",
        )


class Notion:
    def __init__(self) -> None:
        self.pages: tuple[NotionPageSnapshot, ...] = ()
        self.creates = 0
        self.replaces = 0

    def find_by_marker(self, **kwargs: object) -> tuple[NotionPageSnapshot, ...]:
        return self.pages

    def create(self, request: NotionPageUpsertRequest) -> NotionPageSnapshot:
        self.creates += 1
        page = NotionPageSnapshot(
            page_id="a" * 32,
            title=request.title,
            idempotency_marker=request.idempotency_marker,
            markdown=request.canonical_markdown(),
        )
        self.pages = (page,)
        return page

    def replace_content(
        self, *, page_id: str, request: NotionPageUpsertRequest
    ) -> NotionPageSnapshot:
        self.replaces += 1
        return self.create(request)


def notion_payload() -> dict[str, JsonValue]:
    return NotionPageUpsertRequest(
        meeting_id="meeting_0123456789abcdef",
        meeting_artifact_sha256="b" * 64,
        interpretation_id="interpretation_0123456789abcdef",
        interpretation_sha256="c" * 64,
        destination_parent_id="d" * 32,
        title="Cited action",
        summary=CitedText(text="Summary", source_citations=("span:0:10",)),
        idempotency_marker=NotionPageUpsertRequest.marker_for(
            meeting_artifact_sha256="b" * 64, destination_parent_id="d" * 32
        ),
    ).model_dump(mode="json")


def test_notion_upsert_retains_marker_and_exact_content() -> None:
    provider = Notion()
    adapters = MeetingAdapters(notion=provider)
    payload = notion_payload()
    resource = "notion:" + "d" * 32
    first = invoke(adapters, "notion.page.upsert", payload, resource)
    assert invoke(adapters, "notion.page.upsert", payload, resource) == first
    assert provider.creates == 1
    provider.pages = (provider.pages[0].model_copy(update={"markdown": "old"}),)
    assert invoke(adapters, "notion.page.upsert", payload, resource) == first
    assert provider.replaces == 1
    provider.pages *= 2
    with pytest.raises(AdapterRefusalError):
        invoke(adapters, "notion.page.upsert", payload, resource)
    provider.pages = (provider.pages[0].model_copy(update={"title": "conflict"}),)
    with pytest.raises(AdapterRefusalError):
        invoke(adapters, "notion.page.upsert", payload, resource)
    with pytest.raises(AdapterRefusalError):
        invoke(MeetingAdapters(), "notion.page.upsert", payload, resource)


def test_google_service_calls_and_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import Mock

    from zeo_core.integrations.core import IntegrationResult
    from zeo_core.integrations.google.calendar import GoogleCalendarService
    from zeo_core.integrations.google.sheets import GoogleSheetsService
    from zeo_core.integrations.meetings import GoogleMeetingReads

    sheets = GoogleSheetsService()
    calendar = GoogleCalendarService()
    reads = GoogleMeetingReads(sheets=sheets, calendar=calendar)
    assert sheets.auth_provider is None and calendar.auth_provider is None
    values = Mock(return_value=IntegrationResult.success_result(content={"values": []}))
    events = Mock(return_value=IntegrationResult.success_result(content=[]))
    monkeypatch.setattr(sheets, "get_values", values)
    monkeypatch.setattr(calendar, "list_events", events)
    selected = SheetsRead(spreadsheet_id="sheet", range_a1="A1:C1")
    window = CalendarRead.model_validate(
        {
            "calendar_id": "calendar",
            "time_min": "2026-09-09T00:00:00Z",
            "time_max": "2026-09-10T00:00:00Z",
            "max_results": 1,
        }
    )
    assert reads.sheets_values(selected) == {"values": []}
    values.assert_called_once_with("sheet", "A1:C1")
    assert reads.calendar_events(window) == []
    events.assert_called_once_with(
        calendar_id="calendar",
        time_min="2026-09-09T00:00:00+00:00",
        time_max="2026-09-10T00:00:00+00:00",
        max_results=1,
    )
    values.return_value = IntegrationResult.error_result("unavailable")
    events.return_value = IntegrationResult.error_result("unavailable")
    with pytest.raises(AdapterRefusalError):
        reads.sheets_values(selected)
    with pytest.raises(AdapterRefusalError):
        reads.calendar_events(window)
    events.return_value = IntegrationResult.success_result(content=[None, None])
    with pytest.raises(AdapterRefusalError):
        reads.calendar_events(window)
    with pytest.raises(TypeError):
        GoogleMeetingReads(sheets=object(), calendar=calendar)


@pytest.mark.parametrize(
    "mode", ["redirect", "server", "large", "candidate", "content"]
)
def test_gmail_refuses_unbounded_or_malformed_response(mode: str) -> None:
    from zeo_core.integrations.meetings.adapters import DraftGet, DraftReconcile

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json={"emailAddress": "author@example.com"})
        if mode == "redirect":
            return httpx.Response(302, headers={"location": "https://example.com"})
        if mode == "server":
            return httpx.Response(500)
        if mode == "large":
            return httpx.Response(200, content=b"x" * (1024 * 1024 + 1))
        if mode == "candidate":
            return httpx.Response(200, json={"drafts": ["bad"]})
        return httpx.Response(200, json={"id": "draft-fixture", "message": {}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        gmail = GmailDraftClient(client)
        with pytest.raises(AdapterAmbiguousError):
            if mode == "candidate":
                gmail.reconcile(
                    DraftReconcile.model_validate(
                        {**DRAFT, "creation_idempotency_key": "once"}
                    )
                )
            else:
                gmail.get(
                    DraftGet(mailbox="author@example.com", draft_id="draft-fixture")
                )


def test_notion_read_failure_and_changed_page_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import Mock

    provider = Notion()
    payload = notion_payload()
    adapters = MeetingAdapters(notion=provider)
    resource = "notion:" + "d" * 32
    invoke(adapters, "notion.page.upsert", payload, resource)
    original = provider.pages[0]
    provider.pages = (original.model_copy(update={"markdown": "outdated"}),)
    monkeypatch.setattr(
        provider,
        "replace_content",
        Mock(return_value=original.model_copy(update={"page_id": "e" * 32})),
    )
    with pytest.raises(AdapterAmbiguousError):
        invoke(adapters, "notion.page.upsert", payload, resource)
    monkeypatch.setattr(
        provider, "find_by_marker", Mock(side_effect=RuntimeError("unavailable"))
    )
    with pytest.raises(AdapterRefusalError):
        invoke(adapters, "notion.page.upsert", payload, resource)


@pytest.mark.parametrize(
    "range_a1", ["A:A", "1:2", "A0:B4", "C1:A2", "A3:B1", "A1:Z1000", "named-range"]
)
def test_sheets_requires_a_finite_bounded_rectangle(range_a1: str) -> None:
    with pytest.raises(ValidationError):
        SheetsRead(spreadsheet_id="sheet", range_a1=range_a1)


def test_sheets_cell_and_exact_bound() -> None:
    assert SheetsRead(spreadsheet_id="sheet", range_a1="'Team data'!A1").range_a1
    assert SheetsRead(spreadsheet_id="sheet", range_a1="A1:J1000").range_a1
