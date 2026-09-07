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
4. Supply `PublishRequest` with that revision, the exact audience and subscription,
   and `confirm=True`. `send_at` must be a future timezone-aware datetime;
   omission requests immediate delivery for a newsletter. The client rechecks
   the provider revision, type, audience and suppression settings, updates send
   settings, then calls `/publish`.
5. A successful publish endpoint returns **204, with no body**. That acknowledges
   the API action; it does not establish delivery. Retrieve the email again for
   current state and `stats`. `cancel_email` may cancel a schedule, but HubSpot
   may refuse once sending has started.

Preflight is not an atomic lock: HubSpot exposes no compare-and-swap contract
here. The application must serialize writes to an email and prevent concurrent
editor changes during approval and execution. The declared concurrency mode
helps a host schedule invocations; it does not create a distributed lock.

## Campaigns, subscribers, and sequences

`create_campaign(CampaignProperties(properties={"hs_name": "Weekly newsletter"}))`
creates a campaign. Update properties, associate an `EMAIL`, `WORKFLOW`, or
`OBJECT_LIST`, retrieve those assets, and read campaign metrics. Campaign IDs
and email IDs are distinct. A campaign groups assets; creating one sends no mail.

`subscription_types()` returns the account's subscription definitions.
`subscription_status(email)` queries an address. `update_subscription` accepts
`SUBSCRIBED` or `UNSUBSCRIBED`. Opt-in requires an explicit legal basis and an
explanation supplied by the caller. It never infers consent from list membership.
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
requires confirmation and published nontransactional automated emails. To enroll
an existing subscriber, use `enroll(flow_id, email, confirm=True)`; to remove one,
use `remove=True`. The client resolves the v4 flow ID to the v2 workflow ID before
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

All lists return one bounded page with `next_after`; callers choose whether to
continue. Provider pagination URLs are ignored. No operation automatically
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
