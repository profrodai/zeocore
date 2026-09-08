# HubSpot marketing account setup

**Reviewed:** 2026-09-08. Integration: `hubspot.marketing`. No extra dependency
beyond ZeoCore. Read [environment setup](environments.md), then the
[marketing API tutorial](../tutorials/hubspot-marketing.md).

## Test account track

HubSpot provides developer test accounts. In HubSpot go to **Development →
Testing → Test Accounts → Create developer test account**, name it `ZeoCore Test`,
and open that account. This is distinct from a production portal and from an
Enterprise account's standard sandbox. Developer test accounts have trial features
and limitations: marketing email can only go to users added to that developer test
account. Add your designated recipient as an account user before testing delivery.
Manage trial renewal from the test account's Actions menu; do not assume perpetual
production-equivalent entitlement.
[Official account types and creation](https://developers.hubspot.com/docs/getting-started/account-types).

Before obtaining a token, confirm the test portal's account ID in HubSpot's account
switcher. Create all templates, sender settings, subscription types, office address
settings, campaigns and designated test contacts inside that portal. Provision
contacts through the UI; ZeoCore's integration intentionally does not expose CRM
management operations.

## Obtain a portal access token

For a single account, use a private/static app access token. The documented legacy
UI path is **Development → Legacy apps → Create legacy app → Private**; a super
admin is required. Give it an environment-specific name, select scopes, create the
app, then open its Auth tab and copy the access token. HubSpot also offers the new
project-based static-auth flow; follow that flow's installation/token instructions
if your account uses it. A developer API key or CLI personal access key is **not**
the portal bearer token required here.
[Private app creation and token access](https://developers.hubspot.com/docs/apps/legacy-apps/private-apps/overview),
[new authentication options](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/overview).

Supply `HUBSPOT_ACCESS_TOKEN`. For a public/multi-account app, your host must finish
OAuth authorization and refresh-token custody, and pass the resulting access token
for the selected portal. ZeoCore does not implement the browser callback or token
refresh. [Official OAuth flow](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/oauth/working-with-oauth).

## Scopes and product access

Select only the marketing operations you will run:

| Surface | Access to configure |
|---|---|
| Marketing email | Marketing email read/write access; publishing uses `marketing-email` or the documented qualifying entitlement |
| Campaigns | `marketing.campaigns.read`; add `marketing.campaigns.write` for changes |
| Subscription definitions | `subscriptions-definition-read` |
| Subscription status | `subscriptions-status-read`; add `subscriptions-status-write` for changes |
| Marketing workflows | `automation`, plus automated-email/workflow product entitlement |

The [marketing tutorial's access table](../tutorials/hubspot-marketing.md#account-and-scopes)
and its endpoint references describe the additional Marketing Hub/add-on requirements.
Read the scopes shown for the specific current endpoint and the app's granted
permissions. Missing scope options can mean missing product access. Adding CRM or
sales-Sequences scopes will not fix a marketing entitlement problem. We do not use
transactional sending to evade newsletter subscription rules.

## Harmless first check

Save `check_hubspot.py`:

```python
from zeo_core.integrations.hubspot import HubSpotIntegration, PageRequest

hubspot = HubSpotIntegration()
try:
    configured = hubspot.initialize()
    if not configured.success:
        raise SystemExit(configured.error)
    page = hubspot.client.list_emails(PageRequest(limit=1))
    print("Marketing email read succeeded; returned", len(page.results), "record(s)")
finally:
    hubspot.close()
```

```bash
python -m zeo_core.integrations.environments --mode test   --root "$ZEO_ENV_ROOT" --integration hubspot.marketing   --secret HUBSPOT_ACCESS_TOKEN -- python /absolute/path/check_hubspot.py
```

Use the token from the **developer test portal**. For CI supply
`ZEO_TEST_HUBSPOT_ACCESS_TOKEN`. Successful initialization only configures the
client; the GET is the first actual access check. An empty email list is valid.

## Production account track

Open the real brand's portal, verify its account ID and product subscriptions,
and create a separately named private/static app or authorize the production OAuth
app. Store its token as `ZEO_PRODUCTION_HUBSPOT_ACCESS_TOKEN`. Recreate/review the
production template, subscription-type, office-location, contact/list, campaign and
workflow IDs in the production resource configuration. IDs from the test portal
must not be assumed valid in production.

Run the same script with `--mode production` and the production token prompt.
Confirm sender/domain setup and actual Marketing Hub entitlements in the portal
before enabling any publish or enrollment capability. A test account's trial access
is not evidence that the production account has the same features.

## Bounded E2E and cleanup

Run the [offline example](../../examples/hubspot_usage.py) under `--fixture` first.
For live validation, create a draft labeled `ZEO TEST <run-id>` inside the developer
portal, using the approved template, valid footer and one designated account user.
Read and preview it, record render evidence and approved audience/digest, then use
the reviewed publishing path in the marketing tutorial. Confirm provider state and
the recipient's actual inbox. Review mobile rendering and unsubscribe behavior.

For a drip workflow, create a disabled manual-enrollment sequence using published
nontransactional automated emails. Read it back and verify identity/revision/graph.
Validate MANUAL beta acceptance and workflow-ID mapping in the test portal before
activation or enrollment. An unsupported beta feature must fail; there is no silent
list-trigger or CRM fallback. After the test, pause/cancel eligible work, remove the
designated enrollment where supported, and archive only this run's artifacts.
Provider-queued effects may outlive the local process.

## Troubleshooting and rotation

- Cannot find app/token controls: verify super-admin permission, current portal,
  and the legacy versus project-based app route.
- 401: repair/reissue the token for this portal; do not retry credentials blindly.
- 403: check granted scopes, account tier, add-ons and endpoint beta availability.
- No delivered test email: first check developer-account recipient restrictions,
  suppression/subscription eligibility, provider state, sender setup and spam.
- Workflow rejected: inspect MANUAL beta support and the supported graph subset;
  do not widen the integration to CRM or sales-Sequences.

Rotate/revoke the named app's token in its Auth controls, update only the selected
namespace, restart and rerun the harmless GET. OAuth revocation/refresh belongs to
the host's installed-app custody. Retain enough authorized access to reconcile or
cancel outstanding provider work before revoking the token.
