"""Counterexamples for nullable provider metadata and read/approval separation."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from zeo_core.integrations.kit import KitIntegration, record_digest
from zeo_core.tools import CapabilityRegistry, invoke_sync
from zeo_core.tools.builtin.kit import (
    DeleteRequest,
    ReadRequest,
    SaveBroadcastRequest,
    SaveSequenceRequest,
    register_capabilities,
)

from .conftest import ClientFixture, queue_snapshot, snapshot
from .test_boundary import context
from .test_marketing import draft, seq_draft


def test_hour_sequence_with_null_preview_can_activate(
    setup_client: ClientFixture, sequence: dict[str, Any], email: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    email.update(preview_text=None, delay_unit="hours", delay_value=2)
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
    assert calls[-1].method == "PUT"


def test_snapshot_read_and_edit_capabilities(
    setup_client: ClientFixture, sequence: dict[str, Any], email: dict[str, Any]
) -> None:
    client, _, responses = setup_client
    registry = CapabilityRegistry()
    register_capabilities(registry)
    ctx = context(KitIntegration(client))
    queue_snapshot(responses, sequence, email)
    read = invoke_sync(
        registry.get("kit.marketing.read@1.0.0"),
        ReadRequest(operation="sequence_snapshot", resource_id=23),
        ctx,
    )
    assert read.data is not None and read.data.data == snapshot(sequence, email)
    queue_snapshot(responses, sequence, email)
    responses.append(httpx.Response(200, json={"sequence": sequence}))
    edited = invoke_sync(
        registry.get("kit.marketing.sequence.save@1.0.0"),
        SaveSequenceRequest(
            sequence_id=23,
            draft=seq_draft(),
            expected_digest=record_digest(read.data.data),
        ),
        ctx,
    )
    assert edited.status == "success"


@pytest.mark.parametrize("resource", ["sequence", "sequence_email"])
def test_delete_capability_dispatches_resource(
    setup_client: ClientFixture,
    sequence: dict[str, Any],
    email: dict[str, Any],
    resource: str,
) -> None:
    client, calls, responses = setup_client
    registry = CapabilityRegistry()
    register_capabilities(registry)
    if resource == "sequence_email":
        queue_snapshot(responses, sequence, email)
        digest = record_digest(snapshot(sequence, email))
    else:
        responses.append(httpx.Response(200, json={"sequence": sequence}))
        digest = record_digest(sequence)
    responses.append(httpx.Response(204))
    result = invoke_sync(
        registry.get("kit.marketing.delete@1.0.0"),
        DeleteRequest.model_validate(
            {
                "resource": resource,
                "resource_id": 38 if resource == "sequence_email" else 23,
                "sequence_id": 23,
                "expected_digest": digest,
                "confirm": True,
            }
        ),
        context(KitIntegration(client)),
    )
    assert result.status == "success" and calls[-1].method == "DELETE"


def test_broadcast_edit_capability_and_precondition_error(
    setup_client: ClientFixture, broadcast: dict[str, Any]
) -> None:
    client, _, responses = setup_client
    registry = CapabilityRegistry()
    register_capabilities(registry)
    bound = registry.get("kit.marketing.broadcast.save@1.0.0")
    ctx = context(KitIntegration(client))
    responses.extend(
        [
            httpx.Response(200, json={"broadcast": broadcast}),
            httpx.Response(200, json={"broadcast": {"stats": {"status": "draft"}}}),
            httpx.Response(200, json={"broadcast": broadcast}),
        ]
    )
    result = invoke_sync(
        bound,
        SaveBroadcastRequest(
            broadcast_id=57, expected_digest=record_digest(broadcast), draft=draft()
        ),
        ctx,
    )
    assert result.status == "success"
    responses.append(httpx.Response(200, json={"broadcast": broadcast}))
    result = invoke_sync(
        bound,
        SaveBroadcastRequest(broadcast_id=57, expected_digest="0" * 64, draft=draft()),
        ctx,
    )
    assert result.status == "error" and result.machine_message == "ZEO_KIT_PRECONDITION"
