"""Bounded marketing requests. No general CRM or arbitrary HTTP surface."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$")
]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
EmailAddress = Annotated[
    str, StringConstraints(pattern=r"^[^\s/@?#%]+@[^\s/@?#%]+\.[^\s/@?#%]+$")
]


class RequestModel(BaseModel):
    """Reject typos and accidental provider fields before dispatch."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PageRequest(RequestModel):
    limit: int = Field(default=50, ge=1, le=100)
    after: str | None = Field(default=None, min_length=1, max_length=2048)


class Audience(RequestModel):
    """Existing HubSpot contacts and ILS segment IDs; exclusions always win."""

    contact_ids: tuple[Identifier, ...] = Field(default=(), max_length=1000)
    list_ids: tuple[Identifier, ...] = Field(default=(), max_length=100)
    exclude_contact_ids: tuple[Identifier, ...] = Field(default=(), max_length=1000)
    exclude_list_ids: tuple[Identifier, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def validate_members(self) -> Self:
        for values in (
            self.contact_ids,
            self.list_ids,
            self.exclude_contact_ids,
            self.exclude_list_ids,
        ):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate audience IDs are not allowed")
        if set(self.contact_ids) & set(self.exclude_contact_ids) or set(
            self.list_ids
        ) & set(self.exclude_list_ids):
            raise ValueError("An audience ID cannot be both included and excluded")
        return self

    def require_recipients(self) -> None:
        if not self.contact_ids and not self.list_ids:
            raise ValueError(
                "Publishing a newsletter requires an explicit nonempty audience"
            )

    def to_api(self) -> dict[str, Any]:
        return {
            "contactIds": {
                "include": list(self.contact_ids),
                "exclude": list(self.exclude_contact_ids),
            },
            "contactIlsLists": {
                "include": list(self.list_ids),
                "exclude": list(self.exclude_list_ids),
            },
            "suppressGraymail": True,
            "limitSendFrequency": True,
        }


class EmailContent(RequestModel):
    """Template-specific module values retain HubSpot's JSON shape."""

    template_path: Text
    plain_text: Text | None = None
    widgets: dict[str, Any] = Field(default_factory=dict)
    flex_areas: dict[str, Any] = Field(default_factory=dict)

    def to_api(self) -> dict[str, Any]:
        data: dict[str, Any] = {"templatePath": self.template_path}
        if self.plain_text is not None:
            data["plainTextVersion"] = self.plain_text
        if self.widgets:
            data["widgets"] = self.widgets
        if self.flex_areas:
            data["flexAreas"] = self.flex_areas
        return data


class EmailDraft(RequestModel):
    name: Text
    subject: Text
    content: EmailContent
    from_name: Text
    from_email: EmailAddress
    subscription_id: Identifier
    office_location_id: Identifier
    audience: Audience = Field(default_factory=Audience)
    kind: Literal["newsletter", "automated"] = "newsletter"
    campaign_id: Identifier | None = None
    business_unit_id: int | None = Field(default=None, ge=0)

    def to_api(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "subject": self.subject,
            "content": self.content.to_api(),
            "from": {"fromName": self.from_name, "replyTo": self.from_email},
            "subscriptionDetails": {
                "subscriptionId": self.subscription_id,
                "officeLocationId": self.office_location_id,
            },
            "to": self.audience.to_api(),
            "sendOnPublish": False,
            "state": "DRAFT" if self.kind == "newsletter" else "AUTOMATED_DRAFT",
            "subcategory": "batch" if self.kind == "newsletter" else "automated",
        }
        if self.campaign_id is not None:
            data["campaign"] = self.campaign_id
        if self.business_unit_id is not None:
            data["businessUnitId"] = self.business_unit_id
        return data


Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
AudienceMode = Literal["fixed_contacts", "dynamic_segments"]


def send_spec_digest(
    email: dict[str, Any],
    *,
    send_at: datetime | None = None,
    audience_mode: AudienceMode = "fixed_contacts",
) -> str:
    """Bind provider content/metadata and requested execution policy to review.

    This is a comparison helper, not authority to approve a send. The host binds
    its render evidence and approval to this digest before execution. Mutable
    template assets and dynamic segment membership are not snapshotted here.
    """
    payload = {
        "email": {
            key: value
            for key, value in email.items()
            if key not in {"updatedAt", "stats", "sendOnPublish", "publishDate"}
        },
        "send_at": send_at.astimezone(UTC).isoformat() if send_at else None,
        "audience_mode": audience_mode,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


class PublishRequest(RequestModel):
    email_id: Identifier
    expected_updated_at: Text
    expected_send_spec_sha256: Digest
    render_evidence_ref: Text
    audience_mode: AudienceMode = "fixed_contacts"
    audience_policy_ref: Text | None = None
    kind: Literal["newsletter", "automated"] = "newsletter"
    audience: Audience = Field(default_factory=Audience)
    subscription_id: Identifier
    send_at: datetime | None = None
    confirm: bool = False

    @model_validator(mode="after")
    def validate_publish(self) -> Self:
        if self.audience.list_ids or self.audience.exclude_list_ids:
            if self.audience_mode != "dynamic_segments" or not self.audience_policy_ref:
                raise ValueError(
                    "Segment membership requires explicit "
                    "dynamic audience authorization"
                )
        elif self.audience_mode != "fixed_contacts":
            raise ValueError("Dynamic audience mode requires segment IDs")
        if self.kind == "newsletter":
            self.audience.require_recipients()
        elif self.send_at is not None:
            raise ValueError(
                "Automated emails are activated for workflows, not scheduled directly"
            )
        if self.send_at is not None:
            if self.send_at.tzinfo is None or self.send_at.utcoffset() is None:
                raise ValueError("Schedule must include a timezone")
            if self.send_at <= datetime.now(UTC):
                raise ValueError("Schedule must be in the future")
        return self


class CampaignProperties(RequestModel):
    """Writable campaign properties; unknown property names are provider-validated."""

    properties: dict[str, str] = Field(min_length=1, max_length=100)


class SequenceStep(RequestModel):
    email_id: Identifier
    delay_minutes: int = Field(default=0, ge=0, le=525600)


class EmailSequence(RequestModel):
    """A manual-enrollment marketing drip, created disabled by default."""

    name: Text
    steps: tuple[SequenceStep, ...] = Field(min_length=1, max_length=50)
    suppression_list_ids: tuple[int, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def validate_steps(self) -> Self:
        ids = [step.email_id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("A sequence cannot send the same email twice")
        if any(value <= 0 for value in self.suppression_list_ids):
            raise ValueError("Suppression list IDs must be positive")
        if len(self.suppression_list_ids) != len(set(self.suppression_list_ids)):
            raise ValueError("Duplicate suppression list IDs")
        return self

    def to_api(self, *, enabled: bool = False) -> dict[str, Any]:
        actions: list[dict[str, Any]] = []
        for step in self.steps:
            if step.delay_minutes:
                actions.append(
                    {
                        "actionTypeId": "0-1",
                        "fields": {
                            "delta": str(step.delay_minutes),
                            "time_unit": "MINUTES",
                        },
                    }
                )
            actions.append(
                {"actionTypeId": "0-4", "fields": {"content_id": step.email_id}}
            )
        for index, action in enumerate(actions, 1):
            action.update(
                type="SINGLE_CONNECTION", actionId=str(index), actionTypeVersion=0
            )
            if index < len(actions):
                action["connection"] = {
                    "edgeType": "STANDARD",
                    "nextActionId": str(index + 1),
                }
        return {
            "name": self.name,
            "type": "CONTACT_FLOW",
            "objectTypeId": "0-1",
            "flowType": "WORKFLOW",
            "isEnabled": enabled,
            "startActionId": "1",
            "actions": actions,
            "enrollmentCriteria": {"type": "MANUAL", "shouldReEnroll": False},
            "timeWindows": [],
            "blockedDates": [],
            "customProperties": {},
            "dataSources": [],
            "suppressionListIds": list(self.suppression_list_ids),
            "canEnrollFromSalesforce": False,
        }


class SubscriptionChange(RequestModel):
    email: EmailAddress
    subscription_id: int = Field(gt=0)
    status: Literal["SUBSCRIBED", "UNSUBSCRIBED"]
    legal_basis: (
        Literal[
            "CONSENT_WITH_NOTICE",
            "LEGITIMATE_INTEREST_CLIENT",
            "LEGITIMATE_INTEREST_OTHER",
            "LEGITIMATE_INTEREST_PQL",
            "NON_GDPR",
            "PERFORMANCE_OF_CONTRACT",
            "PROCESS_AND_STORE",
        ]
        | None
    ) = None
    legal_basis_explanation: Text | None = None
    consent_evidence_ref: Text | None = None

    @model_validator(mode="after")
    def require_consent_evidence(self) -> Self:
        if self.status == "SUBSCRIBED" and (
            not self.legal_basis
            or not self.legal_basis_explanation
            or not self.consent_evidence_ref
        ):
            raise ValueError(
                "Subscribing requires legal basis, explanation "
                "and independent consent evidence reference"
            )
        if bool(self.legal_basis) != bool(self.legal_basis_explanation):
            raise ValueError("Legal basis and explanation must be supplied together")
        return self

    def to_api(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "channel": "EMAIL",
            "subscriptionId": self.subscription_id,
            "statusState": self.status,
        }
        if self.legal_basis:
            data.update(
                legalBasis=self.legal_basis,
                legalBasisExplanation=self.legal_basis_explanation,
            )
        return data


class MarketingRecord(BaseModel):
    """Provider data, explicitly not interpreted as proof of delivery."""

    data: dict[str, Any]


class MarketingPage(BaseModel):
    results: list[dict[str, Any]]
    next_after: str | None = None
    complete: bool = False
    # Only true for an unpaginated first-page result. Never a snapshot guarantee.
