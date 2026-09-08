"""Adversarial cases requested by the two independent API/design reviewers."""

from __future__ import annotations

import copy
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from zeo_core.integrations.hubspot import (
    Audience,
    EmailContent,
    EmailDraft,
    EmailSequence,
    HubSpotAPIError,
    HubSpotClient,
    HubSpotIntegration,
    HubSpotTransport,
    PageRequest,
    PublishRequest,
    SequenceStep,
    SubscriptionChange,
    send_spec_digest,
)
from zeo_core.integrations.hubspot.client import AssetType
from zeo_core.tools import CapabilityRegistry, ToolContext, invoke_sync
from zeo_core.tools.builtin.hubspot import EmailIdRequest, register_capabilities

REV = "2026-09-07T10:00:00Z"


def draft_data(*, lists: bool = False) -> dict[str, Any]:
    draft = EmailDraft(
        name="Reviewed issue",
        subject="Approved subject",
        content=EmailContent(
            template_path="email/test.html", plain_text="Approved body"
        ),
        from_name="Editor",
        from_email="editor@example.com",
        subscription_id="1",
        office_location_id="2",
        audience=Audience(list_ids=("7",)) if lists else Audience(contact_ids=("42",)),
    )
    return {
        **draft.to_api(),
        "id": "123",
        "updatedAt": REV,
        "type": "BATCH_EMAIL",
        "isPublished": False,
        "isTransactional": False,
    }


def approval(
    data: dict[str, Any], *, dynamic: bool = False, send_at: datetime | None = None
) -> PublishRequest:
    return PublishRequest(
        email_id="123",
        expected_updated_at=REV,
        subscription_id="1",
        expected_send_spec_sha256=send_spec_digest(
            data,
            send_at=send_at,
            audience_mode="dynamic_segments" if dynamic else "fixed_contacts",
        ),
        render_evidence_ref="review/actual-test-render",
        confirm=True,
        send_at=send_at,
        audience=Audience(list_ids=("7",))
        if dynamic
        else Audience(contact_ids=("42",)),
        audience_mode="dynamic_segments" if dynamic else "fixed_contacts",
        audience_policy_ref="approvals/dynamic-no-recipient-cap" if dynamic else None,
    )


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> HubSpotClient:
    return HubSpotClient(
        transport=HubSpotTransport(
            SecretStr("test-token"), transport=httpx.MockTransport(handler)
        )
    )


def flow() -> dict[str, Any]:
    return {
        **EmailSequence(
            name="Welcome",
            steps=(SequenceStep(email_id="9"),),
            suppression_list_ids=(11,),
        ).to_api(enabled=True),
        "id": "456",
        "revisionId": "7",
        "description": "Preserve this description",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"enrollmentCriteria": {"type": "EVENT_BASED", "shouldReEnroll": False}},
        {"enrollmentCriteria": {"type": "MANUAL", "shouldReEnroll": True}},
        {
            "enrollmentCriteria": {
                "type": "MANUAL",
                "shouldReEnroll": False,
                "trigger": {},
            }
        },
        {"enrollmentSchedule": {"type": "DAILY"}},
        {"canEnrollFromSalesforce": True},
        {"timeWindows": [{"day": "MONDAY"}]},
        {"goalFilterBranch": {}},
        {"unEnrollmentSetting": {}},
        {"startActionId": "999"},
        {"objectTypeId": "0-2"},
        {"suppressionListIds": [11, 11]},
    ],
)
@pytest.mark.parametrize("operation", ["activate", "enroll", "pause"])
def test_unsupported_provider_settings_refuse_before_effect(
    change: dict[str, Any],
    operation: str,
) -> None:
    calls: list[httpx.Request] = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={**flow(), **change})

    client = client_for(provider)
    try:
        with pytest.raises(ValueError):
            if operation == "enroll":
                client.enroll(
                    "456",
                    "reader@example.com",
                    revision_id="7",
                    email_versions={"9": REV},
                    confirm=True,
                )
            else:
                client.update_sequence(
                    "456",
                    EmailSequence(name="New", steps=(SequenceStep(email_id="9"),)),
                    revision_id="7",
                    email_versions={"9": REV},
                    enabled=operation == "activate",
                    confirm=True,
                )
        assert len(calls) == 1 and calls[0].method == "GET"
    finally:
        client.close()


