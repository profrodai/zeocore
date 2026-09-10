"""Six bounded meeting operations over host-supplied provider clients."""

from __future__ import annotations

import base64
import hashlib
import json
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from typing import Protocol

import httpx
from pydantic import (
    AwareDatetime,
    EmailStr,
    Field,
    JsonValue,
    TypeAdapter,
    model_validator,
)

from .contracts import ClosedModel, InvocationAuthorization
from .runner import AdapterAmbiguousError, AdapterRefusalError, PreparedOperation


class SheetsRead(ClosedModel):
    spreadsheet_id: str = Field(min_length=1, max_length=200)
    range_a1: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _finite_cells(self) -> SheetsRead:
        import re

        match = re.fullmatch(
            r"(?:[^!]+!)?([A-Z]{1,3})([1-9][0-9]{0,6})(?::([A-Z]{1,3})([1-9][0-9]{0,6}))?",
            self.range_a1,
        )
        if match is None:
            raise ValueError("Sheets range must name a finite A1 cell or rectangle")

        def column(value: str) -> int:
            result = 0
            for character in value:
                result = result * 26 + ord(character) - ord("A") + 1
            return result

        first_col, first_row, last_col, last_row = match.groups()
        width = column(last_col or first_col) - column(first_col) + 1
        height = int(last_row or first_row) - int(first_row) + 1
        if width < 1 or height < 1 or width * height > 10_000:
            raise ValueError("Sheets rectangle must contain at most 10000 cells")
        return self


class CalendarRead(ClosedModel):
    calendar_id: str = Field(min_length=1, max_length=320)
    time_min: AwareDatetime
    time_max: AwareDatetime
    max_results: int = Field(default=100, ge=1, le=250)

    @model_validator(mode="after")
    def _bounded_window(self) -> CalendarRead:
        seconds = (self.time_max - self.time_min).total_seconds()
        if not 0 < seconds <= 31 * 86400:
            raise ValueError("calendar interval must be positive and at most 31 days")
        return self


class DraftCreate(ClosedModel):
    mailbox: EmailStr
    to: tuple[EmailStr, ...] = Field(min_length=1, max_length=20)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=100_000)

    @model_validator(mode="after")
    def _headers_and_recipients(self) -> DraftCreate:
        if (
            "\r" in self.subject
            or "\n" in self.subject
            or len(self.to) != len(set(self.to))
        ):
            raise ValueError("draft headers or recipients are invalid")
        return self


class DraftGet(ClosedModel):
    mailbox: EmailStr
    draft_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,200}$")


class DraftReconcile(DraftCreate):
    creation_idempotency_key: str = Field(min_length=1, max_length=200)


class GoogleReadPort(Protocol):
    def sheets_values(self, request: SheetsRead) -> JsonValue: ...
    def calendar_events(self, request: CalendarRead) -> JsonValue: ...


class GoogleMeetingReads:
    """Existing Zeocore service methods, initialized only after runtime admission."""

    def __init__(self, *, sheets: object, calendar: object) -> None:
        from zeo_core.integrations.google.calendar import GoogleCalendarService
        from zeo_core.integrations.google.sheets import GoogleSheetsService

        if not isinstance(sheets, GoogleSheetsService) or not isinstance(
            calendar, GoogleCalendarService
        ):
            raise TypeError("expected configured Zeocore Google services")
        self._sheets = sheets
        self._calendar = calendar

    def sheets_values(self, request: SheetsRead) -> JsonValue:
        result = self._sheets.get_values(request.spreadsheet_id, request.range_a1)
        if not result.success or result.content is None:
            raise AdapterRefusalError("Sheets observation unavailable")
        return TypeAdapter(JsonValue).validate_python(result.content)

    def calendar_events(self, request: CalendarRead) -> JsonValue:
        result = self._calendar.list_events(
            calendar_id=request.calendar_id,
            time_min=request.time_min.isoformat(),
            time_max=request.time_max.isoformat(),
            max_results=request.max_results,
        )
        if not result.success or result.content is None:
            raise AdapterRefusalError("Calendar observation unavailable")
        if len(result.content) > request.max_results:
            raise AdapterRefusalError("Calendar observation exceeds bound")
        return [item.model_dump(mode="json") for item in result.content]


