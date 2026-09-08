"""Explicit Kit marketing routes and review-bound effects."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, SecretStr, TypeAdapter, ValidationError

from .models import (
    Audience,
    BroadcastDraft,
    Digest,
    Id,
    Page,
    PageRequest,
    Record,
    SendBroadcast,
    SequenceDraft,
    SequenceEmailDraft,
    SourceFilter,
    SubscriberCreate,
    aware,
    broadcast_send_digest,
    record_digest,
)
from .transport import KitAPIError, KitTransport

_DEFAULT_PAGE = PageRequest()


def _provider_model[T: BaseModel](model: type[T], data: object) -> T:
    try:
        return model.model_validate(data)
    except ValidationError:
        raise ValueError("Kit resource contains unsupported fields or values") from None


def _id(value: int) -> str:
    return str(TypeAdapter(Id).validate_python(value))


def _review(data: dict[str, Any], expected: str) -> None:
    TypeAdapter(Digest).validate_python(expected)
    if record_digest(data) != expected:
        raise ValueError("Kit resource changed since review")


def _confirm(confirmed: bool, *references: str) -> None:
    if not confirmed or any(not ref.strip() for ref in references):
        raise ValueError(
            "Explicit confirmation and host-verified evidence are required"
        )


class KitClient:
    def __init__(
        self,
        api_key: SecretStr | None = None,
        *,
        access_token: SecretStr | None = None,
        transport: KitTransport | None = None,
    ) -> None:
        self._transport = transport or KitTransport(api_key, access_token=access_token)

    def close(self) -> None:
        self._transport.close()

    def _record(
        self,
        method: str,
        path: str,
        key: str | None = None,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, str | int | bool] | None = None,
    ) -> Record:
        data = self._transport.request(method, path, body=body, params=params)
        value = data.get(key) if key else data
        if not isinstance(value, dict):
            raise KitAPIError(
                "RESPONSE",
                "Kit returned an invalid resource",
                outcome_unknown=method != "GET",
            )
        if key and method == "GET" and path.rsplit("/", 1)[-1].isdigit():
            if (
                type(value.get("id")) is not int
                or str(value["id"]) != path.rsplit("/", 1)[-1]
            ):
                raise KitAPIError(
                    "RESPONSE", "Kit returned a different resource identity"
                )
        return Record(data=value)

    def _page(
        self,
        path: str,
        key: str,
        page: PageRequest,
        *,
        params: dict[str, str | int | bool] | None = None,
    ) -> Page:
        query: dict[str, str | int | bool] = {
            "per_page": page.per_page,
            **(params or {}),
        }
        if page.after is not None:
            query["after"] = page.after
        data = self._transport.request("GET", path, params=query)
        rows, paging = data.get(key), data.get("pagination")
        if (
            not isinstance(rows, list)
            or len(rows) > page.per_page
            or not all(isinstance(row, dict) for row in rows)
            or not isinstance(paging, dict)
        ):
            raise KitAPIError("RESPONSE", "Kit returned an invalid page")
        has_next, has_previous = (
            paging.get("has_next_page"),
            paging.get("has_previous_page"),
        )
        if type(has_next) is not bool or type(has_previous) is not bool:
            raise KitAPIError("RESPONSE", "Kit omitted pagination completeness")
        after = paging.get("end_cursor") if has_next else None
        if has_next and (
            not isinstance(after, str)
            or not after
            or len(after) > 2048
            or after == page.after
        ):
            raise KitAPIError("RESPONSE", "Kit returned an invalid or repeated cursor")
        return Page(
            results=rows,
            next_after=after,
            complete=page.after is None and not has_next and not has_previous,
        )

    def account(self) -> Record:
        return self._record("GET", "/v4/account")

    def account_metrics(self) -> Record:
        return self._record("GET", "/v4/account/email_stats")

    def list_broadcasts(self, page: PageRequest = _DEFAULT_PAGE) -> Page:
        return self._page("/v4/broadcasts", "broadcasts", page)

    def get_broadcast(self, broadcast_id: int) -> Record:
        return self._record("GET", f"/v4/broadcasts/{_id(broadcast_id)}", "broadcast")

    def broadcast_metrics(self, broadcast_id: int) -> Record:
        return self._record(
            "GET", f"/v4/broadcasts/{_id(broadcast_id)}/stats", "broadcast"
        )

    def broadcast_clicks(self, broadcast_id: int) -> Record:
        return self._record("GET", f"/v4/broadcasts/{_id(broadcast_id)}/clicks")

    def list_templates(self, page: PageRequest = _DEFAULT_PAGE) -> Page:
        return self._page("/v4/email_templates", "email_templates", page)

    def list_segments(self, page: PageRequest = _DEFAULT_PAGE) -> Page:
        return self._page("/v4/segments", "segments", page)

    def create_broadcast(self, draft: BroadcastDraft) -> Record:
        return self._record("POST", "/v4/broadcasts", "broadcast", body=draft.to_api())

    def _broadcast_state(self, broadcast_id: int, allowed: set[str]) -> None:
        stats = self.broadcast_metrics(broadcast_id).data.get("stats")
        if not isinstance(stats, dict) or stats.get("status") not in allowed:
            raise ValueError("Broadcast delivery state does not permit this operation")

    def update_broadcast(
        self, broadcast_id: int, draft: BroadcastDraft, *, expected_digest: str
    ) -> Record:
        current = self.get_broadcast(broadcast_id).data
        _review(current, expected_digest)
        self._broadcast_state(broadcast_id, {"draft"})
        if current.get("public") is not False or current.get("send_at") is not None:
            raise ValueError("Only a private unscheduled draft can be edited")
        return self._record(
            "PUT",
            f"/v4/broadcasts/{_id(broadcast_id)}",
            "broadcast",
            body=draft.to_api(),
        )

    @staticmethod
    def _audience(data: object) -> Audience:
        if data == []:
            return Audience(entire_account=True)
        if (
            not isinstance(data, list)
            or len(data) != 1
            or not isinstance(data[0], dict)
        ):
            raise ValueError("Unsupported Kit audience shape")
        groups = {key: value for key, value in data[0].items() if value is not None}
        if len(groups) != 1:
            raise ValueError("Only one Kit audience group is supported")
        mode, items = next(iter(groups.items()))
        if mode == "all" and items == [{"type": "all_subscribers"}]:
            return Audience(entire_account=True)
        if not isinstance(items, list):
            raise ValueError("Invalid Kit audience filters")
        return _provider_model(
            Audience,
            {
                "mode": mode,
                "filters": [_provider_model(SourceFilter, item) for item in items],
            },
        )

    @classmethod
    def _send_body(cls, data: dict[str, Any], request: SendBroadcast) -> dict[str, Any]:
        template = data.get("email_template")
        if not isinstance(template, dict):
            raise ValueError("Review requires an explicit provider template")
        if template.get("category") == "Starting point":
            raise ValueError("Kit starting point templates are unsupported")
        published_at = data.get("published_at") or data.get("created_at")
        if not isinstance(published_at, str):
            raise ValueError("Kit broadcast has no publication timestamp")
        # Parse without retaining malformed provider data in direct-client errors.
        try:
            stamp = datetime.fromisoformat(published_at)
        except ValueError:
            raise ValueError("Kit broadcast timestamp is invalid") from None
        draft = _provider_model(
            BroadcastDraft,
            {
                "subject": data.get("subject"),
                "content": data.get("content"),
                "email_address": data.get("email_address"),
                "email_template_id": template.get("id"),
                "audience": cls._audience(data.get("subscriber_filter")),
                "description": data.get("description") or "",
                "preview_text": data.get("preview_text") or "",
                "published_at": stamp,
            },
        )
        body = draft.to_api()
        # These approved display bytes must survive validation without trimming.
        body.update(subject=data["subject"], content=data["content"])
        for key in ("thumbnail_alt", "thumbnail_url"):
            value = data.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError("Kit thumbnail metadata is invalid")
            body[key] = value
        body.update(
            public=request.publish_web,
            send_at=aware(request.send_at).isoformat()
            if request.send_at
            else datetime.now(UTC).isoformat(),
        )
        return body

    def send_broadcast(self, request: SendBroadcast) -> Record:
        """Create a scheduled copy from reviewed bytes, preserving the source draft.

        The create endpoint separates public-web publication from email sending.
        Track/cancel the NEW returned broadcast ID; never replay an unknown result.
        """
        _confirm(
            request.confirm, request.render_evidence_ref, request.audience_policy_ref
        )
        if request.send_at is not None and aware(request.send_at) <= datetime.now(UTC):
            raise ValueError("Kit schedule expired before dispatch")
        current = self.get_broadcast(request.broadcast_id).data
        if (
            broadcast_send_digest(
                current, send_at=request.send_at, publish_web=request.publish_web
            )
            != request.expected_digest
        ):
            raise ValueError("Kit send specification changed since review")
        self._broadcast_state(request.broadcast_id, {"draft"})
        if current.get("public") is not False or current.get("send_at") is not None:
            raise ValueError("Sending requires a private unscheduled source draft")
        body = self._send_body(current, request)
        if request.send_at is not None and aware(request.send_at) <= datetime.now(UTC):
            raise ValueError("Kit schedule expired during preflight")
        return self._record("POST", "/v4/broadcasts", "broadcast", body=body)

    def delete_broadcast(
        self, broadcast_id: int, *, expected_digest: str, confirm: bool
    ) -> Record:
        """Hard-delete a draft/scheduled broadcast. Not a promise to undo delivery."""
        _confirm(confirm)
        _review(self.get_broadcast(broadcast_id).data, expected_digest)
        self._broadcast_state(broadcast_id, {"draft", "scheduled"})
        return self._record("DELETE", f"/v4/broadcasts/{_id(broadcast_id)}")

    def list_sequences(self, page: PageRequest = _DEFAULT_PAGE) -> Page:
        return self._page(
            "/v4/sequences", "sequences", page, params={"include": "stats"}
        )

    def get_sequence(self, sequence_id: int) -> Record:
        return self._record("GET", f"/v4/sequences/{_id(sequence_id)}", "sequence")

    def sequence_metrics(self, sequence_id: int) -> Record:
        return self._record(
            "GET",
            f"/v4/sequences/{_id(sequence_id)}",
            "sequence",
            params={"include": "stats"},
        )

    def list_sequence_emails(
        self, sequence_id: int, page: PageRequest = _DEFAULT_PAGE
    ) -> Page:
        return self._page(
            f"/v4/sequences/{_id(sequence_id)}/emails",
            "emails",
            page,
            params={"include_content": True},
        )

    def get_sequence_email(self, sequence_id: int, email_id: int) -> Record:
        return self._record(
            "GET", f"/v4/sequences/{_id(sequence_id)}/emails/{_id(email_id)}", "email"
        )

    def sequence_snapshot(self, sequence_id: int) -> Record:
        sequence = self.get_sequence(sequence_id).data
        page = self.list_sequence_emails(sequence_id, PageRequest(per_page=100))
        if not page.complete:
            raise ValueError(
                "Sequence approval requires its complete bounded email set"
            )
        sequence = {
            key: value
            for key, value in sequence.items()
            if key not in {"stats", "subscriber_count", "email_count"}
        }
        return Record(data={"sequence": sequence, "emails": page.results})

    def create_sequence(self, draft: SequenceDraft) -> Record:
        return self._record("POST", "/v4/sequences", "sequence", body=draft.to_api())

    def _inactive_snapshot(
        self, sequence_id: int, expected_digest: str
    ) -> dict[str, Any]:
        snapshot = self.sequence_snapshot(sequence_id).data
        _review(snapshot, expected_digest)
        if snapshot["sequence"].get("active") is not False:
            raise ValueError("Pause the sequence before editing its definition")
        return snapshot

    def update_sequence(
        self, sequence_id: int, draft: SequenceDraft, *, expected_digest: str
    ) -> Record:
        self._inactive_snapshot(sequence_id, expected_digest)
        return self._record(
            "PUT", f"/v4/sequences/{_id(sequence_id)}", "sequence", body=draft.to_api()
        )

    def save_sequence_email(
        self,
        sequence_id: int,
        draft: SequenceEmailDraft,
        *,
        expected_digest: str,
        email_id: int | None = None,
    ) -> Record:
        snapshot = self._inactive_snapshot(sequence_id, expected_digest)
        if email_id is not None and not any(
            row.get("id") == email_id for row in snapshot["emails"]
        ):
            raise ValueError("Email is not part of the reviewed sequence")
        if any(
            row.get("position") == draft.position and row.get("id") != email_id
            for row in snapshot["emails"]
        ):
            raise ValueError("Choose an unoccupied email position")
        path = f"/v4/sequences/{_id(sequence_id)}/emails"
        if email_id is not None:
            path += f"/{_id(email_id)}"
        return self._record(
            "PUT" if email_id is not None else "POST",
            path,
            "email",
            body=draft.to_api(),
        )

    def publish_sequence_email(
        self,
        sequence_id: int,
        email_id: int,
        *,
        expected_digest: str,
        published: bool,
        confirm: bool,
        render_evidence_ref: str,
    ) -> Record:
        _confirm(confirm, render_evidence_ref)
        snapshot = self._inactive_snapshot(sequence_id, expected_digest)
        matches = [row for row in snapshot["emails"] if row.get("id") == email_id]
        if len(matches) != 1:
            raise ValueError("Review must identify one sequence email")
        if published:
            self._validate_email(matches[0], sequence_id)
        return self._record(
            "PUT",
            f"/v4/sequences/{_id(sequence_id)}/emails/{_id(email_id)}",
            "email",
            body={"published": published},
        )

    @staticmethod
    def _validate_email(row: dict[str, Any], sequence_id: int) -> None:
        if row.get("sequence_id") != sequence_id:
            raise ValueError("Email belongs to another sequence")
        fields = {
            key: row[key] for key in SequenceEmailDraft.model_fields if key in row
        }
        # Kit responses allow null preview text. Hour-based delivery ignores the
        # day schedule; omit its response decoration from the authoring model.
        if fields.get("preview_text") is None:
            fields["preview_text"] = ""
        if fields.get("delay_unit") == "hours":
            fields.pop("send_days", None)
        _provider_model(SequenceEmailDraft, fields)

    @classmethod
    def _validate_active_snapshot(
        cls, snapshot: dict[str, Any], sequence_id: int
    ) -> None:
        sequence, emails = snapshot["sequence"], snapshot["emails"]
        _provider_model(
            SequenceDraft,
            {
                key: sequence[key]
                for key in SequenceDraft.model_fields
                if key in sequence
            },
        )
        ids, positions = (
            [row.get("id") for row in emails],
            [row.get("position") for row in emails],
        )
        if any(type(value) is not int or value < 1 for value in ids) or any(
            type(value) is not int or not 0 <= value <= 99 for value in positions
        ):
            raise ValueError("Sequence email identities or positions are invalid")
        if (
            not emails
            or len(set(ids)) != len(ids)
            or len(set(positions)) != len(positions)
        ):
            raise ValueError("Sequence must have unique email IDs and positions")
        published = [row for row in emails if row.get("published") is True]
        if not published:
            raise ValueError("Sequence has no published email")
        for row in published:
            cls._validate_email(row, sequence_id)

    def set_sequence_active(
        self,
        sequence_id: int,
        *,
        active: bool,
        expected_digest: str,
        confirm: bool,
        render_evidence_ref: str = "",
        audience_policy_ref: str = "",
    ) -> Record:
        _confirm(confirm)
        if active:
            _confirm(confirm, render_evidence_ref, audience_policy_ref)
            snapshot = self.sequence_snapshot(sequence_id).data
            _review(snapshot, expected_digest)
            self._validate_active_snapshot(snapshot, sequence_id)
        else:
            # Risk-reducing pause depends on reviewed identity/settings, not a
            # perfectly understood graph. Queued sends still need reconciliation.
            _review(self.get_sequence(sequence_id).data, expected_digest)
        return self._record(
            "PUT",
            f"/v4/sequences/{_id(sequence_id)}",
            "sequence",
            body={"active": active},
        )

    def delete_sequence(
        self, sequence_id: int, *, expected_digest: str, confirm: bool
    ) -> Record:
        _confirm(confirm)
        _review(self.get_sequence(sequence_id).data, expected_digest)
        return self._record("DELETE", f"/v4/sequences/{_id(sequence_id)}")

    def delete_sequence_email(
        self, sequence_id: int, email_id: int, *, expected_digest: str, confirm: bool
    ) -> Record:
        _confirm(confirm)
        snapshot = self._inactive_snapshot(sequence_id, expected_digest)
        if not any(row.get("id") == email_id for row in snapshot["emails"]):
            raise ValueError("Email is not part of the reviewed sequence")
        return self._record(
            "DELETE", f"/v4/sequences/{_id(sequence_id)}/emails/{_id(email_id)}"
        )

    def list_sequence_subscribers(
        self, sequence_id: int, page: PageRequest = _DEFAULT_PAGE
    ) -> Page:
        return self._page(
            f"/v4/sequences/{_id(sequence_id)}/subscribers",
            "subscribers",
            page,
            params={"status": "all"},
        )

    def enroll(
        self,
        sequence_id: int,
        subscriber_id: int,
        *,
        expected_sequence_digest: str,
        expected_subscriber_digest: str,
        confirm: bool,
        approval_ref: str,
    ) -> Record:
        _confirm(confirm, approval_ref)
        snapshot = self.sequence_snapshot(sequence_id).data
        _review(snapshot, expected_sequence_digest)
        if snapshot["sequence"].get("active") is not True:
            raise ValueError("Sequence must be active before enrollment")
        self._validate_active_snapshot(snapshot, sequence_id)
        subscriber = self.get_subscriber(subscriber_id).data
        _review(subscriber, expected_subscriber_digest)
        if subscriber.get("state") != "active":
            raise ValueError(
                "Subscriber is not active; never automatically repair consent"
            )
        return self._record(
            "POST",
            f"/v4/sequences/{_id(sequence_id)}/subscribers/{_id(subscriber_id)}",
            "subscriber",
            body={},
        )

    def list_subscribers(self, page: PageRequest = _DEFAULT_PAGE) -> Page:
        return self._page(
            "/v4/subscribers", "subscribers", page, params={"status": "all"}
        )

    def get_subscriber(self, subscriber_id: int) -> Record:
        return self._record(
            "GET", f"/v4/subscribers/{_id(subscriber_id)}", "subscriber"
        )

    def create_subscriber(self, request: SubscriberCreate) -> Record:
        return self._record(
            "POST", "/v4/subscribers", "subscriber", body=request.to_api()
        )

    def unsubscribe(
        self, subscriber_id: int, *, expected_digest: str, confirm: bool
    ) -> Record:
        _confirm(confirm)
        _review(self.get_subscriber(subscriber_id).data, expected_digest)
        return self._record("POST", f"/v4/subscribers/{_id(subscriber_id)}/unsubscribe")

    def list_tags(self, page: PageRequest = _DEFAULT_PAGE) -> Page:
        return self._page("/v4/tags", "tags", page)

    def subscriber_tags(
        self, subscriber_id: int, page: PageRequest = _DEFAULT_PAGE
    ) -> Page:
        return self._page(f"/v4/subscribers/{_id(subscriber_id)}/tags", "tags", page)

    def tag_subscribers(self, tag_id: int, page: PageRequest = _DEFAULT_PAGE) -> Page:
        return self._page(
            f"/v4/tags/{_id(tag_id)}/subscribers",
            "subscribers",
            page,
            params={"status": "all"},
        )

    def save_tag(self, name: str, *, tag_id: int | None = None) -> Record:
        if not name.strip():
            raise ValueError("Tag name is required")
        return self._record(
            "PUT" if tag_id is not None else "POST",
            f"/v4/tags/{_id(tag_id)}" if tag_id is not None else "/v4/tags",
            "tag",
            body={"name": name},
        )

    def set_tag(
        self,
        tag_id: int,
        subscriber_id: int,
        *,
        remove: bool,
        confirm: bool,
        approval_ref: str,
    ) -> Record:
        _confirm(confirm, approval_ref)
        # Both adding and removing tags may trigger account Visual Automations.
        return self._record(
            "DELETE" if remove else "POST",
            f"/v4/tags/{_id(tag_id)}/subscribers/{_id(subscriber_id)}",
            None if remove else "subscriber",
            body=None if remove else {},
        )
