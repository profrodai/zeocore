"""Steward S1: bind full workflow review to the requested resource before acting."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from zeo_core.integrations.hubspot import (
    EmailSequence,
    HubSpotAPIError,
    HubSpotClient,
    HubSpotIntegration,
    HubSpotTransport,
    SequenceStep,
)
from zeo_core.tools import CapabilityRegistry, ToolContext, invoke_sync
from zeo_core.tools.builtin.hubspot import (
    EnrollmentRequest,
    ReadRequest,
    register_capabilities,
)


@pytest.mark.parametrize(
    "identity",
    [
        {},
        {"id": "999"},
        {"id": 123},
        {"id": True},
        {"id": None},
        {"id": ""},
        {"id": "provider-private/123"},
    ],
)
@pytest.mark.parametrize(
    "operation",
    [
        "read",
        "update",
        "activate",
        "metrics",
        "archive",
        "enroll",
        "capability_read",
        "capability_enroll",
    ],
)
def test_full_workflow_identity_stops_before_followup(
    identity: dict[str, Any], operation: str
) -> None:
    calls: list[httpx.Request] = []
    sequence = EmailSequence(name="Welcome", steps=(SequenceStep(email_id="9"),))
    data = {**sequence.to_api(enabled=True), "revisionId": "7", **identity}

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=data)

    client = HubSpotClient(
        transport=HubSpotTransport(
            SecretStr("test"), transport=httpx.MockTransport(provider)
        )
    )
    try:
        if operation.startswith("capability"):
            registry = CapabilityRegistry()
            register_capabilities(registry)
            ctx = ToolContext(
                run_id="full-workflow-identity",
                tool_name="hubspot",
                tool_version="1.0.0",
                logger=None,
                fs=None,
                work_dir=".",
                output_dir=".",
                services={"hubspot.marketing": HubSpotIntegration(client)},
            )
            if operation == "capability_read":
                result = invoke_sync(
                    registry.get("hubspot.marketing.read@1.0.0"),
                    ReadRequest(operation="workflow", resource_id="123"),
                    ctx,
                )
            else:
                result = invoke_sync(
                    registry.get("hubspot.marketing.workflow.enrollment@1.0.0"),
                    EnrollmentRequest(
                        flow_id="123",
                        email="reader@example.com",
                        revision_id="7",
                        email_versions={"9": "reviewed"},
                        confirm=True,
                    ),
                    ctx,
                )
            assert result.status == "error" and result.data is None
            assert result.machine_message == "ZEO_HUBSPOT_RESPONSE"
            assert result.metadata["outcome_unknown"] is False
            assert "provider-private" not in str(result)
        else:
            with pytest.raises(HubSpotAPIError) as error:
                if operation == "read":
                    client.get_sequence("123")
                elif operation in {"update", "activate"}:
                    client.update_sequence(
                        "123",
                        sequence,
                        revision_id="7",
                        confirm=True,
                        enabled=operation == "activate",
                        email_versions={"9": "reviewed"},
                    )
                elif operation == "metrics":
                    client.sequence_metrics("123")
                elif operation == "archive":
                    client.archive_sequence("123")
                else:
                    client.enroll(
                        "123",
                        "reader@example.com",
                        revision_id="7",
                        email_versions={"9": "reviewed"},
                        confirm=True,
                    )
            assert error.value.code == "RESPONSE" and not error.value.outcome_unknown
            assert str(error.value) == "HubSpot returned an invalid workflow identity"
        assert [(r.method, r.url.path) for r in calls] == [
            ("GET", "/automation/v4/flows/123")
        ]
    finally:
        client.close()
