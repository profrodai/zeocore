"""HubSpot marketing only: emails, campaigns, preferences and email workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import quote

from pydantic import SecretStr, TypeAdapter

from .models import (
    Audience,
    CampaignProperties,
    EmailAddress,
    EmailDraft,
    EmailSequence,
    Identifier,
    MarketingPage,
    MarketingRecord,
    PageRequest,
    PublishRequest,
    SubscriptionChange,
    send_spec_digest,
)
from .transport import HubSpotAPIError, HubSpotTransport
from .workflow import validate_workflow

EMAILS = "/marketing/emails/2026-03"
CAMPAIGNS = "/marketing/campaigns/2026-03"
PREFERENCES = "/communication-preferences/2026-03"
FLOWS = "/automation/v4/flows"
AssetType = Literal["MARKETING_EMAIL", "AUTOMATION_PLATFORM_FLOW", "OBJECT_LIST"]
_DEFAULT_PAGE = PageRequest()


def _id(value: str) -> str:
    return TypeAdapter(Identifier).validate_python(value)


def _email(value: str) -> str:
    return quote(TypeAdapter(EmailAddress).validate_python(value), safe="")


class HubSpotClient:
    """Explicit API operations; credentials never appear in result objects."""

    def __init__(
        self,
        access_token: SecretStr | None = None,
        *,
        transport: HubSpotTransport | None = None,
    ) -> None:
        if transport is None:
            if access_token is None:
                raise ValueError("HubSpot access token is required")
            transport = HubSpotTransport(access_token)
        self._transport = transport

    def close(self) -> None:
        self._transport.close()

    def _record(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, str | int | bool] | None = None,
    ) -> MarketingRecord:
        return MarketingRecord(
            data=self._transport.request(method, path, body=body, params=params)
        )

    def _page(
        self,
        path: str,
        page: PageRequest,
        *,
        params: dict[str, str | int | bool] | None = None,
    ) -> MarketingPage:
        query: dict[str, str | int | bool] = {"limit": page.limit, **(params or {})}
        if page.after is not None:
            query["after"] = page.after
        data = self._transport.request("GET", path, params=query)
        results = data.get("results")
        paging = data.get("paging", {})
        if (
            not isinstance(results, list)
            or len(results) > page.limit
            or not all(isinstance(row, dict) for row in results)
            or not isinstance(paging, dict)
        ):
            raise HubSpotAPIError("RESPONSE", "HubSpot returned an invalid page")
        next_page = paging.get("next", {})
        if not isinstance(next_page, dict):
            raise HubSpotAPIError("RESPONSE", "HubSpot returned invalid pagination")
        after = next_page.get("after")
        if (next_page and after is None) or (
            after is not None
            and (
                not isinstance(after, str)
                or not after
                or len(after) > 2048
                or after == page.after
            )
        ):
            raise HubSpotAPIError(
                "RESPONSE", "HubSpot returned an invalid or repeated cursor"
            )
        return MarketingPage(
            results=results,
            next_after=after,
            complete=page.after is None and after is None,
        )

    def list_emails(
        self, page: PageRequest = _DEFAULT_PAGE, *, campaign_id: str | None = None
    ) -> MarketingPage:
        params: dict[str, str | int | bool] = {"includeStats": True}
        if campaign_id is not None:
            params["campaign"] = _id(campaign_id)
        return self._page(EMAILS, page, params=params)

    def get_email(self, email_id: str) -> MarketingRecord:
        return self._record(
            "GET", f"{EMAILS}/{_id(email_id)}", params={"includeStats": True}
        )

    def create_email(self, draft: EmailDraft) -> MarketingRecord:
        return self._record("POST", EMAILS, body=draft.to_api())

    def update_email(
        self, email_id: str, draft: EmailDraft, *, expected_updated_at: str
    ) -> MarketingRecord:
        self._check_email(email_id, expected_updated_at)
        return self._record("PATCH", f"{EMAILS}/{_id(email_id)}", body=draft.to_api())

    def clone_email(self, email_id: str, name: str) -> MarketingRecord:
        if not name.strip():
            raise ValueError("Clone name is required")
        return self._record(
            "POST", f"{EMAILS}/clone", body={"id": _id(email_id), "cloneName": name}
        )

    def _check_email(self, email_id: str, expected_updated_at: str) -> dict[str, Any]:
        data = self.get_email(email_id).data
        if not expected_updated_at or data.get("updatedAt") != expected_updated_at:
            raise ValueError(
                "Email changed since review; fetch and review the current revision"
            )
        if data.get("isPublished") is not False or data.get("state") not in {
            "DRAFT",
            "AUTOMATED_DRAFT",
        }:
            raise ValueError(
                "Only an unpublished draft can be changed or published here"
            )
        if data.get("isTransactional") is not False or data.get("type") not in {
            "BATCH_EMAIL",
            "AUTOMATED_EMAIL",
        }:
            raise ValueError(
                "Only nontransactional newsletters and automated marketing emails"
                " are supported"
            )
        return data

    def publish_email(self, request: PublishRequest) -> MarketingRecord:
        if not request.confirm:
            raise ValueError(
                "Publishing can send email; explicit confirmation is required"
            )
        # Recheck at dispatch; a previously validated request may be stale.
        if request.send_at is not None and request.send_at <= datetime.now(UTC):
            raise ValueError("Schedule must still be in the future at dispatch")
        data = self._check_email(request.email_id, request.expected_updated_at)
        expected_type = (
            "BATCH_EMAIL" if request.kind == "newsletter" else "AUTOMATED_EMAIL"
        )
        if data.get("type") != expected_type:
            raise ValueError(
                "Reviewed email kind does not match the requested operation"
            )
        details = data.get("subscriptionDetails", {})
        if (
            not isinstance(details, dict)
            or details.get("subscriptionId") != request.subscription_id
        ):
            raise ValueError("Reviewed subscription type does not match the email")
        if request.kind == "newsletter":
            request.audience.require_recipients()
            self._check_audience(data, request.audience)
        if (
            send_spec_digest(
                data, send_at=request.send_at, audience_mode=request.audience_mode
            )
            != request.expected_send_spec_sha256
        ):
            raise ValueError("Email send specification changed since approval")
        body: dict[str, Any] = {
            "sendOnPublish": request.kind == "newsletter" and request.send_at is None,
        }
        if request.send_at is not None:
            body["publishDate"] = request.send_at.astimezone(UTC).isoformat()
        self._record("PATCH", f"{EMAILS}/{request.email_id}", body=body)
        self._check_configured_send(request, body)
        # A privileged edit after this GET remains a provider-side race.
        return self._record("POST", f"{EMAILS}/{request.email_id}/publish")

    def _check_configured_send(
        self, request: PublishRequest, body: dict[str, Any]
    ) -> None:
        final = self.get_email(request.email_id).data
        if (
            send_spec_digest(
                final, send_at=request.send_at, audience_mode=request.audience_mode
            )
            != request.expected_send_spec_sha256
        ):
            raise ValueError("Email changed during send configuration; review again")
        if final.get("sendOnPublish") is not body["sendOnPublish"]:
            raise ValueError("Provider send configuration does not match approval")
        if request.send_at is not None:
            published_at = final.get("publishDate")
            if (
                not isinstance(published_at, str)
                or datetime.fromisoformat(published_at) != request.send_at
            ):
                raise ValueError("Provider schedule does not match approval")
            if request.send_at <= datetime.now(UTC):
                raise ValueError("Schedule expired before publish")

    @staticmethod
    def _check_audience(data: dict[str, Any], audience: Audience) -> None:
        actual = data.get("to")
        expected = audience.to_api()
        if not isinstance(actual, dict):
            raise ValueError("Email has no reviewed audience")
        for key in ("contactIds", "contactIlsLists"):
            group = actual.get(key, {})
            if not isinstance(group, dict) or any(
                sorted(group.get(part, [])) != sorted(expected[key][part])
                for part in ("include", "exclude")
            ):
                raise ValueError("Email audience changed since review")
        legacy = actual.get("contactLists", {})
        if (
            not isinstance(legacy, dict)
            or legacy.get("include")
            or legacy.get("exclude")
        ):
            raise ValueError(
                "Legacy recipient lists must be migrated to explicit ILS audience IDs"
            )
        if (
            actual.get("suppressGraymail") is not True
            or actual.get("limitSendFrequency") is not True
        ):
            raise ValueError("Email suppression settings changed since review")

    def cancel_email(self, email_id: str) -> MarketingRecord:
        """Provider may refuse cancellation once delivery has started."""
        return self._record("POST", f"{EMAILS}/{_id(email_id)}/unpublish")

    def archive_email(self, email_id: str) -> MarketingRecord:
        return self._record("DELETE", f"{EMAILS}/{_id(email_id)}")

    def list_campaigns(self, page: PageRequest = _DEFAULT_PAGE) -> MarketingPage:
        return self._page(CAMPAIGNS, page)

    def get_campaign(self, campaign_id: str) -> MarketingRecord:
        return self._record("GET", f"{CAMPAIGNS}/{_id(campaign_id)}")

    def create_campaign(self, properties: CampaignProperties) -> MarketingRecord:
        if not properties.properties.get("hs_name", "").strip():
            raise ValueError("Campaign creation requires hs_name")
        return self._record("POST", CAMPAIGNS, body=properties.model_dump())

    def update_campaign(
        self, campaign_id: str, properties: CampaignProperties
    ) -> MarketingRecord:
        return self._record(
            "PATCH", f"{CAMPAIGNS}/{_id(campaign_id)}", body=properties.model_dump()
        )

    def archive_campaign(self, campaign_id: str) -> MarketingRecord:
        return self._record("DELETE", f"{CAMPAIGNS}/{_id(campaign_id)}")

    def campaign_assets(
        self, campaign_id: str, asset_type: AssetType, page: PageRequest = _DEFAULT_PAGE
    ) -> MarketingPage:
        kind: AssetType = TypeAdapter(AssetType).validate_python(asset_type)
        return self._page(f"{CAMPAIGNS}/{_id(campaign_id)}/assets/{kind}", page)

    def associate_asset(
        self,
        campaign_id: str,
        asset_type: AssetType,
        asset_id: str,
        *,
        remove: bool = False,
    ) -> MarketingRecord:
        kind: AssetType = TypeAdapter(AssetType).validate_python(asset_type)
        return self._record(
            "DELETE" if remove else "PUT",
            f"{CAMPAIGNS}/{_id(campaign_id)}/assets/{kind}/{_id(asset_id)}",
        )

    def campaign_metrics(self, campaign_id: str) -> MarketingRecord:
        return self._record("GET", f"{CAMPAIGNS}/{_id(campaign_id)}/reports/metrics")

    def subscription_types(
        self, *, business_unit_id: int | None = None
    ) -> MarketingRecord:
        if business_unit_id is not None and business_unit_id < 0:
            raise ValueError("Business unit ID must be nonnegative")
        return self._record(
            "GET",
            f"{PREFERENCES}/definitions",
            params={"businessUnitId": business_unit_id}
            if business_unit_id is not None
            else None,
        )

    def subscription_status(
        self, email: str, *, business_unit_id: int | None = None
    ) -> MarketingRecord:
        params: dict[str, str | int | bool] = {"channel": "EMAIL"}
        if business_unit_id is not None:
            if business_unit_id < 0:
                raise ValueError("Business unit ID must be nonnegative")
            params["businessUnitId"] = business_unit_id
        return self._record(
            "GET", f"{PREFERENCES}/statuses/{_email(email)}", params=params
        )

    def update_subscription(self, change: SubscriptionChange) -> MarketingRecord:
        return self._record(
            "POST",
            f"{PREFERENCES}/statuses/{_email(change.email)}",
            body=change.to_api(),
        )

    def list_sequences(self, page: PageRequest = _DEFAULT_PAGE) -> MarketingPage:
        """Listing only; arbitrary account workflows cannot be mutated here."""
        result = self._page(FLOWS, page)
        return MarketingPage(
            results=[row for row in result.results if row.get("objectTypeId") == "0-1"],
            next_after=result.next_after,
            complete=result.complete,
        )

    def get_sequence(self, flow_id: str) -> MarketingRecord:
        result = self._record("GET", f"{FLOWS}/{_id(flow_id)}")
        self._require_marketing_flow(result.data)
        return result

    @staticmethod
    def _require_marketing_flow(data: dict[str, Any]) -> None:
        validate_workflow(data)

    def _review_flow_emails(
        self, sequence: EmailSequence, versions: dict[str, str]
    ) -> None:
        if set(versions) != {step.email_id for step in sequence.steps}:
            raise ValueError(
                "Review must bind exactly every referenced marketing email"
            )
        for step in sequence.steps:
            email = self.get_email(step.email_id).data
            if (
                email.get("type") != "AUTOMATED_EMAIL"
                or email.get("isPublished") is not True
                or email.get("isTransactional") is not False
                or not versions[step.email_id]
                or email.get("updatedAt") != versions[step.email_id]
            ):
                raise ValueError(
                    "Workflow email changed or is not published "
                    "nontransactional automated email"
                )

    def create_sequence(self, sequence: EmailSequence) -> MarketingRecord:
        return self._record("POST", FLOWS, body=sequence.to_api())

    def update_sequence(
        self,
        flow_id: str,
        sequence: EmailSequence,
        *,
        revision_id: str,
        email_versions: dict[str, str] | None = None,
        enabled: bool = False,
        confirm: bool = False,
    ) -> MarketingRecord:
        if enabled and not confirm:
            raise ValueError("Activating a sequence requires explicit confirmation")
        current = self.get_sequence(flow_id).data
        if current.get("revisionId") != _id(revision_id):
            raise ValueError("Workflow revision changed; review before updating")
        if enabled:
            self._review_flow_emails(sequence, email_versions or {})
        body = sequence.to_api(enabled=enabled)
        body["revisionId"] = revision_id
        # Description/UUID are the only additional supported writable metadata.
        for key in ("description", "uuid"):
            if key in current:
                body[key] = current[key]
        # PUT has a distinct schema; never round-trip create-only or read-only fields.
        for key in ("objectTypeId", "flowType", "dataSources"):
            del body[key]
        return self._record("PUT", f"{FLOWS}/{_id(flow_id)}", body=body)

    def sequence_metrics(self, flow_id: str) -> MarketingRecord:
        self.get_sequence(flow_id)
        return self._record("GET", f"{FLOWS}/performance/{_id(flow_id)}")

    def archive_sequence(self, flow_id: str) -> MarketingRecord:
        self.get_sequence(flow_id)
        return self._record("DELETE", f"{FLOWS}/{_id(flow_id)}")

    def enroll(
        self,
        flow_id: str,
        email: str,
        *,
        revision_id: str,
        email_versions: dict[str, str] | None = None,
        remove: bool = False,
        confirm: bool = False,
    ) -> MarketingRecord:
        encoded_email = _email(email)
        if not remove and not confirm:
            raise ValueError(
                "Enrollment may send email; explicit confirmation is required"
            )
        current = self.get_sequence(flow_id).data
        if current.get("revisionId") != _id(revision_id):
            raise ValueError("Workflow changed since enrollment review")
        if not remove:
            self._review_flow_emails(validate_workflow(current), email_versions or {})
        if not remove and current.get("isEnabled") is not True:
            raise ValueError("Sequence must be enabled before enrollment")
        mapping = self._transport.request(
            "POST",
            "/automation/v4/workflow-id-mappings/batch/read",
            body={"inputs": [{"type": "FLOW_ID", "flowId": _id(flow_id)}]},
            read_only=True,
        )
        rows = mapping.get("results")
        if (
            mapping.get("errors")
            or not isinstance(rows, list)
            or len(rows) != 1
            or not isinstance(rows[0], dict)
            or str(rows[0].get("flowId")) != flow_id
        ):
            raise HubSpotAPIError(
                "MAPPING", "HubSpot did not return a unique workflow ID mapping"
            )
        workflow_id = rows[0].get("workflowId")
        if type(workflow_id) is not int or workflow_id <= 0:
            raise HubSpotAPIError(
                "MAPPING", "HubSpot returned an invalid legacy workflow ID"
            )
        return self._record(
            "DELETE" if remove else "POST",
            f"/automation/v2/workflows/{workflow_id}/enrollments/contacts/{encoded_email}",
        )
