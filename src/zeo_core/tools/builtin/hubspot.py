"""Canonical agent capabilities backed by the marketing client, never raw URLs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import Field, model_validator

from zeo_core.contracts import (
    CapabilityExample,
    CapabilityResult,
    ConcurrencyMode,
    EffectKind,
)
from zeo_core.integrations.hubspot.client import AssetType, HubSpotClient
from zeo_core.integrations.hubspot.models import (
    CampaignProperties,
    EmailAddress,
    EmailDraft,
    EmailSequence,
    Identifier,
    MarketingRecord,
    PageRequest,
    PublishRequest,
    RequestModel,
    SubscriptionChange,
    Text,
)
from zeo_core.integrations.hubspot.service import HubSpotIntegration
from zeo_core.integrations.hubspot.transport import HubSpotAPIError
from zeo_core.tools import (
    CapabilityRegistry,
    ToolContext,
    bound_capability_of,
    capability,
)


class ReadRequest(RequestModel):
    operation: Literal[
        "emails",
        "email",
        "campaigns",
        "campaign",
        "campaign_assets",
        "campaign_metrics",
        "subscription_types",
        "subscription_status",
        "sequences",
        "sequence",
        "sequence_metrics",
    ]
    resource_id: Identifier | None = None
    email: EmailAddress | None = None
    asset_type: AssetType = "EMAIL"
    business_unit_id: int | None = Field(default=None, ge=0)
    page: PageRequest = Field(default_factory=PageRequest)

    @model_validator(mode="after")
    def check_required(self) -> ReadRequest:
        if (
            self.operation
            in {
                "email",
                "campaign",
                "campaign_assets",
                "campaign_metrics",
                "sequence",
                "sequence_metrics",
            }
            and self.resource_id is None
        ):
            raise ValueError("This read requires resource_id")
        if self.operation == "subscription_status" and self.email is None:
            raise ValueError("Subscription status requires email")
        return self


class SaveEmailRequest(RequestModel):
    draft: EmailDraft
    email_id: Identifier | None = None
    expected_updated_at: Text | None = None

    @model_validator(mode="after")
    def check_revision(self) -> SaveEmailRequest:
        if bool(self.email_id) != bool(self.expected_updated_at):
            raise ValueError("Updates require both email_id and expected_updated_at")
        return self


class EmailIdRequest(RequestModel):
    email_id: Identifier


class CloneRequest(EmailIdRequest):
    name: Text


class CampaignRequest(RequestModel):
    properties: CampaignProperties
    campaign_id: Identifier | None = None


class AssetRequest(RequestModel):
    campaign_id: Identifier
    asset_type: AssetType
    asset_id: Identifier
    remove: bool = False


class SequenceRequest(RequestModel):
    sequence: EmailSequence
    flow_id: Identifier | None = None
    revision_id: Identifier | None = None
    enabled: bool = False
    confirm: bool = False

    @model_validator(mode="after")
    def check_revision(self) -> SequenceRequest:
        if bool(self.flow_id) != bool(self.revision_id):
            raise ValueError("Updates require both flow_id and revision_id")
        if self.enabled and self.flow_id is None:
            raise ValueError(
                "Create disabled, review the sequence, then explicitly activate it"
            )
        return self


class EnrollmentRequest(RequestModel):
    flow_id: Identifier
    email: EmailAddress
    remove: bool = False
    confirm: bool = False


class ArchiveRequest(RequestModel):
    resource: Literal["email", "campaign", "sequence"]
    resource_id: Identifier
    confirm: bool = False


def _run(
    ctx: ToolContext, operation: Callable[[HubSpotClient], MarketingRecord]
) -> CapabilityResult[MarketingRecord]:
    service = ctx.get_service("hubspot.marketing")
    if not isinstance(service, HubSpotIntegration):
        return CapabilityResult.fail(
            "Runner must supply HubSpotIntegration as hubspot.marketing",
            "ZEO_HUBSPOT_CONFIGURATION",
        )
    try:
        return CapabilityResult.ok(data=operation(service.client))
    except HubSpotAPIError as exc:
        return CapabilityResult.fail(
            str(exc),
            "ZEO_HUBSPOT_" + exc.code,
            metadata={
                "outcome_unknown": exc.outcome_unknown,
                "status_code": exc.status_code,
                "retry_after_seconds": exc.retry_after_seconds,
            },
        )
    except ValueError:
        # Pydantic errors may echo input. Keep agent-visible diagnostics secret safe.
        return CapabilityResult.fail(
            (
                "HubSpot precondition failed; check request, configuration and "
                "current provider revision"
            ),
            "ZEO_HUBSPOT_PRECONDITION",
        )


@capability(
    id="hubspot.marketing.read@1.0.0",
    description=(
        "Read HubSpot newsletters, marketing campaigns, subscriptions and"
        " email workflows. Returns one bounded page and its continuation "
        "cursor, or provider data. No CRM operations."
    ),
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(request={"operation": "emails"}, response={"data": {}}),
    ),
)
def read(request: ReadRequest, ctx: ToolContext) -> CapabilityResult[MarketingRecord]:
    def execute(client: HubSpotClient) -> MarketingRecord:
        routes: dict[str, Callable[[], MarketingRecord]] = {
            "emails": lambda: MarketingRecord(
                data=client.list_emails(request.page).model_dump()
            ),
            "email": lambda: client.get_email(request.resource_id or ""),
            "campaigns": lambda: MarketingRecord(
                data=client.list_campaigns(request.page).model_dump()
            ),
            "campaign": lambda: client.get_campaign(request.resource_id or ""),
            "campaign_assets": lambda: MarketingRecord(
                data=client.campaign_assets(
                    request.resource_id or "", request.asset_type, request.page
                ).model_dump()
            ),
            "campaign_metrics": lambda: client.campaign_metrics(
                request.resource_id or ""
            ),
            "subscription_types": lambda: client.subscription_types(
                business_unit_id=request.business_unit_id
            ),
            "subscription_status": lambda: client.subscription_status(
                request.email or "", business_unit_id=request.business_unit_id
            ),
            "sequences": lambda: MarketingRecord(
                data=client.list_sequences(request.page).model_dump()
            ),
            "sequence": lambda: client.get_sequence(request.resource_id or ""),
            "sequence_metrics": lambda: client.sequence_metrics(
                request.resource_id or ""
            ),
        }
        return routes[request.operation]()

    return _run(ctx, execute)


@capability(
    id="hubspot.marketing.email.save@1.0.0",
    description=(
        "Create an unpublished newsletter or automated marketing email, "
        "or replace a reviewed draft. Never sends. Template module values"
        " belong in content.widgets or content.flex_areas."
    ),
    effects={EffectKind.WRITE},
    examples=(
        CapabilityExample(
            request={
                "draft": {
                    "name": "Weekly issue",
                    "subject": "This week",
                    "content": {
                        "template_path": "@hubspot/email/dnd/plain_text.html",
                        "plain_text": "Hello",
                    },
                    "from_name": "Editor",
                    "from_email": "editor@example.com",
                    "subscription_id": "1",
                    "office_location_id": "2",
                }
            },
            response={"data": {}},
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def save_email(
    request: SaveEmailRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(
        ctx,
        lambda client: (
            client.update_email(
                request.email_id,
                request.draft,
                expected_updated_at=request.expected_updated_at or "",
            )
            if request.email_id
            else client.create_email(request.draft)
        ),
    )


@capability(
    id="hubspot.marketing.email.clone@1.0.0",
    description=(
        "Clone an existing marketing email as a draft for a new issue; "
        "returns the new provider ID."
    ),
    effects={EffectKind.WRITE},
    examples=(
        CapabilityExample(
            request={"email_id": "123", "name": "Next issue"}, response={"data": {}}
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def clone_email(
    request: CloneRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(ctx, lambda client: client.clone_email(request.email_id, request.name))


@capability(
    id="hubspot.marketing.email.publish@1.0.0",
    description=(
        "Send or schedule a reviewed newsletter, or activate an automated"
        " marketing email. Requires confirm, exact updatedAt, audience "
        "and subscription. Enterprise or transactional add-on entitlement"
        " required. Never auto-retry an unknown outcome."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    examples=(
        CapabilityExample(
            request={
                "email_id": "123",
                "expected_updated_at": "2026-09-07T10:00:00Z",
                "subscription_id": "1",
                "audience": {"contact_ids": ["42"]},
                "confirm": True,
            },
            response={"data": {}},
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def publish_email(
    request: PublishRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(ctx, lambda client: client.publish_email(request))


@capability(
    id="hubspot.marketing.email.cancel@1.0.0",
    description=(
        "Cancel a scheduled newsletter or unpublish an automated "
        "marketing email. Provider may refuse after sending starts; "
        "success is not proof already delivered mail was recalled."
    ),
    effects={EffectKind.WRITE},
    examples=(CapabilityExample(request={"email_id": "123"}, response={"data": {}}),),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def cancel_email(
    request: EmailIdRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(ctx, lambda client: client.cancel_email(request.email_id))


@capability(
    id="hubspot.marketing.campaign.save@1.0.0",
    description=(
        "Create or update marketing campaign properties. Creation "
        "requires hs_name. This does not send email."
    ),
    effects={EffectKind.WRITE},
    examples=(
        CapabilityExample(
            request={"properties": {"properties": {"hs_name": "Newsletter campaign"}}},
            response={"data": {}},
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def save_campaign(
    request: CampaignRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(
        ctx,
        lambda client: (
            client.update_campaign(request.campaign_id, request.properties)
            if request.campaign_id
            else client.create_campaign(request.properties)
        ),
    )


@capability(
    id="hubspot.marketing.campaign.asset@1.0.0",
    description=(
        "Associate or remove a marketing EMAIL, WORKFLOW or OBJECT_LIST "
        "asset from a campaign."
    ),
    effects={EffectKind.WRITE, EffectKind.DELETE},
    examples=(
        CapabilityExample(
            request={
                "campaign_id": "campaign-1",
                "asset_type": "EMAIL",
                "asset_id": "123",
            },
            response={"data": {}},
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def campaign_asset(
    request: AssetRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(
        ctx,
        lambda client: client.associate_asset(
            request.campaign_id,
            request.asset_type,
            request.asset_id,
            remove=request.remove,
        ),
    )


@capability(
    id="hubspot.marketing.subscription.update@1.0.0",
    description=(
        "Subscribe or unsubscribe an email address from a marketing "
        "subscription type. Opt-in requires explicit caller-supplied "
        "legal basis and explanation; never invent consent."
    ),
    effects={EffectKind.WRITE},
    examples=(
        CapabilityExample(
            request={
                "email": "reader@example.com",
                "subscription_id": 1,
                "status": "UNSUBSCRIBED",
            },
            response={"data": {}},
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def update_subscription(
    request: SubscriptionChange, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(ctx, lambda client: client.update_subscription(request))


@capability(
    id="hubspot.marketing.sequence.save@1.0.0",
    description=(
        "Create, edit, activate or pause a marketing drip sequence of "
        "automated emails and delays. Create is disabled with manual "
        "enrollment. Updates require revision_id; activation requires "
        "confirm and published nontransactional automated emails. HubSpot"
        " workflow API is beta."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    examples=(
        CapabilityExample(
            request={"sequence": {"name": "Welcome", "steps": [{"email_id": "123"}]}},
            response={"data": {}},
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def save_sequence(
    request: SequenceRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(
        ctx,
        lambda client: (
            client.update_sequence(
                request.flow_id,
                request.sequence,
                revision_id=request.revision_id or "",
                enabled=request.enabled,
                confirm=request.confirm,
            )
            if request.flow_id
            else client.create_sequence(request.sequence)
        ),
    )


@capability(
    id="hubspot.marketing.sequence.enrollment@1.0.0",
    description=(
        "Enroll or unenroll an existing contact in an email marketing "
        "workflow. Maps v4 flow ID to legacy workflow ID. Enrollment may "
        "send immediately and requires confirm; never retry an unknown "
        "result automatically."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    examples=(
        CapabilityExample(
            request={"flow_id": "456", "email": "reader@example.com", "confirm": True},
            response={"data": {}},
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def enrollment(
    request: EnrollmentRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    return _run(
        ctx,
        lambda client: client.enroll(
            request.flow_id,
            request.email,
            remove=request.remove,
            confirm=request.confirm,
        ),
    )


@capability(
    id="hubspot.marketing.archive@1.0.0",
    description=(
        "Archive a marketing email, campaign or email-only workflow. "
        "Requires explicit confirmation."
    ),
    effects={EffectKind.DELETE},
    examples=(
        CapabilityExample(
            request={"resource": "email", "resource_id": "123", "confirm": True},
            response={"data": {}},
        ),
    ),
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
)
def archive(
    request: ArchiveRequest, ctx: ToolContext
) -> CapabilityResult[MarketingRecord]:
    def execute(client: HubSpotClient) -> MarketingRecord:
        if not request.confirm:
            raise ValueError("Archiving requires confirmation")
        match request.resource:
            case "email":
                return client.archive_email(request.resource_id)
            case "campaign":
                return client.archive_campaign(request.resource_id)
            case "sequence":
                return client.archive_sequence(request.resource_id)

    return _run(ctx, execute)


def register_capabilities(registry: CapabilityRegistry) -> None:
    """Explicit opt-in. Effects are declarations; the host still owns admission."""
    for fn in (
        read,
        save_email,
        clone_email,
        publish_email,
        cancel_email,
        save_campaign,
        campaign_asset,
        update_subscription,
        save_sequence,
        enrollment,
        archive,
    ):
        registry.register(bound_capability_of(fn))