class GmailDraftClient:
    """Fixed Google draft routes through a host-authenticated HTTP client."""

    _origin = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, JsonValue] | None = None,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, JsonValue]:
        with self._client.stream(
            method,
            self._origin + path,
            json=body,
            params=params,
            follow_redirects=False,
        ) as response:
            if response.is_redirect or response.status_code >= 400:
                raise AdapterAmbiguousError("Gmail request unavailable")
            data = bytearray()
            for chunk in response.iter_bytes():
                if len(data) + len(chunk) > 1024 * 1024:
                    raise AdapterAmbiguousError("Gmail response exceeds bound")
                data.extend(chunk)
        document = TypeAdapter(dict[str, JsonValue]).validate_python(json.loads(data))
        return document

    def _identity(self, mailbox: str) -> None:
        profile = self._request("GET", "/profile")
        if profile.get("emailAddress") != mailbox:
            raise AdapterRefusalError("Gmail account does not match admitted mailbox")

    def create(self, request: DraftCreate, key: str) -> tuple[str, JsonValue]:
        self._identity(str(request.mailbox))
        raw = _draft_bytes(request, key)
        created = self._request(
            "POST",
            "/drafts",
            body={"message": {"raw": base64.urlsafe_b64encode(raw).decode()}},
        )
        identifier = _draft_id(created)
        observed = self._get_raw(identifier)
        _verify_message(observed, raw)
        return identifier, {
            "draft_id": identifier,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
        }

    def get(self, request: DraftGet) -> tuple[str, JsonValue]:
        self._identity(str(request.mailbox))
        raw = self._get_raw(request.draft_id)
        return request.draft_id, {
            "draft_id": request.draft_id,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
        }

    def reconcile(self, request: DraftReconcile) -> tuple[str, JsonValue]:
        self._identity(str(request.mailbox))
        raw = _draft_bytes(request, request.creation_idempotency_key)
        message_id = str(
            BytesParser(policy=policy.default).parsebytes(raw)["Message-ID"]
        )
        listed = self._request(
            "GET", "/drafts", params={"q": "rfc822msgid:" + message_id, "maxResults": 2}
        )
        drafts = listed.get("drafts", [])
        if (
            not isinstance(drafts, list)
            or len(drafts) != 1
            or listed.get("nextPageToken")
        ):
            # Absence from a search index does not prove an earlier create failed.
            raise AdapterAmbiguousError("draft reconciliation is unresolved")
        candidate = drafts[0]
        if not isinstance(candidate, dict):
            raise AdapterAmbiguousError("draft reconciliation is unresolved")
        identifier = _draft_id(candidate)
        _verify_message(self._get_raw(identifier), raw)
        return identifier, {
            "draft_id": identifier,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
        }

    def _get_raw(self, identifier: str) -> bytes:
        result = self._request("GET", "/drafts/" + identifier, params={"format": "raw"})
        if _draft_id(result) != identifier:
            raise AdapterAmbiguousError("Gmail draft identity mismatch")
        message = result.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("raw"), str):
            raise AdapterAmbiguousError("Gmail draft content unavailable")
        value = message["raw"]
        if not isinstance(value, str):
            raise AdapterAmbiguousError("Gmail draft content unavailable")
        return base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )


def _draft_id(document: dict[str, JsonValue]) -> str:
    import re

    value = document.get("id")
    if (
        not isinstance(value, str)
        or re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value) is None
    ):
        raise AdapterAmbiguousError("Gmail draft identity unavailable")
    return value


def _draft_bytes(request: DraftCreate, key: str) -> bytes:
    marker = hashlib.sha256((str(request.mailbox) + "\n" + key).encode()).hexdigest()
    message = EmailMessage(policy=policy.SMTP)
    message["From"] = str(request.mailbox)
    message["To"] = ", ".join(str(item) for item in request.to)
    message["Subject"] = request.subject
    message["Message-ID"] = f"<{marker}@zeo-meeting.invalid>"
    message.set_content(request.body)
    return message.as_bytes()


def _verify_message(observed: bytes, expected: bytes) -> None:
    left = BytesParser(policy=policy.default).parsebytes(observed)
    right = BytesParser(policy=policy.default).parsebytes(expected)
    headers = ("From", "To", "Subject", "Message-ID")
    if (
        any(left.get_all(name) != right.get_all(name) for name in headers)
        or left.is_multipart()
        or left.get_content() != right.get_content()
    ):
        raise AdapterAmbiguousError("Gmail read-back does not match admitted draft")


