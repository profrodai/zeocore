# Kit newsletters and marketing sequences

For credential creation, test accounts, production accounts and environment-isolated
execution, follow the [account setup guide](../integrations/kit.md) first.
The direct-constructor examples below also work outside the managed launcher;
use the launcher when you need its separation guarantees.

Kit marketing is a first-class provider alongside [HubSpot](hubspot-marketing.md).
It provides thirteen explicit agent capabilities for broadcasts, sequence authoring,
subscriber consent, tags, segmentation reads and marketing metrics. It uses the
existing `httpx` dependency. These APIs are in this source revision; the previously
published Zeocore 0.9.0 does not contain them.

Run `python examples/kit_usage.py` for a credential-free example that invokes the
real registry, client and HTTP boundary with simulated responses. It sends no mail.

## Configure and register

Set exactly one secret through the host environment or secret manager:
`KIT_API_KEY` for a personal Kit v4 API key, or `KIT_ACCESS_TOKEN` for an app OAuth
access token managed by your host. API keys use `X-Kit-Api-Key`; OAuth uses
`Authorization: Bearer`. The integration never persists or refreshes tokens.
V3 keys are incompatible. Never put credentials in prompts or operation receipts.

```python
from zeo_core.integrations.kit import KitIntegration
from zeo_core.tools import CapabilityRegistry
from zeo_core.tools.builtin.kit import register_capabilities

integration = KitIntegration()
configured = integration.initialize()
if not configured.success:
    raise RuntimeError(configured.error)
registry = CapabilityRegistry()
register_capabilities(registry)
# Supply {"kit.marketing": integration} in ToolContext.services.
# Close integration when the host shuts down.
```

`kit.marketing` is also a `zeo_core.integrations` entry point. Initialization
configures a client; it does not verify authentication or account entitlements.
Read `account`, `templates`, and `segments` before preparing a campaign. Choose a
verified sending address and a supported HTML template explicitly. Kit's
“Starting point” templates are not supported by broadcast API creation. Account
plan restrictions and sender verification remain provider checks; a 403 cannot be
fixed by changing subscription state or switching to another email channel.