@pytest.mark.parametrize(
    "alteration", ["crm", "version", "branch", "loop", "duplicate", "email"]
)
def test_changed_action_or_email_reference_refuses_enrollment(alteration: str) -> None:
    data = flow()
    action = data["actions"][0]
    if alteration == "crm":
        action["actionTypeId"] = "0-14"
    elif alteration == "version":
        action["actionTypeVersion"] = 1
    elif alteration == "branch":
        action["type"] = "STATIC_BRANCH"
    elif alteration == "loop":
        action["connection"] = {"edgeType": "STANDARD", "nextActionId": "1"}
    elif alteration == "duplicate":
        data["actions"].append(copy.deepcopy(action))
    else:
        action["fields"]["content_id"] = "10"
    calls: list[str] = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(200, json=data)

    client = client_for(provider)
    try:
        with pytest.raises(ValueError):
            client.enroll(
                "456",
                "reader@example.com",
                revision_id="7",
                email_versions={"9": REV},
                confirm=True,
            )
        assert calls == ["GET"]
    finally:
        client.close()


@pytest.mark.parametrize("target", ["revision", "email_revision"])
def test_workflow_and_referenced_email_revisions_are_bound(target: str) -> None:
    calls: list[str] = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if "/flows/" in request.url.path:
            return httpx.Response(
                200, json={**flow(), "revisionId": "8" if target == "revision" else "7"}
            )
        return httpx.Response(
            200,
            json={
                "type": "AUTOMATED_EMAIL",
                "isPublished": True,
                "isTransactional": False,
                "updatedAt": "changed",
            },
        )

    client = client_for(provider)
    try:
        with pytest.raises(ValueError):
            client.enroll(
                "456",
                "reader@example.com",
                revision_id="7",
                email_versions={"9": REV},
                confirm=True,
            )
        assert calls == (["GET"] if target == "revision" else ["GET", "GET"])
    finally:
        client.close()


def test_pause_preserves_supported_metadata_and_definition() -> None:
    data = flow()
    calls: list[httpx.Request] = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=data if request.method == "GET" else {})

    client = client_for(provider)
    try:
        client.update_sequence(
            "456",
            EmailSequence(
                name="Welcome",
                steps=(SequenceStep(email_id="9"),),
                suppression_list_ids=(11,),
            ),
            revision_id="7",
        )
        body = json.loads(calls[-1].content)
        assert body["actions"] == data["actions"]
        assert body["suppressionListIds"] == [11]
        assert body["description"] == data["description"]
        assert body["isEnabled"] is False
    finally:
        client.close()


def test_dynamic_membership_requires_explicit_unbounded_policy() -> None:
    data = draft_data(lists=True)
    with pytest.raises(ValidationError, match="dynamic audience"):
        PublishRequest(
            email_id="123",
            expected_updated_at=REV,
            subscription_id="1",
            audience=Audience(list_ids=("7",)),
            confirm=True,
            expected_send_spec_sha256="0" * 64,
            render_evidence_ref="review/1",
        )
    request = approval(data, dynamic=True)
    # Membership changes without changing the draft/list ID. The policy explicitly
    # permits provider-evaluated membership with no enforceable recipient cap.
    membership = ["42"]
    membership.extend(str(i) for i in range(100, 10000))
    sent: list[str] = []

    def provider(req: httpx.Request) -> httpx.Response:
        if req.method == "PATCH":
            data.update(json.loads(req.content))
        if req.method == "POST":
            sent.extend(membership)
            return httpx.Response(204)
        return httpx.Response(200, json=data)

    client = client_for(provider)
    try:
        client.publish_email(request)
        assert sent == membership and len(sent) > 100
    finally:
        client.close()


@pytest.mark.parametrize(
    "changed_field",
    ["subject", "from", "content", "subscriptionDetails", "businessUnitId"],
)
def test_complete_send_spec_rejects_tamper_even_with_same_timestamp(
    changed_field: str,
) -> None:
    data = draft_data()
    request = approval(data)
    data[changed_field] = "tampered"
    calls: list[str] = []

    def provider(req: httpx.Request) -> httpx.Response:
        calls.append(req.method)
        return httpx.Response(200, json=data)

    client = client_for(provider)
    try:
        with pytest.raises(ValueError):
            client.publish_email(request)
        assert calls == ["GET"]
    finally:
        client.close()


def test_change_between_preflight_and_configuration_read_refuses_publish() -> None:
    data = draft_data()
    request = approval(data)
    calls: list[str] = []

    def provider(req: httpx.Request) -> httpx.Response:
        calls.append(req.method)
        if req.method == "PATCH":
            data.update(json.loads(req.content))
            data["subject"] = "Concurrent dashboard edit"
        return httpx.Response(200, json=data)

    client = client_for(provider)
    try:
        with pytest.raises(ValueError, match="during send configuration"):
            client.publish_email(request)
        assert calls == ["GET", "PATCH", "GET"]
    finally:
        client.close()


def test_edit_after_final_read_demonstrates_residual_provider_race() -> None:
    data = draft_data()
    request = approval(data)
    sent: list[str] = []

    def provider(req: httpx.Request) -> httpx.Response:
        if req.method == "PATCH":
            data.update(json.loads(req.content))
        if req.method == "POST":
            # A privileged provider editor wins after every local check. This is
            # deliberately an observed LIMITATION, never a safety PASS.
            data["subject"] = "Edit after final GET"
            sent.append(data["subject"])
            return httpx.Response(204)
        return httpx.Response(200, json=data)

    client = client_for(provider)
    try:
        assert client.publish_email(request).data == {}
        assert sent == ["Edit after final GET"]
    finally:
        client.close()