class MeetingAdapters:
    """Validate all bindings before authority lookup; provider calls remain deferred."""

    def __init__(
        self,
        *,
        reads: GoogleReadPort | None = None,
        gmail: GmailDraftClient | None = None,
        notion: object | None = None,
    ) -> None:
        self._reads = reads
        self._gmail = gmail
        self._notion = notion

    def prepare(
        self, authorization: InvocationAuthorization, payload: dict[str, JsonValue]
    ) -> PreparedOperation:
        operation = authorization.operation
        if operation == "sheets.values.read":
            request = SheetsRead.model_validate(payload)
            _resource(
                authorization, f"sheets:{request.spreadsheet_id}:{request.range_a1}"
            )
            reads = self._required_reads()
            return lambda: ("", reads.sheets_values(request))
        if operation == "calendar.events.list":
            calendar = CalendarRead.model_validate(payload)
            _resource(authorization, f"calendar:{calendar.calendar_id}")
            reads = self._required_reads()
            return lambda: ("", reads.calendar_events(calendar))
        if operation == "notion.page.upsert":
            return self._notion_operation(authorization, payload)
        gmail = self._gmail
        if gmail is None:
            raise AdapterRefusalError("Gmail adapter is not configured")
        if operation == "gmail.draft.create":
            draft = DraftCreate.model_validate(payload)
            _resource(authorization, f"gmail:{draft.mailbox}:drafts")
            return lambda: gmail.create(draft, authorization.idempotency_key)
        if operation == "gmail.draft.get":
            lookup = DraftGet.model_validate(payload)
            _resource(authorization, f"gmail:{lookup.mailbox}:draft:{lookup.draft_id}")
            return lambda: gmail.get(lookup)
        reconcile = DraftReconcile.model_validate(payload)
        _resource(authorization, f"gmail:{reconcile.mailbox}:drafts")
        return lambda: gmail.reconcile(reconcile)

    def _required_reads(self) -> GoogleReadPort:
        if self._reads is None:
            raise AdapterRefusalError("Google read adapters are not configured")
        return self._reads

    def _notion_operation(
        self, authorization: InvocationAuthorization, payload: dict[str, JsonValue]
    ) -> PreparedOperation:
        from typing import cast

        from zeo_core.integrations.notion.upsert import (
            NotionPageUpsertProvider,
            NotionPageUpsertRequest,
        )

        request = NotionPageUpsertRequest.model_validate(payload)
        _resource(authorization, f"notion:{request.destination_parent_id}")
        if request.meeting_id != authorization.meeting_id or self._notion is None:
            raise AdapterRefusalError("Notion meeting or provider is unavailable")
        provider = cast(NotionPageUpsertProvider, self._notion)

        def execute() -> tuple[str, JsonValue]:
            try:
                matches = provider.find_by_marker(
                    destination_parent_id=request.destination_parent_id,
                    idempotency_marker=request.idempotency_marker,
                )
            except Exception:
                raise AdapterRefusalError("Notion destination unavailable") from None
            if len(matches) > 1:
                raise AdapterRefusalError("Notion marker is not unique")
            if matches and matches[0].title != request.title:
                raise AdapterRefusalError("Notion title conflicts")
            if not matches:
                result = provider.create(request)
            elif matches[0].markdown == request.canonical_markdown():
                result = matches[0]
            else:
                result = provider.replace_content(
                    page_id=matches[0].page_id, request=request
                )
            if (
                (bool(matches) and result.page_id != matches[0].page_id)
                or result.title != request.title
                or result.idempotency_marker != request.idempotency_marker
                or result.markdown != request.canonical_markdown()
            ):
                raise AdapterAmbiguousError("Notion read-back requires reconciliation")
            return result.page_id, {
                "page_id": result.page_id,
                "content_sha256": hashlib.sha256(result.markdown.encode()).hexdigest(),
            }

        return execute


def _resource(authorization: InvocationAuthorization, expected: str) -> None:
    if authorization.resource != expected:
        raise AdapterRefusalError("provider resource differs from runtime authority")
