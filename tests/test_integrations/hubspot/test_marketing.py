"""Behavioral proof through the HTTP boundary; no live provider claims."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, SecretStr, ValidationError

from zeo_core.adapters.llm_tools import project_openai_tool
from zeo_core.contracts import EffectKind
from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.hubspot import (
    Audience,
    CampaignProperties,
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
from zeo_core.tools import CapabilityRegistry, ToolContext, invoke_sync
from zeo_core.tools.builtin.hubspot import (
    ArchiveRequest,
    AssetRequest,
    CampaignRequest,
    CloneRequest,
    EmailIdRequest,
    EnrollmentRequest,
    ReadRequest,
    SaveEmailRequest,
    SequenceRequest,
    register_capabilities,
)

CANARY = "hubspot-test-secret-must-not-escape"
API_CONTRACT = json.loads(Path(__file__).with_name("api_contract.json").read_text())
REVISION = "2026-09-07T10:00:00Z"
ClientFixture = tuple[
    HubSpotClient, list[httpx.Request], list[httpx.Response | Exception]
]


@pytest.fixture
def draft() -> EmailDraft:
    return EmailDraft(
        name="Weekly",
        subject="This week",
        content=EmailContent(
            template_path="email/custom.html",
            plain_text="The news",
            widgets={"body": {"body": {"html": "<p>The news</p>"}}},
        ),
        from_name="Editor",
        from_email="editor@example.com",
        subscription_id="5",
        office_location_id="6",
        audience=Audience(contact_ids=("42",), list_ids=("7",)),
    )


def email_data(draft: EmailDraft) -> dict[str, Any]:
    return {
        **draft.to_api(),
        "id": "123",
        "type": "BATCH_EMAIL",
        "updatedAt": REVISION,
        "isPublished": False,
        "isTransactional": False,
    }


def sequence() -> EmailSequence:
    return EmailSequence(
        name="Welcome",
        steps=(
            SequenceStep(email_id="1"),
            SequenceStep(email_id="2", delay_minutes=1440),
        ),
    )


@pytest.fixture
def setup_client() -> Iterator[
    tuple[HubSpotClient, list[httpx.Request], list[httpx.Response | Exception]]
]:
    calls: list[httpx.Request] = []
    responses: list[httpx.Response | Exception] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "api.hubapi.com"
        assert request.headers["Authorization"] == "Bearer " + CANARY
        assert_wire_schema(request)
        assert responses, f"Unexpected extra request {request.method}"
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    client = HubSpotClient(
        transport=HubSpotTransport(
            SecretStr(CANARY), transport=httpx.MockTransport(handler)
        )
    )
    yield client, calls, responses
    client.close()


def assert_wire_schema(request: httpx.Request) -> None:
    """Compare against upstream fields, not a baseline produced by our client."""
    path = request.url.path
    schema_key: tuple[str, str] | None = None
    if path == "/marketing/emails/2026-03" and request.method == "POST":
        schema_key = ("marketingEmails", "EmailCreateRequest")
    elif path.startswith("/marketing/emails/2026-03/") and request.method == "PATCH":
        schema_key = ("marketingEmails", "EmailUpdateRequest")
    elif path == "/automation/v4/flows" and request.method == "POST":
        schema_key = ("automationV4", "ApiContactFlowCreateRequest")
    elif path.startswith("/automation/v4/flows/") and request.method == "PUT":
        schema_key = ("automationV4", "ApiContactFlowPutRequest")
    elif (
        path.startswith("/communication-preferences/2026-03/statuses/")
        and request.method == "POST"
    ):
        schema_key = ("subscriptions", "PartialPublicStatusRequest")
    if schema_key:
        family, name = schema_key
        schema = API_CONTRACT["contracts"][family]["schemas"][name]
        body = json.loads(request.content)
        assert set(schema["required"]) <= body.keys()
        assert body.keys() <= set(schema["fields"])
    if path.endswith(("/publish", "/unpublish")):
        assert not request.content


def test_capability_tool_projections_are_usable() -> None:
    registry = CapabilityRegistry()
    register_capabilities(registry)
    manifests = list(registry.manifests())
    assert len(manifests) == 11
    for manifest in manifests:
        projection = project_openai_tool(manifest)
        assert projection.ok, projection.incompatibility


def test_publish_response_contract_has_no_delivery_body() -> None:
    path = "/marketing/emails/2026-03/{emailId}/publish"
    assert API_CONTRACT["contracts"]["marketingEmails"]["paths"][path]["post"][
        "success_codes"
    ] == ["204"]


def test_sequence_activation_and_pause_through_capability(
    setup_client: ClientFixture,
) -> None:
    client, calls, responses = setup_client
    spec = sequence()
    responses.extend(
        [
            httpx.Response(200, json={**spec.to_api(), "revisionId": "7"}),
            httpx.Response(
                200,
                json={
                    "type": "AUTOMATED_EMAIL",
                    "updatedAt": REVISION,
                    "isPublished": True,
                    "isTransactional": False,
                },
            ),
            httpx.Response(
                200,
                json={
                    "type": "AUTOMATED_EMAIL",
                    "updatedAt": REVISION,
                    "isPublished": True,
                    "isTransactional": False,
                },
            ),
            httpx.Response(200, json={"id": "456", "isEnabled": True}),
        ]
    )
    registry = CapabilityRegistry()
    register_capabilities(registry)
    result = invoke_sync(
        registry.get("hubspot.marketing.workflow.save@1.0.0"),
        SequenceRequest(
            sequence=spec,
            flow_id="456",
            revision_id="7",
            enabled=True,
            confirm=True,
            email_versions={"1": REVISION, "2": REVISION},
        ),
        context(client),
    )
    assert result.data and result.data.data["isEnabled"] is True
    assert [call.method for call in calls] == ["GET", "GET", "GET", "PUT"]


def test_sequence_enrollment_capability_and_unenrollment(
    setup_client: ClientFixture,
) -> None:
    client, calls, responses = setup_client
    registry = CapabilityRegistry()
    register_capabilities(registry)
    for remove in (False, True):
        responses.extend(
            [
                httpx.Response(
                    200,
                    json={
                        **sequence().to_api(enabled=True),
                        "revisionId": "7",
                        "id": "456",
                    },
                ),
                *(
                    []
                    if remove
                    else [
                        httpx.Response(
                            200,
                            json={
                                "type": "AUTOMATED_EMAIL",
                                "isPublished": True,
                                "isTransactional": False,
                                "updatedAt": REVISION,
                            },
                        ),
                        httpx.Response(
                            200,
                            json={
                                "type": "AUTOMATED_EMAIL",
                                "isPublished": True,
                                "isTransactional": False,
                                "updatedAt": REVISION,
                            },
                        ),
                    ]
                ),
                httpx.Response(
                    200, json={"results": [{"flowId": 456, "workflowId": 99}]}
                ),
                httpx.Response(204),
            ]
        )
        result = invoke_sync(
            registry.get("hubspot.marketing.workflow.enrollment@1.0.0"),
            EnrollmentRequest(
                flow_id="456",
                email="reader@example.com",
                remove=remove,
                confirm=True,
                revision_id="7",
                email_versions={"1": REVISION, "2": REVISION},
            ),
            context(client),
        )
        assert result.data is not None
        assert calls[-1].method == ("DELETE" if remove else "POST")


def test_integration_entry_point_and_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from importlib.metadata import entry_points

    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN", raising=False)
    matches = list(
        entry_points(group="zeo_core.integrations", name="hubspot.marketing")
    )
    assert len(matches) == 1
    service = matches[0].load()()
    assert isinstance(service, IntegrationProtocol)
    assert not service.initialize().success


def test_email_draft_request(setup_client: ClientFixture, draft: EmailDraft) -> None:
    client, calls, responses = setup_client
    responses.append(httpx.Response(201, json={"id": "123"}))
    assert client.create_email(draft).data["id"] == "123"
    req = calls[0]
    assert (req.method, req.url.path) == ("POST", "/marketing/emails/2026-03")
    body = json.loads(req.content)
    assert body["content"]["templatePath"] == "email/custom.html"
    assert body["content"]["widgets"]["body"]["body"]["html"] == "<p>The news</p>"
    assert (
        "templatePath" not in body
    )  # Guide prose differs from the actual v2026-03 schema.
    assert "type" not in body  # Derived/read-only provider field.
    assert body["state"] == "DRAFT"
    assert body["sendOnPublish"] is False
    assert body["subscriptionDetails"] == {
        "subscriptionId": "5",
        "officeLocationId": "6",
    }
    assert body["to"]["contactIlsLists"]["include"] == ["7"]
    assert body["to"]["suppressGraymail"] is True
    assert body["from"] == {"fromName": "Editor", "replyTo": "editor@example.com"}


@pytest.mark.parametrize("scheduled", [False, True])
def test_publish_preflight_then_schedule_and_publish(
    setup_client: ClientFixture, draft: EmailDraft, scheduled: bool
) -> None:
    client, calls, responses = setup_client
    send_at = datetime.now(UTC) + timedelta(days=1) if scheduled else None
    configured = {**email_data(draft), "sendOnPublish": not scheduled}
    if send_at:
        configured["publishDate"] = send_at.isoformat()
    responses.extend(
        [
            httpx.Response(200, json=email_data(draft)),
            httpx.Response(200, json={"id": "123"}),
            httpx.Response(200, json=configured),
            httpx.Response(204),
        ]
    )
    request = PublishRequest(
        email_id="123",
        expected_updated_at=REVISION,
        expected_send_spec_sha256=send_spec_digest(
            email_data(draft), send_at=send_at, audience_mode="dynamic_segments"
        ),
        render_evidence_ref="reviews/render-1",
        audience_mode="dynamic_segments",
        audience_policy_ref="reviews/dynamic-audience-1",
        audience=draft.audience,
        subscription_id="5",
        send_at=send_at,
        confirm=True,
    )
    result = client.publish_email(request)
    assert result.data == {}  # API acceptance has no delivery-state body.
    assert [r.method for r in calls] == ["GET", "PATCH", "GET", "POST"]
    assert calls[-1].url.path == "/marketing/emails/2026-03/123/publish"
    assert calls[-1].content == b""
    body = json.loads(calls[1].content)
    assert body["sendOnPublish"] is (not scheduled)
    if send_at:
        assert datetime.fromisoformat(body["publishDate"]) == send_at
    else:
        assert "publishDate" not in body


@pytest.mark.parametrize(
    "changed",
    [
        {"updatedAt": "new-revision"},
        {"isPublished": True},
        {"state": "SCHEDULED"},
        {"isTransactional": True},
        {"type": "SINGLE_SEND_API"},
        {"subscriptionDetails": {"subscriptionId": "another"}},
        {"to": {}},
        {"to": {"contactIds": {"include": ["another"]}}},
    ],
)
def test_publish_refuses_stale_or_wrong_target(
    setup_client: ClientFixture, draft: EmailDraft, changed: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    responses.append(httpx.Response(200, json={**email_data(draft), **changed}))
    with pytest.raises(ValueError):
        client.publish_email(
            PublishRequest(
                email_id="123",
                expected_updated_at=REVISION,
                expected_send_spec_sha256=send_spec_digest(
                    email_data(draft), audience_mode="dynamic_segments"
                ),
                render_evidence_ref="reviews/render-1",
                audience_mode="dynamic_segments",
                audience_policy_ref="reviews/dynamic-audience-1",
                audience=draft.audience,
                subscription_id="5",
                confirm=True,
            )
        )
    assert len(calls) == 1


def test_publish_requires_confirmation_before_network(
    setup_client: ClientFixture, draft: EmailDraft
) -> None:
    client, calls, _ = setup_client
    with pytest.raises(ValueError, match="confirmation"):
        client.publish_email(
            PublishRequest(
                email_id="123",
                expected_updated_at=REVISION,
                expected_send_spec_sha256=send_spec_digest(
                    email_data(draft), audience_mode="dynamic_segments"
                ),
                render_evidence_ref="reviews/render-1",
                audience_mode="dynamic_segments",
                audience_policy_ref="reviews/dynamic-audience-1",
                audience=draft.audience,
                subscription_id="5",
            )
        )
    assert not calls


@pytest.mark.parametrize(
    "kwargs",
    [
        {"contact_ids": ("1", "1")},
        {"contact_ids": ("1",), "exclude_contact_ids": ("1",)},
        {"list_ids": ("1",), "exclude_list_ids": ("1",)},
        {"contact_ids": ("../deals",)},
    ],
)
def test_audience_rejects_ambiguous_input(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Audience(**kwargs)


def test_empty_draft_audience_is_allowed_but_send_is_not() -> None:
    assert not Audience().contact_ids
    with pytest.raises(ValidationError):
        PublishRequest(
            email_id="1",
            expected_updated_at=REVISION,
            subscription_id="5",
            expected_send_spec_sha256="0" * 64,
            render_evidence_ref="review/test",
        )


@pytest.mark.parametrize(
    "send_at", [datetime(2027, 1, 1), datetime(2000, 1, 1, tzinfo=UTC)]
)
def test_invalid_schedule(send_at: datetime) -> None:
    with pytest.raises(ValidationError):
        PublishRequest(
            email_id="1",
            expected_updated_at=REVISION,
            subscription_id="5",
            expected_send_spec_sha256="0" * 64,
            render_evidence_ref="review/test",
            audience=Audience(contact_ids=("2",)),
            send_at=send_at,
        )


def test_paging_uses_cursor_not_provider_link(setup_client: ClientFixture) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [
            httpx.Response(
                200,
                json={
                    "results": [{"id": "1"}],
                    "paging": {
                        "next": {
                            "after": "next+token",
                            "link": "https://evil.example/steal",
                        }
                    },
                },
            ),
            httpx.Response(200, json={"results": []}),
        ]
    )
    first = client.list_emails(PageRequest(limit=1))
    second = client.list_emails(PageRequest(limit=1, after=first.next_after))
    assert first.next_after == "next+token"
    assert not second.results and second.next_after is None
    assert calls[1].url.params["after"] == "next+token"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"results": [1]},
        {"results": [], "paging": []},
        {"results": [], "paging": {"next": []}},
        {"results": [], "paging": {"next": {"link": "https://evil.example/next"}}},
        {"results": [], "paging": {"next": {"after": "x" * 2049}}},
        {"results": [{"id": str(i)} for i in range(101)]},
        {"results": [], "paging": {"next": {"after": "same"}}},
    ],
)
def test_malformed_pages_fail_closed(
    setup_client: ClientFixture, payload: dict[str, Any]
) -> None:
    client, _, responses = setup_client
    responses.append(httpx.Response(200, json=payload))
    with pytest.raises(HubSpotAPIError):
        client.list_campaigns(PageRequest(after="same"))


@pytest.mark.parametrize(
    "status,code,unknown",
    [
        (401, "AUTHENTICATION", False),
        (403, "ACCESS", False),
        (404, "NOT_FOUND", False),
        (429, "RATE_LIMIT", False),
        (503, "HTTP", True),
        (302, "HTTP", False),
    ],
)
def test_errors_do_not_leak_or_retry(
    setup_client: ClientFixture,
    draft: EmailDraft,
    status: int,
    code: str,
    unknown: bool,
) -> None:
    client, calls, responses = setup_client
    responses.append(
        httpx.Response(
            status,
            json={"message": CANARY},
            headers={"Retry-After": "12", "Location": "https://evil.example"},
        )
    )
    with pytest.raises(HubSpotAPIError) as error:
        client.create_email(draft)
    assert error.value.code == code and error.value.outcome_unknown is unknown
    assert CANARY not in str(error.value) + repr(error.value.__dict__)
    assert error.value.retry_after_seconds == 12
    assert len(calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.ReadTimeout(CANARY),
        httpx.Response(200, text=CANARY),
        httpx.Response(200, json=[CANARY]),
    ],
)
def test_ambiguous_mutation_is_not_replayed(
    setup_client: ClientFixture, draft: EmailDraft, response: httpx.Response | Exception
) -> None:
    client, calls, responses = setup_client
    responses.append(response)
    with pytest.raises(HubSpotAPIError) as error:
        client.create_email(draft)
    assert error.value.outcome_unknown
    assert CANARY not in str(error.value)
    assert len(calls) == 1


def test_campaign_routes_and_subscription_contract(setup_client: ClientFixture) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [
            httpx.Response(201, json={"id": "campaign-1"}),
            httpx.Response(200, json={}),
            httpx.Response(204),
            httpx.Response(204),
            httpx.Response(200, json={}),
            httpx.Response(200, json={}),
        ]
    )
    client.create_campaign(CampaignProperties(properties={"hs_name": "Launch"}))
    client.update_campaign(
        "campaign-1", CampaignProperties(properties={"hs_name": "New"})
    )
    client.associate_asset("campaign-1", "MARKETING_EMAIL", "123")
    client.associate_asset("campaign-1", "MARKETING_EMAIL", "123", remove=True)
    client.subscription_status("reader+news@example.com", business_unit_id=0)
    client.update_subscription(
        SubscriptionChange(
            email="reader@example.com", subscription_id=5, status="UNSUBSCRIBED"
        )
    )
    assert json.loads(calls[0].content) == {"properties": {"hs_name": "Launch"}}
    assert (
        calls[2].url.path
        == "/marketing/campaigns/2026-03/campaign-1/assets/MARKETING_EMAIL/123"
    )
    assert calls[3].method == "DELETE"
    assert calls[4].url.params["channel"] == "EMAIL"
    assert calls[4].url.params["businessUnitId"] == "0"
    assert b"reader%2Bnews%40example.com" in calls[4].url.raw_path
    assert json.loads(calls[5].content) == {
        "channel": "EMAIL",
        "subscriptionId": 5,
        "statusState": "UNSUBSCRIBED",
    }


def test_consent_is_never_invented() -> None:
    with pytest.raises(ValidationError):
        SubscriptionChange(
            email="reader@example.com", subscription_id=5, status="SUBSCRIBED"
        )
    change = SubscriptionChange(
        email="reader@example.com",
        subscription_id=5,
        status="SUBSCRIBED",
        legal_basis="CONSENT_WITH_NOTICE",
        legal_basis_explanation="Reader opted in through the newsletter form",
        consent_evidence_ref="consent-records/form-submission-1",
    )
    assert change.to_api()["legalBasis"] == "CONSENT_WITH_NOTICE"


def test_sequence_compilation_and_distinct_put_schema(
    setup_client: ClientFixture,
) -> None:
    client, calls, responses = setup_client
    spec = sequence()
    responses.extend(
        [
            httpx.Response(201, json={"id": "456"}),
            httpx.Response(200, json={**spec.to_api(), "revisionId": "7"}),
            httpx.Response(200, json={"id": "456"}),
        ]
    )
    client.create_sequence(spec)
    body = json.loads(calls[0].content)
    assert body["isEnabled"] is False
    assert body["enrollmentCriteria"] == {"type": "MANUAL", "shouldReEnroll": False}
    assert [a["actionTypeId"] for a in body["actions"]] == ["0-4", "0-1", "0-4"]
    assert body["actions"][0]["connection"]["nextActionId"] == "2"
    assert body["actions"][1]["fields"] == {"delta": "1440", "time_unit": "MINUTES"}
    assert "connection" not in body["actions"][-1]
    client.update_sequence("456", spec, revision_id="7")
    update = json.loads(calls[-1].content)
    assert update["revisionId"] == "7"
    assert (
        not {
            "dataSources",
            "flowType",
            "objectTypeId",
            "nextAvailableActionId",
            "id",
            "createdAt",
        }
        & update.keys()
    )


def test_enrollment_maps_ids_before_effect(setup_client: ClientFixture) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [
            httpx.Response(
                200, json={**sequence().to_api(enabled=True), "revisionId": "7"}
            ),
            httpx.Response(
                200,
                json={
                    "type": "AUTOMATED_EMAIL",
                    "isPublished": True,
                    "isTransactional": False,
                    "updatedAt": REVISION,
                },
            ),
            httpx.Response(
                200,
                json={
                    "type": "AUTOMATED_EMAIL",
                    "isPublished": True,
                    "isTransactional": False,
                    "updatedAt": REVISION,
                },
            ),
            httpx.Response(200, json={"results": [{"flowId": 456, "workflowId": 99}]}),
            httpx.Response(204),
        ]
    )
    assert (
        client.enroll(
            "456",
            "reader@example.com",
            confirm=True,
            revision_id="7",
            email_versions={"1": REVISION, "2": REVISION},
        ).data
        == {}
    )
    assert json.loads(calls[3].content) == {
        "inputs": [{"flowId": "456", "type": "FLOW_ID"}]
    }
    assert (
        calls[-1].url.path
        == "/automation/v2/workflows/99/enrollments/contacts/reader@example.com"
    )
    assert "456/enrollments" not in calls[-1].url.path


@pytest.mark.parametrize(
    "mapping",
    [
        {"results": []},
        {"results": [{"flowId": 9, "workflowId": 99}]},
        {"results": [{"flowId": 456, "workflowId": 0}]},
        {"results": [{"flowId": 456, "workflowId": 99}], "errors": [{}]},
    ],
)
def test_bad_mapping_prevents_enrollment(
    setup_client: ClientFixture, mapping: dict[str, Any]
) -> None:
    client, calls, responses = setup_client
    responses.extend(
        [
            httpx.Response(
                200, json={**sequence().to_api(enabled=True), "revisionId": "7"}
            ),
            httpx.Response(
                200,
                json={
                    "type": "AUTOMATED_EMAIL",
                    "isPublished": True,
                    "isTransactional": False,
                    "updatedAt": REVISION,
                },
            ),
            httpx.Response(
                200,
                json={
                    "type": "AUTOMATED_EMAIL",
                    "isPublished": True,
                    "isTransactional": False,
                    "updatedAt": REVISION,
                },
            ),
            httpx.Response(200, json=mapping),
        ]
    )
    with pytest.raises(HubSpotAPIError):
        client.enroll(
            "456",
            "reader@example.com",
            confirm=True,
            revision_id="7",
            email_versions={"1": REVISION, "2": REVISION},
        )
    assert len(calls) == 4


def test_nonmarketing_workflow_refused_before_mutation(
    setup_client: ClientFixture,
) -> None:
    client, calls, responses = setup_client
    flow = sequence().to_api(enabled=True)
    flow["actions"][0]["actionTypeId"] = "0-14"
    responses.append(httpx.Response(200, json=flow))
    with pytest.raises(ValueError, match="outside marketing"):
        client.archive_sequence("456")
    assert len(calls) == 1


def test_service_lifecycle_and_no_credentials_in_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN", raising=False)
    integration = HubSpotIntegration()
    assert isinstance(integration, IntegrationProtocol)
    assert not integration.initialize().success
    with pytest.raises(ValueError):
        _ = integration.client
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", CANARY)
    result = integration.initialize()
    assert result.success and CANARY not in result.model_dump_json()
    assert integration.is_available()
    integration.close()
    integration.close()
    assert not integration.is_available()


def context(client: HubSpotClient | None) -> ToolContext:
    return ToolContext(
        run_id="test-hubspot",
        tool_name="hubspot",
        tool_version="1.0.0",
        logger=None,
        fs=None,
        work_dir=".",
        output_dir=".",
        services={"hubspot.marketing": HubSpotIntegration(client)} if client else {},
    )


def test_capability_invokes_real_client_and_projects_effects(
    setup_client: ClientFixture, draft: EmailDraft
) -> None:
    client, calls, responses = setup_client
    responses.append(httpx.Response(201, json={"id": "123"}))
    registry = CapabilityRegistry()
    register_capabilities(registry)
    cap = registry.get("hubspot.marketing.email.save@1.0.0")
    result = invoke_sync(cap, SaveEmailRequest(draft=draft), context(client))
    assert result.data and result.data.data["id"] == "123"
    assert len(calls) == 1
    send = registry.get("hubspot.marketing.email.publish@1.0.0")
    assert EffectKind.EXTERNAL_COMMUNICATION in send.definition.effects.kinds
    result = invoke_sync(cap, SaveEmailRequest(draft=draft), context(None))
    assert result.data is None


def test_capability_ambiguous_result_is_structured(
    setup_client: ClientFixture, draft: EmailDraft
) -> None:
    client, _, responses = setup_client
    responses.append(httpx.ReadTimeout(CANARY))
    registry = CapabilityRegistry()
    register_capabilities(registry)
    result = invoke_sync(
        registry.get("hubspot.marketing.email.save@1.0.0"),
        SaveEmailRequest(draft=draft),
        context(client),
    )
    assert result.data is None
    assert "outcome_unknown" in result.model_dump_json()
    assert CANARY not in result.model_dump_json()


@pytest.mark.parametrize(
    "operation",
    [
        "emails",
        "email",
        "campaigns",
        "campaign",
        "campaign_assets",
        "campaign_metrics",
        "subscription_types",
        "subscription_status",
        "workflows",
        "workflow",
        "workflow_metrics",
    ],
)
def test_every_read_capability_dispatches(
    setup_client: ClientFixture, operation: str
) -> None:
    client, calls, responses = setup_client
    payload = (
        sequence().to_api()
        if operation in {"workflow", "workflow_metrics"}
        else {"results": [{"id": "1", "objectTypeId": "0-1"}]}
    )
    responses.extend([httpx.Response(200, json=payload), httpx.Response(200, json={})])
    registry = CapabilityRegistry()
    register_capabilities(registry)
    result = invoke_sync(
        registry.get("hubspot.marketing.read@1.0.0"),
        ReadRequest(operation=operation, resource_id="123", email="reader@example.com"),
        context(client),
    )
    assert result.data is not None
    assert calls and all(call.method == "GET" for call in calls)


@pytest.mark.parametrize(
    "name,input_model",
    [
        ("email.clone", CloneRequest(email_id="123", name="Next")),
        ("email.cancel", EmailIdRequest(email_id="123")),
        (
            "campaign.save",
            CampaignRequest(
                properties=CampaignProperties(properties={"hs_name": "Launch"})
            ),
        ),
        (
            "campaign.save",
            CampaignRequest(
                campaign_id="1",
                properties=CampaignProperties(properties={"hs_name": "Launch"}),
            ),
        ),
        (
            "campaign.asset",
            AssetRequest(campaign_id="1", asset_id="2", asset_type="MARKETING_EMAIL"),
        ),
        (
            "subscription.update",
            SubscriptionChange(
                email="reader@example.com", subscription_id=5, status="UNSUBSCRIBED"
            ),
        ),
        ("workflow.save", SequenceRequest(sequence=sequence())),
        ("archive", ArchiveRequest(resource="email", resource_id="1", confirm=True)),
        ("archive", ArchiveRequest(resource="campaign", resource_id="1", confirm=True)),
    ],
)
def test_mutation_capabilities_are_wired(
    setup_client: ClientFixture, name: str, input_model: BaseModel
) -> None:
    client, calls, responses = setup_client
    responses.append(httpx.Response(200, json={"id": "123"}))
    registry = CapabilityRegistry()
    register_capabilities(registry)
    result = invoke_sync(
        registry.get(f"hubspot.marketing.{name}@1.0.0"), input_model, context(client)
    )
    assert result.data is not None
    assert len(calls) == 1 and calls[0].method != "GET"


def test_invalid_requests_reject_without_network() -> None:
    for construct in [
        lambda: PageRequest(limit=0),
        lambda: PageRequest(limit=101),
        lambda: EmailSequence(name="Empty", steps=()),
        lambda: ReadRequest(operation="email"),
        lambda: ReadRequest(operation="subscription_status"),
        lambda: SequenceRequest(sequence=sequence(), enabled=True),
        lambda: EnrollmentRequest(
            flow_id="../deals", revision_id="7", email="reader@example.com"
        ),
    ]:
        with pytest.raises(ValidationError):
            construct()


def test_transport_blocks_arbitrary_endpoints() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Out-of-scope request reached transport")

    transport = HubSpotTransport(
        SecretStr(CANARY), transport=httpx.MockTransport(handler)
    )
    for path in [
        "https://evil.example",
        "/crm/v3/objects/deals",
        "/automation/v4/sequences",
        "/marketing/emails/2026-03/../other",
        "/marketing/emails/2026-03/%2e%2e/other",
        "/marketing/emails/2026-03/%5cother",
        "/marketing/emails/2026-03?url=evil",
    ]:
        with pytest.raises(ValueError):
            transport.request("GET", path)
    transport.close()
