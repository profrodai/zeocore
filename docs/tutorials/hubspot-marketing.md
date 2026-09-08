# HubSpot newsletters and marketing automation

The `hubspot.marketing` integration covers newsletters, automated marketing
emails, campaigns, subscription preferences, and email drip workflows. It uses
the existing `httpx` dependency. These APIs are available in the source tree
after this change; the previously published Zeocore 0.9.0 does not contain them.

Run the credential-free example:

```bash
python examples/hubspot_usage.py
```

It invokes registered capabilities through the real client and a simulated HTTP
boundary. Its output explicitly says that it did not send mail.

## Account and scopes

Provision a HubSpot private-app access token, or supply an OAuth access token
managed by your application. Set `HUBSPOT_ACCESS_TOKEN` through your environment
or secret manager. Never put it in an agent prompt, a publication proposal, or a
receipt. The integration does not persist tokens or refresh OAuth tokens.

| Operations | API family | Required access |
|---|---|---|
| Draft, retrieve, clone, update, statistics | Marketing emails, `2026-03` | Appropriate marketing email read/write scopes |
| Publish, schedule, cancel | Marketing emails, `2026-03` | `marketing-email` or `transactional-email`; Marketing Hub Enterprise or transactional email add-on |
| Campaigns, assets, campaign metrics | Campaigns, `2026-03` | `marketing.campaigns.read`; also `marketing.campaigns.write` for changes; Marketing Hub Professional or higher |
| Subscription types and preferences | Communication preferences, `2026-03` | `subscriptions-definition-read`, `subscriptions-status-read`, `subscriptions-status-write` as needed |
| Email workflows | Workflows v4 beta; v2 enrollment | `automation`, plus account entitlement for automated marketing email workflows |

Provider entitlements and granted scopes are enforced by HubSpot. A configured
client is not proof of access. A 403 result names the scope/tier check instead of
falling back to a different kind of email. The integration does not use the
transactional single-send endpoint to bypass newsletter subscription rules.

