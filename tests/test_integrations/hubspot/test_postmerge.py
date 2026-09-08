"""Regression proofs for Steward post-merge findings N1-N3."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from zeo_core.integrations.hubspot import (
    Audience,
    EmailContent,
    EmailDraft,
    EmailSequence,
    HubSpotClient,
    HubSpotTransport,
    PublishRequest,
    SequenceStep,
    send_spec_digest,
)


def workflow() -> dict[str, Any]:
    return {
        **EmailSequence(name="Test", steps=(SequenceStep(email_id="9"),)).to_api(),
        "revisionId": "7",
        "id": "456",
    }


@pytest.mark.parametrize(
    "optional",
    ["enrollmentSchedule", "eventAnchor", "goalFilterBranch", "unEnrollmentSetting"],
)
def test_null_optional_response_fields_are_inert(optional: str) -> None:
    data = workflow()
    data[optional] = None
    data["actions"][0]["connection"] = None
    data["actions"][0]["providerDecoration"] = None
    client = HubSpotClient(
        transport=HubSpotTransport(
            SecretStr("test"),
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=data)),
        )
    )
    try:
        assert client.get_sequence("456").data == data
        assert optional in data  # Validation never mutates provider records.
        data[optional] = {}
        with pytest.raises(ValueError):
            client.get_sequence("456")
        data[optional] = None
        data["actions"][0]["providerDecoration"] = {"unknown": True}
        with pytest.raises(ValueError):
            client.get_sequence("456")
    finally:
        client.close()


@pytest.mark.parametrize(
    "change",
    [{}, {"revisionId": "8"}, {"type": "COMPANY_FLOW"}, {"objectTypeId": "0-2"}],
)
def test_unenrollment_ignores_graph_drift_but_binds_identity_and_revision(
    change: dict[str, Any],
) -> None:
    data = {**workflow(), **change}
    data["actions"][0]["actionTypeId"] = "0-14"
    data["enrollmentCriteria"] = {"type": "EVENT_BASED"}
    calls: list[str] = []
    responses = [
        httpx.Response(200, json=data),
        httpx.Response(200, json={"results": [{"flowId": 456, "workflowId": 99}]}),
        httpx.Response(204),
    ]

    def provider(req: httpx.Request) -> httpx.Response:
        calls.append(req.method)
        return responses.pop(0)

    client = HubSpotClient(
        transport=HubSpotTransport(
            SecretStr("test"), transport=httpx.MockTransport(provider)
        )
    )
    try:
        if change:
            with pytest.raises(ValueError):
                client.enroll("456", "reader@example.com", revision_id="7", remove=True)
            assert calls == ["GET"]
        else:
            assert (
                client.enroll(
                    "456", "reader@example.com", revision_id="7", remove=True
                ).data
                == {}
            )
            assert calls == ["GET", "POST", "DELETE"]
    finally:
        client.close()


def test_direct_client_malformed_schedule_error_never_echoes_provider_bytes() -> None:
    draft = EmailDraft(
        name="Issue",
        subject="Reviewed",
        content=EmailContent(template_path="test.html", plain_text="News"),
        from_name="Editor",
        from_email="editor@example.com",
        subscription_id="1",
        office_location_id="2",
        audience=Audience(contact_ids=("42",)),
    )
    data = {
        **draft.to_api(),
        "id": "123",
        "updatedAt": "rev",
        "type": "BATCH_EMAIL",
        "isPublished": False,
        "isTransactional": False,
    }
    when = datetime.now(UTC) + timedelta(days=1)
    marker = "private-provider-bytes"
    changed = {**data, "publishDate": marker, "sendOnPublish": False}
    responses = [
        httpx.Response(200, json=data),
        httpx.Response(200, json={}),
        httpx.Response(200, json=changed),
    ]
    client = HubSpotClient(
        transport=HubSpotTransport(
            SecretStr("test"),
            transport=httpx.MockTransport(lambda req: responses.pop(0)),
        )
    )
    try:
        with pytest.raises(ValueError) as error:
            client.publish_email(
                PublishRequest(
                    email_id="123",
                    expected_updated_at="rev",
                    expected_send_spec_sha256=send_spec_digest(data, send_at=when),
                    render_evidence_ref="review/1",
                    audience=draft.audience,
                    subscription_id="1",
                    send_at=when,
                    confirm=True,
                )
            )
        assert str(error.value) == "Provider schedule is invalid"
        assert marker not in str(error.value)
        assert not responses
    finally:
        client.close()
