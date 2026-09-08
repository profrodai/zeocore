"""Marketing behavior at the HTTP boundary, including forbidden effects."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from zeo_core.integrations.kit import (
    Audience,
    BroadcastDraft,
    KitAPIError,
    PageRequest,
    SendBroadcast,
    SequenceDraft,
    SequenceEmailDraft,
    SubscriberCreate,
    broadcast_send_digest,
    record_digest,
)
from zeo_core.integrations.kit.models import SourceFilter

from .conftest import ClientFixture, page, queue_snapshot, snapshot, upstream


def draft() -> BroadcastDraft:
    return BroadcastDraft(
        subject="News",
        content="<p>News</p>",
        email_address="editor@example.com",
        email_template_id=6,
        audience=Audience(filters=(SourceFilter(type="tag", ids=(1,)),)),
    )


def seq_draft() -> SequenceDraft:
    return SequenceDraft(
        name="Welcome", email_address="editor@example.com", email_template_id=6
    )


def email_draft() -> SequenceEmailDraft:
    return SequenceEmailDraft(
        subject="Welcome",
        content="<p>Welcome</p>",
        position=0,
        delay_value=1,
        delay_unit="days",
    )


def send_request(data: dict[str, Any], **kwargs: Any) -> SendBroadcast:  # noqa: ANN401
    return SendBroadcast(
        broadcast_id=57,
        expected_digest=broadcast_send_digest(
            data,
            send_at=kwargs.get("send_at"),
            publish_web=kwargs.get("publish_web", False),
        ),
        render_evidence_ref="approved/render",
        audience_policy_ref="approved/dynamic-audience",
        confirm=True,
        **kwargs,
    )


def test_broadcast_create_and_edit_remain_private_drafts(
    setup_client: ClientFixture, broadcast: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    responses.append(httpx.Response(201, json={"broadcast": broadcast}))
    assert client.create_broadcast(draft()).data["id"] == 57
    responses.extend(
        [
            httpx.Response(200, json={"broadcast": broadcast}),
            httpx.Response(200, json={"broadcast": {"stats": {"status": "draft"}}}),
            httpx.Response(200, json={"broadcast": broadcast}),
        ]
    )
    client.update_broadcast(57, draft(), expected_digest=record_digest(broadcast))
    assert [r.method for r in calls] == ["POST", "GET", "GET", "PUT"]
    for request in (calls[0], calls[-1]):
        body = json.loads(request.content)
        assert body["send_at"] is None and body["public"] is False
        assert body["subscriber_filter"] == [{"all": [{"type": "tag", "ids": [1]}]}]


@pytest.mark.parametrize(
    "scheduled,public", [(False, False), (True, False), (True, True)]
)
def test_send_creates_new_object_from_approved_bytes(
    setup_client: ClientFixture,
    broadcast: dict[str, Any],
    scheduled: bool,
    public: bool,
) -> None:
    client, calls, responses = setup_client
    stamp = datetime.now(UTC) + timedelta(days=1) if scheduled else None
    request = send_request(broadcast, send_at=stamp, publish_web=public)
    responses.extend(
        [
            httpx.Response(200, json={"broadcast": broadcast}),
            httpx.Response(200, json={"broadcast": {"stats": {"status": "draft"}}}),
            httpx.Response(201, json={"broadcast": {"id": 58}}),
        ]
    )
    result = client.send_broadcast(request)
    assert result.data["id"] == 58
    assert [(r.method, r.url.path) for r in calls] == [
        ("GET", "/v4/broadcasts/57"),
        ("GET", "/v4/broadcasts/57/stats"),
        ("POST", "/v4/broadcasts"),
    ]
    body = json.loads(calls[-1].content)
    assert (
        body["subject"] == broadcast["subject"]
        and body["content"] == broadcast["content"]
    )
    assert body["public"] is public and body["subscriber_filter"] == []
    assert body["send_at"] is not None
    if stamp:
        assert datetime.fromisoformat(body["send_at"]) == stamp


@pytest.mark.parametrize(
    "change",
    ["subject", "content", "subscriber_filter", "email_template", "email_address"],
)
def test_changed_broadcast_never_sends(
    setup_client: ClientFixture, broadcast: dict[str, Any], change: str
) -> None:
    client, calls, responses = setup_client
    request = send_request(broadcast)
    broadcast[change] = "tampered"
    responses.append(httpx.Response(200, json={"broadcast": broadcast}))
    with pytest.raises(ValueError, match="changed"):
        client.send_broadcast(request)
    assert len(calls) == 1 and calls[0].method == "GET"


@pytest.mark.parametrize("state", ["sending", "completed", "aborted", "unknown"])
def test_broadcast_cannot_send_or_delete_after_delivery_starts(
    setup_client: ClientFixture, broadcast: dict[str, Any], state: str
) -> None:
    client, calls, responses = setup_client
    for operation in [
        lambda: client.send_broadcast(send_request(broadcast)),
        lambda: client.delete_broadcast(
            57, expected_digest=record_digest(broadcast), confirm=True
        ),
    ]:
        responses.extend(
            [
                httpx.Response(200, json={"broadcast": broadcast}),
                httpx.Response(200, json={"broadcast": {"stats": {"status": state}}}),
            ]
        )
        with pytest.raises(ValueError, match="delivery state"):
            operation()
    assert all(r.method == "GET" for r in calls)


def test_broadcast_delete_is_explicit_hard_delete(
    setup_client: ClientFixture, broadcast: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [
            httpx.Response(200, json={"broadcast": broadcast}),
            httpx.Response(200, json={"broadcast": {"stats": {"status": "scheduled"}}}),
            httpx.Response(204),
        ]
    )
    assert (
        client.delete_broadcast(
            57, expected_digest=record_digest(broadcast), confirm=True
        ).data
        == {}
    )
    assert calls[-1].method == "DELETE"


@pytest.mark.parametrize(
    "field,value",
    [
        ("published_at", "secret-bad-date"),
        ("email_template", None),
        ("email_template", {"id": "secret-invalid"}),
        ("subscriber_filter", [{"all": []}]),
        ("subscriber_filter", [{"all": [], "any": []}]),
        ("subscriber_filter", [{"all": [{"type": "unreviewed-secret"}]}]),
        ("thumbnail_url", {}),
        ("email_address", "secret-bad-address"),
    ],
)
def test_provider_shape_errors_are_safe_before_send(
    setup_client: ClientFixture, broadcast: dict[str, Any], field: str, value: object
) -> None:
    client, calls, responses = setup_client
    broadcast[field] = value
    responses.extend(
        [
            httpx.Response(200, json={"broadcast": broadcast}),
            httpx.Response(200, json={"broadcast": {"stats": {"status": "draft"}}}),
        ]
    )
    with pytest.raises(ValueError) as error:
        client.send_broadcast(send_request(broadcast))
    assert "secret" not in str(error.value)
    assert all(r.method == "GET" for r in calls)


def test_missing_confirmation_and_invalid_schedule_do_not_call_provider(
    setup_client: ClientFixture, broadcast: dict[str, Any]
) -> None:
    client, calls, _ = setup_client
    with pytest.raises(ValueError):
        client.send_broadcast(
            send_request(broadcast).model_copy(update={"confirm": False})
        )
    with pytest.raises(ValueError):
        send_request(broadcast, send_at=datetime.now(UTC) - timedelta(seconds=1))
    with pytest.raises(ValueError):
        send_request(broadcast, send_at=datetime(2099, 1, 1))
    assert not calls


def test_sequence_authoring_is_paused_and_draft_only(
    setup_client: ClientFixture, sequence: dict[str, Any], email: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    responses.append(httpx.Response(201, json={"sequence": sequence}))
    client.create_sequence(seq_draft())
    queue_snapshot(responses, sequence, email)
    responses.append(httpx.Response(200, json={"sequence": sequence}))
    client.update_sequence(
        23, seq_draft(), expected_digest=record_digest(snapshot(sequence, email))
    )
    queue_snapshot(responses, sequence, email)
    responses.append(httpx.Response(200, json={"email": email}))
    client.save_sequence_email(
        23,
        email_draft(),
        email_id=38,
        expected_digest=record_digest(snapshot(sequence, email)),
    )
    writes = [json.loads(r.content) for r in calls if r.method != "GET"]
    assert writes[0]["active"] is False and writes[1]["active"] is False
    assert writes[2]["published"] is False
    assert calls[-2].url.params["include_content"] == "true"


def test_new_sequence_email_and_publication(
    setup_client: ClientFixture, sequence: dict[str, Any], email: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [
            httpx.Response(200, json={"sequence": sequence}),
            httpx.Response(200, json=page("emails", [])),
            httpx.Response(201, json={"email": email}),
        ]
    )
    empty = {"sequence": snapshot(sequence, email)["sequence"], "emails": []}
    client.save_sequence_email(23, email_draft(), expected_digest=record_digest(empty))
    assert (
        calls[-1].method == "POST"
        and json.loads(calls[-1].content)["published"] is False
    )
    queue_snapshot(responses, sequence, email)
    responses.append(httpx.Response(200, json={"email": email}))
    client.publish_sequence_email(
        23,
        38,
        expected_digest=record_digest(snapshot(sequence, email)),
        published=True,
        confirm=True,
        render_evidence_ref="review/render",
    )
    assert json.loads(calls[-1].content) == {"published": True}


def test_activate_then_pause_with_unreadable_email_graph(
    setup_client: ClientFixture, sequence: dict[str, Any], email: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    queue_snapshot(responses, sequence, email)
    responses.append(httpx.Response(200, json={"sequence": sequence}))
    client.set_sequence_active(
        23,
        active=True,
        expected_digest=record_digest(snapshot(sequence, email)),
        confirm=True,
        render_evidence_ref="render",
        audience_policy_ref="policy",
    )
    assert json.loads(calls[-1].content) == {"active": True}
    sequence["future_unknown_setting"] = {"enabled": True}
    responses.extend(
        [
            httpx.Response(200, json={"sequence": sequence}),
            httpx.Response(200, json={"sequence": sequence}),
        ]
    )
    client.set_sequence_active(
        23, active=False, expected_digest=record_digest(sequence), confirm=True
    )
    assert json.loads(calls[-1].content) == {"active": False}
    assert calls[-2].url.path == "/v4/sequences/23"


@pytest.mark.parametrize(
    "field,value",
    [
        ("content", None),
        ("delay_value", -1),
        ("sequence_id", 99),
        ("id", {}),
        ("position", {}),
        ("published", False),
    ],
)
def test_activation_refuses_invalid_sequence(
    setup_client: ClientFixture,
    sequence: dict[str, Any],
    email: dict[str, Any],
    field: str,
    value: object,
) -> None:
    client, calls, responses = setup_client
    email[field] = value
    queue_snapshot(responses, sequence, email)
    with pytest.raises(ValueError):
        client.set_sequence_active(
            23,
            active=True,
            expected_digest=record_digest(snapshot(sequence, email)),
            confirm=True,
            render_evidence_ref="render",
            audience_policy_ref="policy",
        )
    assert all(r.method == "GET" for r in calls)


def test_aggregate_review_requires_complete_emails(
    setup_client: ClientFixture, sequence: dict[str, Any], email: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [
            httpx.Response(200, json={"sequence": sequence}),
            httpx.Response(200, json=page("emails", [email], more=True)),
        ]
    )
    with pytest.raises(ValueError, match="complete"):
        client.sequence_snapshot(23)
    assert len(calls) == 2


def test_edit_refuses_active_changed_or_occupied_sequence(
    setup_client: ClientFixture, sequence: dict[str, Any], email: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    for active, digest, message in [
        (True, None, "Pause"),
        (False, "0" * 64, "changed"),
        (False, None, "unoccupied"),
    ]:
        sequence["active"] = active
        queue_snapshot(responses, sequence, email)
        with pytest.raises(ValueError, match=message):
            client.save_sequence_email(
                23,
                email_draft(),
                expected_digest=digest or record_digest(snapshot(sequence, email)),
            )
    assert all(r.method == "GET" for r in calls)


@pytest.mark.parametrize(
    "state", ["active", "inactive", "cancelled", "complained", "bounced"]
)
def test_enroll_never_repairs_consent(
    setup_client: ClientFixture,
    sequence: dict[str, Any],
    email: dict[str, Any],
    state: str,
) -> None:
    client, calls, responses = setup_client
    sequence["active"] = True
    subscriber = upstream("/v4/subscribers/{id}")["subscriber"]
    subscriber.update(id=357, state=state)
    queue_snapshot(responses, sequence, email)
    responses.append(httpx.Response(200, json={"subscriber": subscriber}))
    arguments = {
        "expected_sequence_digest": record_digest(snapshot(sequence, email)),
        "expected_subscriber_digest": record_digest(subscriber),
        "confirm": True,
        "approval_ref": "approval",
    }
    if state == "active":
        responses.append(httpx.Response(201, json={"subscriber": subscriber}))
        client.enroll(23, 357, **arguments)  # type: ignore[arg-type]
        assert calls[-1].url.path == "/v4/sequences/23/subscribers/357"
    else:
        with pytest.raises(ValueError, match="not active"):
            client.enroll(23, 357, **arguments)  # type: ignore[arg-type]
        assert all(r.method == "GET" for r in calls)
    assert not any(
        r.method == "POST" and r.url.path == "/v4/subscribers" for r in calls
    )


def test_subscriber_upsert_does_not_claim_reactivation_and_unsubscribe_is_global(
    setup_client: ClientFixture,
) -> None:
    client, calls, responses = setup_client
    subscriber = {"id": 357, "state": "cancelled"}
    responses.append(httpx.Response(200, json={"subscriber": subscriber}))
    result = client.create_subscriber(
        SubscriberCreate(
            email_address="reader@example.com",
            state="active",
            consent_evidence_ref="independent-consent",
            confirm=True,
        )
    )
    assert result.data["state"] == "cancelled"
    assert "consent_evidence_ref" not in json.loads(calls[-1].content)
    responses.extend(
        [httpx.Response(200, json={"subscriber": subscriber}), httpx.Response(204)]
    )
    client.unsubscribe(357, expected_digest=record_digest(subscriber), confirm=True)
    assert calls[-1].url.path == "/v4/subscribers/357/unsubscribe"


def test_tag_organization_and_membership_effects(setup_client: ClientFixture) -> None:
    client, calls, responses = setup_client
    for tag_id in [None, 7]:
        responses.append(
            httpx.Response(200, json={"tag": {"id": 7, "name": "Campaign"}})
        )
        client.save_tag("Campaign", tag_id=tag_id)
    for remove in [False, True]:
        with pytest.raises(ValueError):
            client.set_tag(
                7, 357, remove=remove, confirm=False, approval_ref="automation-review"
            )
        responses.append(
            httpx.Response(204)
            if remove
            else httpx.Response(201, json={"subscriber": {"id": 357}})
        )
        client.set_tag(
            7, 357, remove=remove, confirm=True, approval_ref="automation-review"
        )
    assert [r.method for r in calls] == ["POST", "PUT", "POST", "DELETE"]


def test_sequence_deletion_paths(
    setup_client: ClientFixture, sequence: dict[str, Any], email: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    queue_snapshot(responses, sequence, email)
    responses.append(httpx.Response(204))
    client.delete_sequence_email(
        23, 38, expected_digest=record_digest(snapshot(sequence, email)), confirm=True
    )
    responses.extend(
        [httpx.Response(200, json={"sequence": sequence}), httpx.Response(204)]
    )
    client.delete_sequence(23, expected_digest=record_digest(sequence), confirm=True)
    assert [r.url.path for r in calls if r.method == "DELETE"] == [
        "/v4/sequences/23/emails/38",
        "/v4/sequences/23",
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"filters": []},
        {"entire_account": True, "mode": "none"},
        {"filters": [{"type": "tag", "ids": [1, 1]}]},
        {"filters": [{"type": "tag", "ids": [True]}]},
    ],
)
def test_no_accidental_all_subscriber_audience(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Audience.model_validate(payload)


@pytest.mark.parametrize(
    "changes",
    [
        {"position": 1, "delay_value": 0},
        {"delay_unit": "hours", "delay_value": 0},
        {"delay_unit": "hours", "send_days": ["monday"]},
        {"send_days": []},
    ],
)
def test_sequence_delay_boundaries(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SequenceEmailDraft.model_validate({**email_draft().model_dump(), **changes})


def test_inactive_default_and_hour_delay_serialization() -> None:
    assert SubscriberCreate(email_address="reader@example.com").state == "inactive"
    with pytest.raises(ValidationError):
        SubscriberCreate(email_address="reader@example.com", state="active")
    data = email_draft().model_dump()
    data.update(delay_unit="hours", delay_value=2)
    assert "send_days" not in SequenceEmailDraft.model_validate(data).to_api()


def test_wrong_resource_identity_fails_closed(setup_client: ClientFixture) -> None:
    client, _, responses = setup_client
    responses.append(httpx.Response(200, json={"subscriber": {"id": 2}}))
    with pytest.raises(KitAPIError, match="identity"):
        client.get_subscriber(1)


def test_first_page_empty_is_complete_but_cursor_page_is_not(
    setup_client: ClientFixture,
) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [httpx.Response(200, json=page("subscribers", [])) for _ in range(2)]
    )
    assert client.list_subscribers().complete
    assert not client.list_subscribers(PageRequest(after="previous")).complete
    assert calls[-1].url.params["status"] == "all"


@pytest.mark.parametrize(
    "paging",
    [
        {},
        {"has_next_page": "false", "has_previous_page": False},
        {"has_next_page": True, "has_previous_page": False, "end_cursor": "same"},
    ],
)
def test_incomplete_pagination_fails_closed(
    setup_client: ClientFixture, paging: dict[str, Any]
) -> None:
    client, _, responses = setup_client
    responses.append(httpx.Response(200, json={"tags": [], "pagination": paging}))
    with pytest.raises(KitAPIError):
        client.list_tags(PageRequest(after="same"))
