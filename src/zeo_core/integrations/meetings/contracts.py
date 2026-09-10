"""Closed meeting-v1 execution and receipt contracts owned by the runtime."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Operation = Literal[
    "notion.page.upsert",
    "sheets.values.read",
    "calendar.events.list",
    "gmail.draft.create",
    "gmail.draft.get",
    "gmail.draft.reconcile",
]
Outcome = Literal["SUCCEEDED", "REFUSED", "AMBIGUOUS"]


class ClosedModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class InvocationAuthorization(ClosedModel):
    schema_version: Literal[1] = 1
    invocation_id: str = Field(pattern=r"^invocation_[0-9a-z]{16,}$")
    meeting_id: str = Field(pattern=r"^meeting_[0-9a-z]{16,}$")
    organization_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    action_id: str | None = Field(default=None, pattern=r"^action_[0-9a-z]{16,}$")
    lease_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    operation: Operation
    resource: str = Field(min_length=1)
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1)
    authorized_at: AwareDatetime


class InvocationReceipt(ClosedModel):
    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^receipt_[0-9a-z]{16,}$")
    invocation_id: str = Field(pattern=r"^invocation_[0-9a-z]{16,}$")
    operation: Operation
    resource: str = Field(min_length=1)
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: Outcome
    provider_object_id: str = ""
    response_sha256: str = Field(default="", pattern=r"^$|^[0-9a-f]{64}$")
    observed_at: AwareDatetime
    reconciled: bool = False

    @model_validator(mode="after")
    def _created_object_is_identified(self) -> InvocationReceipt:
        if (
            self.outcome == "SUCCEEDED"
            and self.operation.endswith(".create")
            and not self.provider_object_id
        ):
            raise ValueError("successful create requires a provider object")
        return self


class InvocationReconciliation(ClosedModel):
    schema_version: Literal[1] = 1
    reconciliation_id: str = Field(pattern=r"^reconciliation_[0-9a-z]{16,}$")
    invocation_id: str = Field(pattern=r"^invocation_[0-9a-z]{16,}$")
    outcome: Literal["SUCCEEDED", "REFUSED"]
    provider_object_id: str = ""
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: AwareDatetime


class AuthorizationResult(ClosedModel):
    authorization: InvocationAuthorization
    disposition: Literal["EXECUTE", "RECONCILE", "REPLAY_FINAL"]
    receipt: InvocationReceipt | None = None
    reconciliation: InvocationReconciliation | None = None