Kit documents rate limits of 120 requests per rolling 60 seconds for API keys and
600 for OAuth. This client does not retry automatically. See
[authentication](https://developers.kit.com/api-reference/authentication).

## Available agent operations

All IDs below have the prefix `kit.marketing.` and suffix `@1.0.0`.

| Capability | Behavior |
|---|---|
| `read` | Account, templates, segments, broadcasts and stats/clicks, sequences and stats/full snapshots, emails, subscribers and tag memberships |
| `broadcast.save` | Create or edit a private, unscheduled draft |
| `broadcast.send` | Create a new immediate or scheduled send from an approved source draft |
| `sequence.save` | Create or edit a paused sequence with sender, schedule, exclusions, repeat and hold settings |
| `sequence.email.save` | Create or edit an unpublished email in a paused sequence |
| `sequence.email.publish` | Explicitly publish/unpublish a reviewed email in a paused sequence |
| `sequence.state` | Activate a reviewed full sequence, or pause its reviewed settings |
| `sequence.enroll` | Enroll an existing active subscriber in a reviewed active sequence |
| `subscriber.create` | Upsert a marketing subscriber, inactive by default; active creation needs independent consent evidence |
| `subscriber.unsubscribe` | Unsubscribe a reviewed subscriber from all future Kit email |
| `tag.save` | Create or rename a tag for campaign organization |
| `tag.membership` | Add/remove an existing subscriber, with approval for possible Visual Automation triggers |
| `delete` | Delete a reviewed draft/scheduled broadcast, sequence, or email in a paused sequence |

Kit has no separate campaign object in this surface. Organize campaign broadcasts
and audiences with names and tags. This integration exposes no purchases, sales
CRM facade, arbitrary API routes, or general Visual Automation graph authoring.

## Broadcast lifecycle

1. Create `BroadcastDraft` with subject, HTML content, sender, template ID and an
   explicit `Audience`. Choose a single logical group (`all`, `any`, or `none`)
   containing tag and/or segment IDs. Empty input fails. Sending to the entire
   account requires `Audience(entire_account=True)` explicitly.
2. Save the draft. Draft writes always set `public=False` and `send_at=None`.
   To edit an existing draft, fetch it, review it, and pass its `record_digest`
   as `expected_digest`. The client also requires the provider's draft delivery
   state. Drafts that are already public or scheduled cannot be edited here.
3. Review the actual Kit render, template, sender, unsubscribe/footer content,
   audience policy and schedule. Fetch the final source draft and compute
   `broadcast_send_digest(record.data, send_at=approved_time,
   publish_web=approved_web_publication)`. Bind that digest and authenticated
   render/audience evidence to the host's approval record.
4. Invoke `broadcast.send` with `SendBroadcast`, the approved digest, evidence
   references, `confirm=True`, and optionally a future timezone-aware `send_at`.
   Omission requests immediate sending. Web publication defaults to false and
   requires separate explicit `publish_web=True` authority bound into the digest.
5. **Track the returned new broadcast ID.** The client creates a new send object
   using the reviewed source draft's content, sender, template, filter and display
   metadata. The original remains a draft. A repeated send can create a duplicate;
   the host must record the attempt and returned ID durably before allowing replay.
6. Read `broadcast_metrics` and `broadcast_clicks` using the returned send ID.
   Cancellation uses explicit hard deletion of a draft/scheduled object. Deletion
   is permanent, is not reversible unpublish, and cannot undo delivery that began.

The new-object send uses Kit's create endpoint because its `send_at` contract
separates email delivery from the `public` flag's web-publication effect. Kit's
update prose currently says `public=true` is needed for scheduling, conflicting
with that distinction. Zeocore does not silently grant web publication to schedule
an email. Draft editing uses PUT with null `send_at`, matching the documented draft
semantics but differing from the update JSON schema's nonnullable string. This
specific API-contract discrepancy requires a live test-account check.

Audience membership remains dynamic until Kit resolves it. `none` is a complement
and may select most of the account. Neither a digest nor a bounded list supplies
a recipient cap or immutable recipient snapshot. The host must authorize this
policy explicitly. Template contents, account settings, suppression and consent
can change independently of the broadcast record and must be considered at review.

## Sequence lifecycle

Create a `SequenceDraft` with explicit sender/template, IANA timezone, nonempty
send days, hour 0–23, exclusions and repeat/hold choices. Creation is paused.
Fetch `sequence_snapshot` before each edit: it contains the sequence definition
and all email steps with HTML, bounded to 100. A partial page is refused. Sequence
stats and subscriber/email counts are excluded from the approval digest; the
actual email set is included. No claim of a transactionally stable snapshot is made.

Use `SequenceEmailDraft` with explicit zero-based position and delay. Only the
first day-based email may use zero delay. Hour delays must be positive and cannot
specify send days. Existing positions cannot be overwritten by inserting another
email. Editing demotes an email to unpublished. After reviewing its render, use
`sequence.email.publish` with the complete snapshot digest and confirmation.
Publish first, re-read/review the complete snapshot, then activate separately.
Activation requires at least one valid published email plus render and audience
policy evidence. A paused sequence can contain unpublished future steps.

Publishing a step, activating a sequence, repeat settings, or enrolling a reader
may affect already queued subscribers immediately. Pausing does not establish
that every queued provider action was cancelled. Changes to schedules do not
retroactively reschedule previously queued sends. For risk-reducing pause, review
the current sequence record and use its `record_digest`; an unreadable email graph
does not prevent pausing. Reconcile the result with Kit.

Enrollment requires a complete reviewed sequence digest, current subscriber-record
digest, independent host approval and explicit confirmation. It never creates a
subscriber or changes their consent. Kit's current v4 specification exposes no
per-subscriber sequence-removal endpoint. Global unsubscribe is a separate,
explicit operation; it is never substituted for sequence-only removal. Pausing or
deleting a sequence affects its broader audience and also needs explicit authority.

## Subscribers and tags

Creating a subscriber defaults to inactive. Active creation requires confirmation
and an independently recorded consent reference. The host must resolve that
reference; a model-written string is not consent. Kit upsert does not change an
existing subscriber's state. A successful response with `state=cancelled` remains
cancelled, even if the request asked for active. Never infer reactivation.

Unsubscribe acts across the account's future email, preserving history and tags.
Tag creation deduplicates names case-insensitively; rename keeps the ID. Both tag
addition and removal may trigger existing Kit Visual Automations, so both declare
external communication effects and require host approval. No subscriber is created
as a side effect of tag membership or sequence enrollment.

## ZeoCreator and Sovereign Agent host composition

Register Kit capabilities on the same `CapabilityRegistry` used by ZeoCreator,
including the registry returned by `zeo_creator.registry.capability_registry()`.
HubSpot and Kit coexist with distinct provider IDs and injected services. Use the
existing LLM/MCP projections; there is no second registry or provider SDK dependency.

The controlling host consumes ZeoCreator `ProposedPublicationOperation` objects,
binds organization/publication/assignment/connection/destination/artifact and
approval digest, and maps approved content to Kit drafts. Choose destination
provider `kit.marketing`. Preserve proposal idempotency keys and map each draft and
send to its distinct provider ID. Admit sending separately from drafting.
`confirm=True`, effect declarations and digest equality are input checks; they do
not implement host admission, independently authenticate evidence, or grant consent.

Use the application-owned bridge described in the
[HubSpot host boundary](hubspot-marketing.md#zeocreator-and-sovereign-agent).
These provider capabilities do not fill Sovereign Agent's separate generic
external-receipt acceptance mechanism. API acceptance, delivery reconciliation,
and assignment acceptance are different receipts.

## Failures, concurrency and acceptance

Lists return one bounded page with `next_after` and `complete`. Only a first page
without either preceding or following pages is complete. The client follows no
provider pagination URLs and never treats a later final page as the whole set.
Callers choose continuation and must not infer absence from partial data.

Transport failures, mutation 5xx responses, and malformed success responses report
`outcome_unknown=True`. Never automatically replay them: reconcile against Kit and
the host's durable attempt ledger. A 401 requires new authorization; a 403 requires
an access/plan check; a 429 includes numeric retry timing when present. Error
messages omit provider bodies and request credentials. Keyed mutation responses
must contain a strictly positive integer resource ID. Update and membership
responses must identify the requested target; a broadcast send must return a
new ID distinct from its source draft. Invalid response identity after dispatch
is an unknown outcome, including through agent capabilities; it never authorizes
automatic replay. Returned account/subscriber
records and email HTML remain sensitive data; the host controls their access,
retention and tracing. Injected HTTP transports must provide their own redaction.

The client uses no compare-and-swap or distributed lock. Serialize operations per
account/resource in the host and avoid simultaneous dashboard edits. There is a
race between preflight and the write. Revoking credentials or cancelling a local
invocation does not cancel a provider-accepted send or enrollment. Read back state
and use the explicit provider operations where still possible.

Tests use an independent subset of the official
[Kit v4 specification](https://developers.kit.com/api-reference/v4.json), retrieved
2026-09-07, source SHA256
`a8edeb6df018764cb7b7126185ac9bcf0d9c75bbb3917f2d0665adb4135c5e76`.
The fixture preserves upstream bytes for the selected operation definitions.
Two named test exceptions expose upstream inconsistencies: null `send_at` for a
PUT draft, and one logical audience group despite the schema marking all three
required. These are documented choices, not evidence of live provider acceptance.

Before production, validate drafts, rendered output, private scheduled-copy sending,
cancellation, sequence publication/activation/pause, enrollment, suppression,
consent and metrics in a controlled Kit account with an explicitly approved test
recipient. No live account, render or delivery is certified by the offline gate.
Principal Zeocore owns the API drift watch before each release and monthly, next
2026-10-07. Compare the saved schema with current Kit docs and repeat affected
behavior and live checks before adopting a changed contract.
