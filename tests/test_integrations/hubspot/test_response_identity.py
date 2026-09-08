"""Elder review: never bind one workflow's revision to another workflow's removal."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from zeo_core.integrations.hubspot import (
    HubSpotAPIError,
    HubSpotClient,
    HubSpotIntegration,
    HubSpotTransport,
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
    "operation", ["identity", "remove", "capability_identity", "capability_remove"]
)
def test_wrong_workflow_identity_stops_before_mapping(
    identity: dict[str, Any], operation: str
) -> None:
    calls: list[httpx.Request] = []
    data = {
        "type": "CONTACT_FLOW",
        "objectTypeId": "0-1",
        "flowType": "WORKFLOW",
        "revisionId": "7",
        **identity,
    }

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
                run_id="identity-review",
                tool_name="hubspot",
                tool_version="1.0.0",
                logger=None,
                fs=None,
                work_dir=".",
                output_dir=".",
                services={"hubspot.marketing": HubSpotIntegration(client)},
            )
            if operation == "capability_identity":
                result = invoke_sync(
                    registry.get("hubspot.marketing.read@1.0.0"),
                    ReadRequest(operation="workflow_identity", resource_id="123"),
                    ctx,
                )
            else:
                result = invoke_sync(
                    registry.get("hubspot.marketing.workflow.enrollment@1.0.0"),
                    EnrollmentRequest(
                        flow_id="123",
                        email="reader@example.com",
                        revision_id="7",
                        remove=True,
                    ),
                    ctx,
                )
            assert result.status == "error" and result.data is None
            assert result.machine_message == "ZEO_HUBSPOT_RESPONSE"
            assert result.metadata["outcome_unknown"] is False
            assert "provider-private" not in str(result)
        else:
            with pytest.raises(HubSpotAPIError) as error:
                if operation == "identity":
                    client.get_workflow_identity("123")
                else:
                    client.enroll(
                        "123", "reader@example.com", revision_id="7", remove=True
                    )
            assert error.value.code == "RESPONSE" and not error.value.outcome_unknown
            assert str(error.value) == "HubSpot returned an invalid workflow identity"
        assert [(r.method, r.url.path) for r in calls] == [
            ("GET", "/automation/v4/flows/123")
        ]
    finally:
        client.close()


def test_correct_workflow_identity_allows_removal_despite_graph_drift() -> None:
    calls: list[httpx.Request] = []
    data: dict[str, Any] = {
        "id": "123",
        "type": "CONTACT_FLOW",
        "objectTypeId": "0-1",
        "flowType": "WORKFLOW",
        "revisionId": "7",
        "actions": [{"unknown": True}],
        "enrollmentCriteria": {"type": "EVENT_BASED"},
    }
    responses = [
        httpx.Response(200, json=data),
        httpx.Response(200, json={"results": [{"flowId": 123, "workflowId": 456}]}),
        httpx.Response(204),
    ]

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses.pop(0)

    client = HubSpotClient(
        transport=HubSpotTransport(
            SecretStr("test"), transport=httpx.MockTransport(provider)
        )
    )
    try:
        assert (
            client.enroll(
                "123", "reader@example.com", revision_id="7", remove=True
            ).data
            == {}
        )
        assert [r.method for r in calls] == ["GET", "POST", "DELETE"]
        assert calls[-1].url.path.startswith("/automation/v2/workflows/456/")
    finally:
        client.close()