def test_unsubscribe_refusal_never_repairs_consent() -> None:
    data = draft_data()
    request = approval(data)
    paths: list[str] = []

    def provider(req: httpx.Request) -> httpx.Response:
        paths.append(req.url.path)
        if req.method == "PATCH":
            data.update(json.loads(req.content))
        return (
            httpx.Response(403, json={"message": "Unsubscribed"})
            if req.method == "POST"
            else httpx.Response(200, json=data)
        )

    client = client_for(provider)
    try:
        with pytest.raises(HubSpotAPIError):
            client.publish_email(request)
        assert len(paths) == 4
        assert not any("communication-preferences" in path for path in paths)
    finally:
        client.close()


def test_consent_requires_independent_reference_and_does_not_send_it_to_provider() -> (
    None
):
    fields: dict[str, Any] = {
        "email": "reader@example.com",
        "subscription_id": 1,
        "status": "SUBSCRIBED",
        "legal_basis": "CONSENT_WITH_NOTICE",
        "legal_basis_explanation": "Reader opted in",
    }
    with pytest.raises(ValidationError):
        SubscriptionChange(**fields)
    result = SubscriptionChange(**fields, consent_evidence_ref="consent/record-1")
    assert "consent_evidence_ref" not in result.to_api()


def test_lost_cancel_response_remains_unknown_after_local_connection_close() -> None:
    data = draft_data()
    request = approval(data, send_at=datetime.now(UTC) + timedelta(days=1))

    def provider(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/unpublish"):
            raise httpx.ReadTimeout("response lost")
        if req.method == "PATCH":
            data.update(json.loads(req.content))
        return (
            httpx.Response(204)
            if req.method == "POST"
            else httpx.Response(200, json=data)
        )

    client = client_for(provider)
    client.publish_email(request)
    integration = HubSpotIntegration(client)
    registry = CapabilityRegistry()
    register_capabilities(registry)
    ctx = ToolContext(
        run_id="cancel",
        tool_name="hubspot",
        tool_version="1.0.0",
        logger=None,
        fs=None,
        work_dir=".",
        output_dir=".",
        services={"hubspot.marketing": integration},
    )
    result = invoke_sync(
        registry.get("hubspot.marketing.email.cancel@1.0.0"),
        EmailIdRequest(email_id="123"),
        ctx,
    )
    integration.close()  # Local credential access removed; not provider cancellation.
    assert result.data is None
    assert result.metadata["outcome_unknown"] is True


def test_path_pii_not_in_standard_http_logs(caplog: pytest.LogCaptureFixture) -> None:
    address = "private-reader@example.com"

    def provider(req: httpx.Request) -> httpx.Response:
        logging.getLogger("httpcore.http11").debug("request %s", req.url)
        return httpx.Response(200, json={})

    client = client_for(provider)
    try:
        with caplog.at_level(logging.DEBUG):
            client.subscription_status(address)
            logging.getLogger("httpx").info("unrelated request still logged")
        assert address not in caplog.text and "private-reader%40" not in caplog.text
        assert "unrelated request still logged" in caplog.text
    finally:
        client.close()


def test_incomplete_page_never_proves_absence() -> None:
    client = client_for(
        lambda req: httpx.Response(
            200, json={"results": [], "paging": {"next": {"after": "next"}}}
        )
    )
    try:
        page = client.list_emails()
        assert not page.complete and page.next_after == "next"
    finally:
        client.close()
    client = client_for(lambda req: httpx.Response(200, json={"results": []}))
    try:
        assert client.list_emails().complete
        assert not client.list_emails(PageRequest(after="previous")).complete
    finally:
        client.close()


@pytest.mark.parametrize(
    "asset_type", ["MARKETING_EMAIL", "AUTOMATION_PLATFORM_FLOW", "OBJECT_LIST"]
)
def test_documented_marketing_asset_types(asset_type: str) -> None:
    paths: list[str] = []

    def provider(req: httpx.Request) -> httpx.Response:
        paths.append(req.url.path)
        return httpx.Response(204)

    client = client_for(provider)
    try:
        client.associate_asset("campaign", cast(AssetType, asset_type), "123")
        assert paths == [
            f"/marketing/campaigns/2026-03/campaign/assets/{asset_type}/123"
        ]
        for unsupported in ("EMAIL", "WORKFLOW", "SEQUENCE"):
            with pytest.raises(ValueError):
                client.associate_asset("campaign", cast(AssetType, unsupported), "123")
        assert len(paths) == 1
    finally:
        client.close()
