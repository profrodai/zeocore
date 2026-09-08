"""Explicit Kit marketing capabilities on the canonical registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Self

from pydantic import Field, model_validator

from zeo_core.contracts import (
    CapabilityExample,
    CapabilityResult,
    ConcurrencyMode,
    EffectKind,
)
from zeo_core.integrations.kit.client import KitClient
from zeo_core.integrations.kit.models import (
    BroadcastDraft,
    Digest,
    Id,
    PageRequest,
    Record,
    Request,
    SendBroadcast,
    SequenceDraft,
    SequenceEmailDraft,
    SubscriberCreate,
    Text,
)
from zeo_core.integrations.kit.service import KitIntegration
from zeo_core.integrations.kit.transport import KitAPIError
from zeo_core.tools import (
    CapabilityRegistry,
    ToolContext,
    bound_capability_of,
    capability,
)


class ReadRequest(Request):
    operation: Literal[
        "account",
        "account_metrics",
        "broadcasts",
        "broadcast",
        "broadcast_metrics",
        "broadcast_clicks",
        "templates",
        "segments",
        "sequences",
        "sequence",
        "sequence_metrics",
        "sequence_snapshot",
        "sequence_emails",
        "sequence_email",
        "sequence_subscribers",
        "subscribers",
        "subscriber",
        "subscriber_tags",
        "tags",
        "tag_subscribers",
    ]
    resource_id: Id | None = None
    sequence_id: Id | None = None
    page: PageRequest = Field(default_factory=PageRequest)

    @model_validator(mode="after")
    def required_ids(self) -> Self:
        if (
            self.operation
            not in {
                "account",
                "account_metrics",
                "broadcasts",
                "templates",
                "segments",
                "sequences",
                "subscribers",
                "tags",
            }
            and self.resource_id is None
        ):
            raise ValueError("This read requires resource_id")
        if self.operation == "sequence_email" and self.sequence_id is None:
            raise ValueError("Reading a sequence email requires sequence_id")
        return self


class SaveBroadcastRequest(Request):
    draft: BroadcastDraft
    broadcast_id: Id | None = None
    expected_digest: Digest | None = None

    @model_validator(mode="after")
    def revision(self) -> Self:
        if (self.broadcast_id is None) != (self.expected_digest is None):
            raise ValueError("An edit requires both broadcast ID and reviewed digest")
        return self


class SaveSequenceRequest(Request):
    draft: SequenceDraft
    sequence_id: Id | None = None
    expected_digest: Digest | None = None

    @model_validator(mode="after")
    def revision(self) -> Self:
        if (self.sequence_id is None) != (self.expected_digest is None):
            raise ValueError(
                "An edit requires both sequence ID and reviewed snapshot digest"
            )
        return self


class SaveSequenceEmailRequest(Request):
    sequence_id: Id
    draft: SequenceEmailDraft
    expected_digest: Digest
    email_id: Id | None = None


class PublishSequenceEmailRequest(Request):
    sequence_id: Id
    email_id: Id
    expected_digest: Digest
    published: bool
    render_evidence_ref: Text
    confirm: bool = False


class SequenceStateRequest(Request):
    sequence_id: Id
    active: bool
    expected_digest: Digest
    confirm: bool = False
    render_evidence_ref: Text | None = None
    audience_policy_ref: Text | None = None

    @model_validator(mode="after")
    def activation_evidence(self) -> Self:
        if self.active and (
            not self.render_evidence_ref or not self.audience_policy_ref
        ):
            raise ValueError("Activation requires render and dynamic-audience evidence")
        return self


class EnrollmentRequest(Request):
    sequence_id: Id
    subscriber_id: Id
    expected_sequence_digest: Digest
    expected_subscriber_digest: Digest
    approval_ref: Text
    confirm: bool = False


class UnsubscribeRequest(Request):
    subscriber_id: Id
    expected_digest: Digest
    confirm: bool = False


class TagRequest(Request):
    name: Text
    tag_id: Id | None = None


class TagMembershipRequest(Request):
    tag_id: Id
    subscriber_id: Id
    remove: bool = False
    approval_ref: Text
    confirm: bool = False


class DeleteRequest(Request):
    resource: Literal["broadcast", "sequence", "sequence_email"]
    resource_id: Id
    sequence_id: Id | None = None
    expected_digest: Digest
    confirm: bool = False

    @model_validator(mode="after")
    def parent(self) -> Self:
        if self.resource == "sequence_email" and self.sequence_id is None:
            raise ValueError("Deleting a sequence email requires its parent ID")
        return self


def _run(
    ctx: ToolContext, operation: Callable[[KitClient], Record]
) -> CapabilityResult[Record]:
    service = ctx.get_service("kit.marketing")
    if not isinstance(service, KitIntegration):
        return CapabilityResult.fail(
            "Runner must supply KitIntegration as kit.marketing",
            "ZEO_KIT_CONFIGURATION",
        )
    try:
        return CapabilityResult.ok(data=operation(service.client))
    except KitAPIError as exc:
        return CapabilityResult.fail(
            str(exc),
            "ZEO_KIT_" + exc.code,
            metadata={
                "outcome_unknown": exc.outcome_unknown,
                "status_code": exc.status_code,
                "retry_after_seconds": exc.retry_after_seconds,
            },
        )
    except ValueError:
        return CapabilityResult.fail(
            "Kit precondition failed; check reviewed input and current provider state",
            "ZEO_KIT_PRECONDITION",
        )


@capability(
    id="kit.marketing.read@1.0.0",
    description=(
        "Read Kit broadcasts, sequences and full approval snapshots, "
        "subscriber state, tags and marketing metrics. Lists are bounded "
        "pages with explicit completeness."
    ),
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(request={"operation": "broadcasts"}, response={"data": {}}),
    ),
)
def read(request: ReadRequest, ctx: ToolContext) -> CapabilityResult[Record]:
    def execute(client: KitClient) -> Record:
        rid, page = request.resource_id or 0, request.page
        routes: dict[str, Callable[[], Record]] = {
            "account": client.account,
            "account_metrics": client.account_metrics,
            "broadcasts": lambda: Record(
                data=client.list_broadcasts(page).model_dump()
            ),
            "broadcast": lambda: client.get_broadcast(rid),
            "broadcast_metrics": lambda: client.broadcast_metrics(rid),
            "broadcast_clicks": lambda: client.broadcast_clicks(rid),
            "templates": lambda: Record(data=client.list_templates(page).model_dump()),
            "segments": lambda: Record(data=client.list_segments(page).model_dump()),
            "sequences": lambda: Record(data=client.list_sequences(page).model_dump()),
            "sequence": lambda: client.get_sequence(rid),
            "sequence_metrics": lambda: client.sequence_metrics(rid),
            "sequence_snapshot": lambda: client.sequence_snapshot(rid),
            "sequence_emails": lambda: Record(
                data=client.list_sequence_emails(rid, page).model_dump()
            ),
            "sequence_email": lambda: client.get_sequence_email(
                request.sequence_id or 0, rid
            ),
            "sequence_subscribers": lambda: Record(
                data=client.list_sequence_subscribers(rid, page).model_dump()
            ),
            "subscribers": lambda: Record(
                data=client.list_subscribers(page).model_dump()
            ),
            "subscriber": lambda: client.get_subscriber(rid),
            "subscriber_tags": lambda: Record(
                data=client.subscriber_tags(rid, page).model_dump()
            ),
            "tags": lambda: Record(data=client.list_tags(page).model_dump()),
            "tag_subscribers": lambda: Record(
                data=client.tag_subscribers(rid, page).model_dump()
            ),
        }
        return routes[request.operation]()

    return _run(ctx, execute)


@capability(
    id="kit.marketing.broadcast.save@1.0.0",
    description=(
        "Create or edit a private unscheduled broadcast draft. Edits bind "
        "the reviewed record digest and require draft delivery state. "
        "Never sends or publishes to the web."
    ),
    effects={EffectKind.WRITE},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "draft": {
                    "subject": "Weekly",
                    "content": "<p>News</p>",
                    "email_address": "editor@example.com",
                    "email_template_id": 1,
                    "audience": {"filters": [{"type": "tag", "ids": [2]}]},
                }
            },
            response={"data": {}},
        ),
    ),
)
def save_broadcast(
    request: SaveBroadcastRequest, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(
        ctx,
        lambda client: (
            client.update_broadcast(
                request.broadcast_id,
                request.draft,
                expected_digest=request.expected_digest or "",
            )
            if request.broadcast_id is not None
            else client.create_broadcast(request.draft)
        ),
    )


@capability(
    id="kit.marketing.broadcast.send@1.0.0",
    description=(
        "Create a NEW sending or scheduled broadcast from approved "
        "source-draft bytes. Source remains a draft. Track/cancel the "
        "returned new ID. Requires reviewed send digest, render and "
        "dynamic-audience policy references, confirm. Web publication is "
        "separately explicit; never auto-retry an unknown outcome."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "broadcast_id": 1,
                "expected_digest": "0" * 64,
                "render_evidence_ref": "review/render",
                "audience_policy_ref": "review/dynamic-tags",
                "confirm": True,
            },
            response={"data": {}},
        ),
    ),
)
def send_broadcast(
    request: SendBroadcast, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(ctx, lambda client: client.send_broadcast(request))


@capability(
    id="kit.marketing.sequence.save@1.0.0",
    description=(
        "Create a disabled Kit sequence or edit a paused sequence with its "
        "reviewed complete snapshot digest. Includes sending schedule, "
        "repeat, hold and exclusion settings. Never activates delivery."
    ),
    effects={EffectKind.WRITE},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "draft": {
                    "name": "Welcome",
                    "email_address": "editor@example.com",
                    "email_template_id": 1,
                }
            },
            response={"data": {}},
        ),
    ),
)
def save_sequence(
    request: SaveSequenceRequest, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(
        ctx,
        lambda client: (
            client.update_sequence(
                request.sequence_id,
                request.draft,
                expected_digest=request.expected_digest or "",
            )
            if request.sequence_id is not None
            else client.create_sequence(request.draft)
        ),
    )


@capability(
    id="kit.marketing.sequence.email.save@1.0.0",
    description=(
        "Create or replace an unpublished email step in a paused sequence, "
        "bound to its reviewed complete snapshot. Position and delay are "
        "explicit. Editing demotes the email to draft until reviewed "
        "publication."
    ),
    effects={EffectKind.WRITE},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "sequence_id": 1,
                "expected_digest": "0" * 64,
                "draft": {
                    "subject": "Welcome",
                    "content": "<p>Hello</p>",
                    "position": 0,
                    "delay_value": 0,
                    "delay_unit": "days",
                },
            },
            response={"data": {}},
        ),
    ),
)
def save_sequence_email(
    request: SaveSequenceEmailRequest, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(
        ctx,
        lambda client: client.save_sequence_email(
            request.sequence_id,
            request.draft,
            expected_digest=request.expected_digest,
            email_id=request.email_id,
        ),
    )


@capability(
    id="kit.marketing.sequence.email.publish@1.0.0",
    description=(
        "Publish or unpublish a reviewed email in a paused sequence. "
        "Provider publication can affect queued subscribers; requires "
        "explicit confirmation and render evidence, never auto-retry."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "sequence_id": 1,
                "email_id": 2,
                "expected_digest": "0" * 64,
                "published": True,
                "render_evidence_ref": "review/render",
                "confirm": True,
            },
            response={"data": {}},
        ),
    ),
)
def publish_sequence_email(
    request: PublishSequenceEmailRequest, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(
        ctx,
        lambda client: client.publish_sequence_email(
            request.sequence_id,
            request.email_id,
            expected_digest=request.expected_digest,
            published=request.published,
            confirm=request.confirm,
            render_evidence_ref=request.render_evidence_ref,
        ),
    )


@capability(
    id="kit.marketing.sequence.state@1.0.0",
    description=(
        "Activate a sequence using its complete reviewed snapshot digest, "
        "render and audience evidence; queued subscribers may receive "
        "email. Pause using the current sequence-record digest without "
        "requiring an intact email set. Provider queued sends still "
        "require reconciliation."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "sequence_id": 1,
                "active": False,
                "expected_digest": "0" * 64,
                "confirm": True,
            },
            response={"data": {}},
        ),
    ),
)
def sequence_state(
    request: SequenceStateRequest, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(
        ctx,
        lambda client: client.set_sequence_active(
            request.sequence_id,
            active=request.active,
            expected_digest=request.expected_digest,
            confirm=request.confirm,
            render_evidence_ref=request.render_evidence_ref or "",
            audience_policy_ref=request.audience_policy_ref or "",
        ),
    )


@capability(
    id="kit.marketing.sequence.enroll@1.0.0",
    description=(
        "Enroll one existing active subscriber into a reviewed active "
        "sequence. Requires complete sequence and subscriber digests, "
        "approval reference and confirm. Never creates/reactivates the "
        "subscriber; may send immediately. Per-subscriber sequence removal "
        "is not exposed by Kit v4."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "sequence_id": 1,
                "subscriber_id": 2,
                "expected_sequence_digest": "0" * 64,
                "expected_subscriber_digest": "0" * 64,
                "approval_ref": "review/enrollment",
                "confirm": True,
            },
            response={"data": {}},
        ),
    ),
)
def enroll(request: EnrollmentRequest, ctx: ToolContext) -> CapabilityResult[Record]:
    return _run(
        ctx,
        lambda client: client.enroll(
            request.sequence_id,
            request.subscriber_id,
            expected_sequence_digest=request.expected_sequence_digest,
            expected_subscriber_digest=request.expected_subscriber_digest,
            confirm=request.confirm,
            approval_ref=request.approval_ref,
        ),
    )


@capability(
    id="kit.marketing.subscriber.create@1.0.0",
    description=(
        "Create/upsert a marketing subscriber; default is inactive. Active "
        "creation requires separately authorized independent consent "
        "evidence and confirm, and may trigger account automations. Kit "
        "upsert does not change existing subscriber state; never infer "
        "reactivation from success."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={"email_address": "reader@example.com", "state": "inactive"},
            response={"data": {}},
        ),
    ),
)
def create_subscriber(
    request: SubscriberCreate, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(ctx, lambda client: client.create_subscriber(request))


@capability(
    id="kit.marketing.subscriber.unsubscribe@1.0.0",
    description=(
        "Globally unsubscribe a reviewed subscriber from ALL future Kit "
        "emails. This is not sequence-only removal. Requires confirm and "
        "current subscriber-record digest; preserves subscriber history "
        "and tags."
    ),
    effects={EffectKind.WRITE},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={"subscriber_id": 1, "expected_digest": "0" * 64, "confirm": True},
            response={"data": {}},
        ),
    ),
)
def unsubscribe(
    request: UnsubscribeRequest, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(
        ctx,
        lambda client: client.unsubscribe(
            request.subscriber_id,
            expected_digest=request.expected_digest,
            confirm=request.confirm,
        ),
    )


@capability(
    id="kit.marketing.tag.save@1.0.0",
    description=(
        "Create a named marketing tag or rename an existing tag. Kit "
        "matches create names case-insensitively; existing IDs remain "
        "stable. A tag organizes campaigns and audiences, not a separate "
        "campaign API object."
    ),
    effects={EffectKind.WRITE},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(request={"name": "Weekly newsletter"}, response={"data": {}}),
    ),
)
def save_tag(request: TagRequest, ctx: ToolContext) -> CapabilityResult[Record]:
    return _run(
        ctx, lambda client: client.save_tag(request.name, tag_id=request.tag_id)
    )


@capability(
    id="kit.marketing.tag.membership@1.0.0",
    description=(
        "Add/remove a tag on one existing subscriber. BOTH operations may "
        "trigger Kit Visual Automations. Requires host-reviewed "
        "automation/audience approval and confirm. Never creates a "
        "subscriber or changes consent."
    ),
    effects={EffectKind.WRITE, EffectKind.EXTERNAL_COMMUNICATION},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "tag_id": 1,
                "subscriber_id": 2,
                "approval_ref": "review/tag-effect",
                "confirm": True,
            },
            response={"data": {}},
        ),
    ),
)
def tag_membership(
    request: TagMembershipRequest, ctx: ToolContext
) -> CapabilityResult[Record]:
    return _run(
        ctx,
        lambda client: client.set_tag(
            request.tag_id,
            request.subscriber_id,
            remove=request.remove,
            confirm=request.confirm,
            approval_ref=request.approval_ref,
        ),
    )


@capability(
    id="kit.marketing.delete@1.0.0",
    description=(
        "Delete a reviewed draft/scheduled broadcast, sequence or paused "
        "sequence email. Broadcast deletion is permanent and cancels the "
        "scheduled object; this is not reversible unpublish. Requires "
        "confirm and record digest (complete snapshot for sequence-email "
        "deletion). Cannot undo delivery already started."
    ),
    effects={EffectKind.DELETE},
    concurrency=ConcurrencyMode.SERIAL_PER_CAPABILITY,
    examples=(
        CapabilityExample(
            request={
                "resource": "broadcast",
                "resource_id": 1,
                "expected_digest": "0" * 64,
                "confirm": True,
            },
            response={"data": {}},
        ),
    ),
)
def delete(request: DeleteRequest, ctx: ToolContext) -> CapabilityResult[Record]:
    def execute(client: KitClient) -> Record:
        if request.resource == "broadcast":
            return client.delete_broadcast(
                request.resource_id,
                expected_digest=request.expected_digest,
                confirm=request.confirm,
            )
        if request.resource == "sequence":
            return client.delete_sequence(
                request.resource_id,
                expected_digest=request.expected_digest,
                confirm=request.confirm,
            )
        return client.delete_sequence_email(
            request.sequence_id or 0,
            request.resource_id,
            expected_digest=request.expected_digest,
            confirm=request.confirm,
        )

    return _run(ctx, execute)


def register_capabilities(registry: CapabilityRegistry) -> None:
    """Opt in explicitly; the registry does not grant provider-effect authority."""
    for fn in (
        read,
        save_broadcast,
        send_broadcast,
        save_sequence,
        save_sequence_email,
        publish_sequence_email,
        sequence_state,
        enroll,
        create_subscriber,
        unsubscribe,
        save_tag,
        tag_membership,
        delete,
    ):
        registry.register(bound_capability_of(fn))
