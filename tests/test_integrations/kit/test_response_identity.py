"""Elder review: a dispatched write needs an operation-bound response identity."""

from __future__ import annotations

from functools import partial
from typing import Any

import httpx
import pytest

from zeo_core.integrations.kit import KitAPIError, KitIntegration, record_digest
from zeo_core.tools import CapabilityRegistry, invoke_sync
from zeo_core.tools.builtin.kit import register_capabilities

from .conftest import ClientFixture, queue_snapshot, snapshot
from .test_boundary import context
from .test_marketing import draft, send_request


@pytest.mark.parametrize(
    "record",
    [
        {},
        {"id": 57},
        {"id": True},
        {"id": -1},
        {"id": 0},
        {"id": "58"},
        {"id": None},
        {"id": 58.0},
        {"id": {"secret": "provider-value"}},
    ],
)
@pytest.mark.parametrize("capability", [False, True])
def test_send_requires_distinct_strict_identity_after_one_post(
    setup_client: ClientFixture,
    broadcast: dict[str, Any],
    record: dict[str, Any],
    capability: bool,
) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [
            httpx.Response(200, json={"broadcast": broadcast}),
            httpx.Response(200, json={"broadcast": {"stats": {"status": "draft"}}}),
            httpx.Response(201, json={"broadcast": record}),
        ]
    )
    request = send_request(broadcast)
    if capability:
        registry = CapabilityRegistry()
        register_capabilities(registry)
        result = invoke_sync(
            registry.get("kit.marketing.broadcast.send@1.0.0"),
            request,
            context(KitIntegration(client)),
        )
        assert result.status == "error" and result.data is None
        assert result.machine_message == "ZEO_KIT_RESPONSE"
        assert result.metadata["outcome_unknown"] is True
        assert "provider-value" not in str(result)
    else:
        with pytest.raises(KitAPIError) as error:
            client.send_broadcast(request)
        assert error.value.code == "RESPONSE" and error.value.outcome_unknown
        assert str(error.value) == "Kit returned an invalid resource identity"
    assert [r.method for r in calls] == ["GET", "GET", "POST"]
    assert not responses


@pytest.mark.parametrize("record", [{}, {"id": False}, {"id": -1}, {"id": "58"}])
def test_draft_create_requires_strict_identity(
    setup_client: ClientFixture, record: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    responses.append(httpx.Response(201, json={"broadcast": record}))
    with pytest.raises(KitAPIError) as error:
        client.create_broadcast(draft())
    assert error.value.outcome_unknown and len(calls) == 1


@pytest.mark.parametrize(
    "operation",
    ["broadcast_edit", "sequence_pause", "email_publish", "tag_rename", "tag_add"],
)
@pytest.mark.parametrize("valid", [False, True])
def test_mutation_response_binds_the_target_resource(
    setup_client: ClientFixture,
    broadcast: dict[str, Any],
    sequence: dict[str, Any],
    email: dict[str, Any],
    operation: str,
    valid: bool,
) -> None:
    client, calls, responses = setup_client
    if operation == "broadcast_edit":
        responses.extend(
            [
                httpx.Response(200, json={"broadcast": broadcast}),
                httpx.Response(200, json={"broadcast": {"stats": {"status": "draft"}}}),
            ]
        )
        key, expected = "broadcast", 57
        action = partial(
            client.update_broadcast,
            57,
            draft(),
            expected_digest=record_digest(broadcast),
        )
    elif operation == "sequence_pause":
        responses.append(httpx.Response(200, json={"sequence": sequence}))
        key, expected = "sequence", 23
        action = partial(
            client.set_sequence_active,
            23,
            active=False,
            expected_digest=record_digest(sequence),
            confirm=True,
        )
    elif operation == "email_publish":
        queue_snapshot(responses, sequence, email)
        key, expected = "email", 38
        action = partial(
            client.publish_sequence_email,
            23,
            38,
            expected_digest=record_digest(snapshot(sequence, email)),
            published=False,
            confirm=True,
            render_evidence_ref="review",
        )
    elif operation == "tag_rename":
        key, expected = "tag", 7
        action = partial(client.save_tag, "Campaign", tag_id=7)
    else:
        key, expected = "subscriber", 357
        action = partial(
            client.set_tag, 7, 357, remove=False, confirm=True, approval_ref="review"
        )
    responses.append(
        httpx.Response(200, json={key: {"id": expected if valid else 999}})
    )
    if valid:
        assert action().data["id"] == expected
    else:
        with pytest.raises(KitAPIError) as error:
            action()
        assert error.value.code == "RESPONSE" and error.value.outcome_unknown
    assert sum(r.method in {"POST", "PUT"} for r in calls) == 1
    assert not responses
