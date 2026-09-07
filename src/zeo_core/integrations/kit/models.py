"""Typed Kit marketing inputs; effect authority stays with the host."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Id = Annotated[int, Field(gt=0, strict=True)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Email = Annotated[
    str, StringConstraints(pattern=r"^[^\s/@?#%]+@[^\s/@?#%]+\.[^\s/@?#%]+$")
]
Day = Literal[
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]
DAYS: tuple[Day, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PageRequest(Request):
    per_page: int = Field(default=50, ge=1, le=1000)
    after: str | None = Field(default=None, min_length=1, max_length=2048)


class Record(BaseModel):
    """Provider response, never evidence of delivery or host approval."""

    data: dict[str, Any]


class Page(BaseModel):
    results: list[dict[str, Any]]
    next_after: str | None
    complete: bool


def record_digest(data: dict[str, Any]) -> str:
    """Exact canonical JSON digest. Call before approval, never to invent it."""
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Time must include a timezone")
    return value.astimezone(UTC)


class SourceFilter(Request):
    type: Literal["tag", "segment"]
    ids: tuple[Id, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("Duplicate audience IDs")
        return self


class Audience(Request):
    """One documented logical group. Membership is dynamic, never snapshotted."""

    mode: Literal["all", "any", "none"] = "all"
    filters: tuple[SourceFilter, ...] = Field(default=(), max_length=2)
    entire_account: bool = False

    @model_validator(mode="after")
    def explicit_target(self) -> Self:
        if self.entire_account:
            if self.filters or self.mode != "all":
                raise ValueError("Entire-account audience cannot include filters")
        elif not self.filters:
            raise ValueError("Choose explicit tags/segments or the entire account")
        types = [item.type for item in self.filters]
        if len(set(types)) != len(types):
            raise ValueError("Combine IDs of each source type into one filter")
        return self

    def to_api(self) -> list[dict[str, Any]]:
        if self.entire_account:
            # Kit's documented default is all subscribers. The host must explicitly
            # authorize that scope; it is never produced from an empty input.
            return []
        return [{self.mode: [item.model_dump(mode="json") for item in self.filters]}]


class BroadcastDraft(Request):
    subject: Text
    content: Text
    email_address: Email
    email_template_id: Id
    audience: Audience
    description: str = ""
    preview_text: str = ""
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def valid_time(self) -> Self:
        aware(self.published_at)
        return self

    def to_api(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "content": self.content,
            "email_address": self.email_address,
            "email_template_id": self.email_template_id,
            "description": self.description,
            "preview_text": self.preview_text,
            "public": False,
            "published_at": aware(self.published_at).isoformat(),
            "send_at": None,
            "thumbnail_alt": None,
            "thumbnail_url": None,
            "subscriber_filter": self.audience.to_api(),
        }


class SendBroadcast(Request):
    """Send an approved draft as a new broadcast; track the returned new ID."""

    broadcast_id: Id
    expected_digest: Digest
    render_evidence_ref: Text
    audience_policy_ref: Text
    send_at: datetime | None = None
    publish_web: bool = False
    confirm: bool = False

    @model_validator(mode="after")
    def future_schedule(self) -> Self:
        if self.send_at is not None and aware(self.send_at) <= datetime.now(UTC):
            raise ValueError("Scheduled time must be in the future")
        return self


def broadcast_send_digest(
    data: dict[str, Any], *, send_at: datetime | None = None, publish_web: bool = False
) -> str:
    return record_digest(
        {
            "broadcast": data,
            "send_at": aware(send_at).isoformat() if send_at else "immediate",
            "publish_web": publish_web,
        }
    )


class Exclusion(Request):
    type: Literal["tag", "segment", "form", "sequence"]
    ids: tuple[Id, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("Duplicate exclusion IDs")
        return self


class SequenceDraft(Request):
    name: Text
    email_address: Email
    email_template_id: Id
    send_days: tuple[Day, ...] = DAYS
    send_hour: int = Field(default=9, ge=0, le=23)
    time_zone: Text = "UTC"
    repeat: bool = False
    hold: bool = False
    exclude_subscriber_sources: tuple[Exclusion, ...] = Field(default=(), max_length=4)

    @model_validator(mode="after")
    def valid_schedule(self) -> Self:
        if not self.send_days or len(set(self.send_days)) != len(self.send_days):
            raise ValueError("Send days must be nonempty and unique")
        try:
            ZoneInfo(self.time_zone)
        except ZoneInfoNotFoundError, ValueError:
            raise ValueError("Unsupported sequence timezone") from None
        kinds = [item.type for item in self.exclude_subscriber_sources]
        if len(set(kinds)) != len(kinds):
            raise ValueError("Combine each exclusion source type")
        return self

    def to_api(self) -> dict[str, Any]:
        return {**self.model_dump(mode="json"), "active": False}


class SequenceEmailDraft(Request):
    subject: Text
    content: Text
    position: int = Field(ge=0, le=99)
    delay_value: int = Field(ge=0, le=3650)
    delay_unit: Literal["days", "hours"]
    preview_text: str = ""
    email_template_id: Id | None = None
    send_days: tuple[Day, ...] | None = None

    @model_validator(mode="after")
    def valid_delay(self) -> Self:
        if self.delay_unit == "hours" and self.send_days is not None:
            raise ValueError("Hour delays cannot specify send days")
        if self.delay_value == 0 and (self.position != 0 or self.delay_unit != "days"):
            raise ValueError("Only the first day-based email can send immediately")
        if self.send_days is not None and (
            not self.send_days or len(set(self.send_days)) != len(self.send_days)
        ):
            raise ValueError("Send days must be nonempty and unique")
        return self

    def to_api(self) -> dict[str, Any]:
        data = {**self.model_dump(mode="json"), "published": False}
        if self.delay_unit == "hours":
            del data["send_days"]
        return data


class SubscriberCreate(Request):
    email_address: Email
    first_name: str | None = None
    state: Literal["active", "inactive"] = "inactive"
    consent_evidence_ref: Text | None = None
    confirm: bool = False

    @model_validator(mode="after")
    def require_consent(self) -> Self:
        if self.state == "active" and (
            not self.confirm or not self.consent_evidence_ref
        ):
            raise ValueError(
                "Active subscription requires confirmation and independent consent "
                "evidence"
            )
        return self

    def to_api(self) -> dict[str, Any]:
        return {
            "email_address": self.email_address,
            "first_name": self.first_name,
            "state": self.state,
        }