References: [marketing email guide](https://developers.hubspot.com/docs/api-reference/latest/marketing/marketing-emails/guide),
[campaign guide](https://developers.hubspot.com/docs/api-reference/latest/marketing/campaigns/guide),
[subscription guide](https://developers.hubspot.com/docs/api-reference/latest/communication-preferences/guide),
[workflow guide](https://developers.hubspot.com/docs/api-reference/legacy/automation/workflows/guide).

## Load and discover

```python
from zeo_core.integrations.hubspot import HubSpotIntegration
from zeo_core.tools import CapabilityRegistry
from zeo_core.tools.builtin.hubspot import register_capabilities

integration = HubSpotIntegration()
configured = integration.initialize()
if not configured.success:
    raise RuntimeError(configured.error)

registry = CapabilityRegistry()
register_capabilities(registry)
# The host supplies {"hubspot.marketing": integration} in ToolContext.services.
# Use registry manifests with the existing LLM/MCP adapters.
# Close the integration when the host shuts down.
```

The integration is also discoverable through the `zeo_core.integrations` entry
point named `hubspot.marketing`. Capability registration is an explicit opt-in.
Declarations describe effects; the controlling application's admission mechanism
still decides whether a proposed effect may execute. `confirm=True` records an
explicit request but is not a substitute for the host's approval policy.

## Newsletter lifecycle

1. Create `EmailDraft` with name, subject, sender, template content, office
   location and subscription type. `Audience` takes existing contact IDs and
   current ILS segment IDs, including exclusions. Empty audiences are permitted
   while drafting. Duplicates and conflicting inclusions/exclusions are rejected.
2. Invoke `hubspot.marketing.email.save@1.0.0`, or call
   `integration.client.create_email(draft)`. The result contains the provider ID.
   Template-specific HTML belongs in `EmailContent.widgets` or `flex_areas`;
   `plain_text` supplies the plain-text version. A template path alone does not
   establish the rendered design or unsubscribe/footer content.
3. Review the actual HubSpot render, audience, subscription, sender and schedule.
   Fetch `get_email(id)` and retain its `updatedAt` as the reviewed revision.
   Update only unpublished drafts with that revision, or clone an earlier issue.
4. Supply `PublishRequest` with that revision, the approved send-specification
   digest and render reference described below, audience policy, subscription,
   and `confirm=True`. `send_at` must be a future timezone-aware datetime;
   omission requests immediate delivery for a newsletter. The client rechecks
   the provider revision, type, audience and suppression settings, updates send
   settings, re-reads and checks the send specification, then calls `/publish`.
5. A successful publish endpoint returns **204, with no body**. That acknowledges
   the API action; it does not establish delivery. Retrieve the email again for
   current state and `stats`. `cancel_email` may cancel a schedule, but HubSpot
   may refuse once sending has started.

Preflight is not an atomic lock: HubSpot exposes no compare-and-swap contract
here. The application must serialize its writes. A controlled-editor test portal is
the initial operating profile; this client cannot prevent privileged dashboard
changes during approval or execution. The declared concurrency mode
helps a host schedule invocations; it does not create a distributed lock.

## Campaigns, subscribers, and sequences

`create_campaign(CampaignProperties(properties={"hs_name": "Weekly newsletter"}))`
creates a campaign. Update properties, associate a `MARKETING_EMAIL`, `AUTOMATION_PLATFORM_FLOW`, or
`OBJECT_LIST`, retrieve those assets, and read campaign metrics. Campaign IDs
and email IDs are distinct. A campaign groups assets; creating one sends no mail.

`subscription_types()` returns the account's subscription definitions.
`subscription_status(email)` queries an address. `update_subscription` accepts
`SUBSCRIBED` or `UNSUBSCRIBED`. Opt-in requires an explicit legal basis, explanation and an independently
recorded consent evidence reference resolved by the host. It never infers consent from list membership.
Optional brand reads preserve `business_unit_id=0`; writes identify the actual
subscription ID. General contact creation, CRM records, deals, pipelines, tickets,
and sales Sequences are outside this integration. Audience management uses
existing HubSpot contact/segment identifiers; it does not provide a CRM facade.

For a welcome series, create automated `EmailDraft` objects (`kind="automated"`),
review them, and activate them with `PublishRequest(kind="automated")`. Then use:

```python
from zeo_core.integrations.hubspot import EmailSequence, SequenceStep

sequence = EmailSequence(
    name="Welcome series",
    steps=(
        SequenceStep(email_id="123"),
        SequenceStep(email_id="124", delay_minutes=1440),
    ),
)
# result = integration.client.create_sequence(sequence)
```

Sequences compile to email and delay actions, are created disabled, and use
manual enrollment with re-enrollment disabled. To edit, activate, or pause, call
`update_sequence` with the full sequence and current `revision_id`. Activation
requires confirmation and `email_versions`, a mapping of every referenced email
ID to its reviewed `updatedAt`. All must be published nontransactional automated
emails. To enroll an existing subscriber, use `enroll(flow_id, email,
revision_id=reviewed_revision, email_versions=reviewed_versions, confirm=True)`;
to remove one, use `remove=True` and the current `revision_id`. Retrieved
workflows must match the bounded linear, manual-enrollment subset, including
action versions, edges, suppression and trigger settings. Unsupported definitions
are refused before update, activation, enrollment or archive. Null-valued optional
provider settings and action decorations are tolerated; nonempty unknown behavior
and empty trigger objects still fail closed. Full workflow reads also require the
returned string ID to match the requested workflow before validating its graph
or revision. Missing, malformed or mismatched IDs stop updates, activation,
enrollment, metrics and archive after the first GET, with a sanitized response
error and no follow-up request. Unenrollment is deliberately narrower:
use the `workflow_identity` read to review the current revision, then remove the
contact. It requires the returned workflow ID to match the requested ID before exposing
metadata or mapping an unenrollment. Missing, malformed or mismatched IDs fail
with a sanitized response error before any mapping or deletion. It validates
contact-workflow identity and revision without requiring the
entire action graph to remain within our authoring subset.
Agent capability IDs are `hubspot.marketing.workflow.save@1.0.0` and
`hubspot.marketing.workflow.enrollment@1.0.0`; read operations use `workflow`,
`workflows` and `workflow_metrics`. These never call the Sales Sequences API. The client resolves the v4 flow ID to the v2 workflow ID before
enrollment. Missing, partial or ambiguous mappings fail before the effect.

## ZeoCreator and Sovereign Agent

ZeoCreator produces provider-neutral `ProposedPublicationOperation` objects.
The controlling application consumes those proposals and invokes Zeocore. Keep
this boundary: provider execution does not belong inside editorial contracts.

An application can start with `zeo_creator.registry.capability_registry()` and
call `register_capabilities(registry)` on that registry. Editorial capabilities
and the eleven HubSpot capabilities then share the same Zeocore invocation and
tool projection interfaces. Supply `HubSpotIntegration` through the host context.

For a newsletter proposal, set its destination provider to `hubspot.marketing`
and preserve its organization, publication, assignment, connection, destination,
artifact, approval digest and idempotency key. The host verifies those bindings
and the current artifact bytes, maps approved content to `EmailDraft`, and records
the resulting HubSpot email ID against the proposal. It must separately admit
the reviewed publish effect. Record API acceptance and later reconciliation as
different facts. Never treat a provider response as Sovereign Agent acceptance
of the original assignment.

Sovereign Agent's current public handoff example explicitly stops before generic
external-receipt acceptance. These capabilities do not invent that missing
runtime mechanism. They supply the real provider execution boundary for an
application-owned bridge. [Existing handoff example](https://github.com/profrodai/sovereign-agent-resources/tree/main/examples/sovereign-agent-zeocreator-handoff)

## Failure and retry behavior

All lists return one bounded page with `next_after` and `complete`. The latter
is true only when a first-page request has no continuation; a later final page
alone is not complete. Neither is a stable snapshot across provider mutations.
Callers choose whether to continue and must never infer absence from an
incomplete listing, especially after an unknown create outcome. Provider pagination URLs are ignored. No operation automatically
retries. 401 requires reauthorization; 403 requires scopes/tier investigation;
429 includes a numeric `retry_after_seconds` when available. Transport failures,
invalid success bodies and mutation 5xx responses carry `outcome_unknown=True`.
Reconcile before retrying: blind replay can duplicate a draft, subscription
effect, enrollment or send. Hosts should durably bind proposal idempotency keys
to attempts and provider IDs. This client does not claim exactly-once delivery.

The endpoint/schema contract was checked on 2026-09-07 against
[HubSpot's published API specifications](https://github.com/HubSpot/HubSpot-public-api-spec-collection).
Live account entitlements, actual email rendering and delivery require a
configured test portal; the repository gate uses injected transport responses.

## Approval and hosted execution limits

`PublishRequest` requires `expected_send_spec_sha256` and `render_evidence_ref`.
After the operator reviews the actual rendered email, compute
`send_spec_digest(email_record.data, send_at=approved_time,
audience_mode=approved_mode)` and bind it to the host's approval record. The
comparison covers the full returned email record except `updatedAt`, `stats`,
`sendOnPublish`, and `publishDate`; the desired schedule is included separately.
The client compares it before configuration and after a second provider read.
It also verifies that the configured send settings match the request. The host
must resolve and authenticate the render evidence reference; a model-generated
reference or a digest computed during execution is not approval.

There is still a race between the final read and bodyless publish. Templates,
remote assets and personalized content can also change outside the email record.
A test demonstrates an editor changing content after the final read and before
publication. This is evidence of a limitation. Initial live use requires a
restricted test portal, controlled editors and a designated test audience.
Concurrent-editor safety and exact rendered-byte delivery are not claimed.

`audience_mode="fixed_contacts"` is the default and refuses included OR excluded
segment IDs. It binds the explicit contact IDs, not their mutable address values
or their continued eligibility. Provider suppression may reduce delivery.
Segment use requires `audience_mode="dynamic_segments"` and an
`audience_policy_ref` resolved by the host to explicit authorization. This policy
permits membership evaluation by HubSpot at execution, including changed
membership after approval. Bounds are the specified segment IDs; there is **no
enforceable recipient-count cap or snapshot guarantee**. A policy requiring
an exact recipient set or a maximum count cannot authorize this mode. The initial
live fixture must use fixed designated contacts and controlled contact records.

Subscription opt-in additionally requires `consent_evidence_ref`. The host must
resolve an independently recorded consent/basis record and separately authorize
subscribe or re-subscribe; caller-supplied explanation text is insufficient.
That reference is not sent to HubSpot. Send and enrollment failures never trigger
an automatic subscription update. Global, brand and subscription-specific opt-outs
are distinct provider states; a subscription write never certifies that global
suppression has disappeared. None of these input checks determines legal compliance.

## Scheduled work and revocation

Scheduling and workflow activation leave work with HubSpot. Treat these as three
separate operations: deny new local authorization, cancel or pause existing
provider work and reconcile it, then revoke credentials. Where safe, attempt
cancellation before removing the credentials needed for it. A lost cancellation
response leaves an unresolved external commitment even after the local integration
closes or the connection is revoked. Persist the provider IDs, pending schedules,
workflow state and unknown outcome in the host journal and notify the operator.
Do not postpone emergency credential revocation indefinitely. Local closure and
credential revocation never mean all sending stopped. A 204 cancellation response
still needs provider-state reconciliation; delivery already in progress may remain.

The standard `httpx` and synchronous `httpcore` request logs are suppressed only
within this client's request context to avoid email-address paths and headers.
An injected transport, host HTTP tracing or third-party instrumentation must apply
its own URL/header redaction. Do not retain raw subscription/enrollment URLs in
receipts. Error messages alone are not the complete privacy boundary.

## API evidence and unresolved provider checks

The contract fixture records the upstream commit, path, Git blob hash and SHA-256
for each source. Every recorded endpoint method, success code, query parameter,
required field and permitted field was independently compared to the downloaded
blobs at commit `7f4f0c203d7895e594c9f60543dc0542b4f6305d` on 2026-09-07.
Parameter ordering is immaterial. This checks the snapshot provenance; it does
not prove that the live service obeys its schema.

Paths below are relative to `PublicApiSpecs/` in the
[pinned official collection](https://github.com/HubSpot/HubSpot-public-api-spec-collection/tree/7f4f0c203d7895e594c9f60543dc0542b4f6305d/PublicApiSpecs).
JSON pointers resolve within the named file.

| Question | Exact schema and pointer | Choice and remaining proof |
|---|---|---|
| Template nesting | `Marketing/Marketing Emails/Rollouts/145892/2026-03/marketingEmails.json`, `/components/schemas/EmailCreateRequest/properties/content` → `PublicEmailContent`, `/components/schemas/PublicEmailContent/properties/templatePath` | Use `content.templatePath`; the marketing guide's root-level example conflicts. Live creation and rendering pending. |
| Schedule versus send | Same email file, `/components/schemas/EmailUpdateRequest/properties/publishDate` and `/properties/sendOnPublish`; `/paths/~1marketing~1emails~12026-03~1{emailId}~1publish/post/responses/204` | PATCH approved settings, re-read, bodyless publish. Acceptance/schedule execution remain live tests. |
| String audience IDs | Same email file, `/components/schemas/PublicEmailRecipients/properties/include/items/type` and `/properties/exclude/items/type` | Both string; request models and wire assertions retain strings. |
| Create versus PUT | `Automation/Automation V4/Rollouts/144908/v4/automationV4.json`, `/components/schemas/ApiContactFlowCreateRequest` versus `/components/schemas/ApiContactFlowPutRequest` | PUT omits create-only fields despite the guide's broader example. Preserve supported description/UUID; refuse unknown behavior instead of dropping it. Live PUT pending. |
| Manual criteria | Same workflow file, `/components/schemas/ApiManualEnrollmentCriteria` | Schema supports MANUAL, while the guide's enrollment reference does not establish it. First live workflow validation item. No automatic fallback to list-based enrollment. |
| Workflow ID mapping | Same workflow file, `/paths/~1automation~1v4~1workflow-id-mappings~1batch~1read/post` | Resolve FLOW_ID to unique positive integer workflowId before v2 enrollment; live mapping remains unverified. |
| Campaign asset names | Campaign schema leaves assetType unconstrained; [guide asset-type table](https://developers.hubspot.com/docs/api-reference/latest/marketing/campaigns/guide#list-assets) supplies semantics | Only MARKETING_EMAIL, AUTOMATION_PLATFORM_FLOW, OBJECT_LIST. EMAIL is sales email; WORKFLOW is unsupported. |

The 2026-03 version remains intentionally pinned. Principal Zeocore owns the
sunset/drift watch: inspect HubSpot deprecation notices and the used schemas
before each Zeocore release and monthly, next due 2026-10-07. Newer 2026-09
rollouts are not an instruction to silently migrate. A version change requires
schema comparison, focused tests and a live test-portal check. Beta workflow
validation stays a separate acceptance item; the requested workflow scope has
not been removed or replaced by undocumented fallback behavior.
