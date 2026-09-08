# Kit account setup

**Reviewed:** 2026-09-08. Integration: `kit.marketing`. No extra dependency beyond
ZeoCore. Read [environment setup](environments.md) first; the operational API and
approval rules are in [Kit marketing](../tutorials/kit-marketing.md).

## Get the right credential

Use a **Kit API v4 key** for automation of your own creator account. Sign in at
[Kit](https://app.kit.com), open **Settings → Developer**, and use **Add a new key**.
Name it `zeocore-test` or `zeocore-production`, then save the displayed key in your
secret manager: it is only shown at creation. The integration's variable is
`KIT_API_KEY`, not the older v3 API secret. Kit uses `X-Kit-Api-Key` for v4 keys.
[Official key instructions](https://developers.kit.com/api-reference/authentication).

For an app used by other creators, create an app, enable API access, register your
exact OAuth callback and implement the authorization-code/refresh flow in your
host. Supply the resulting access token as `KIT_ACCESS_TOKEN`. Do not supply the
OAuth client ID, client secret, authorization code or refresh token as the access
token. Public App Store integrations require OAuth; a personal API key is not a
substitute. ZeoCore consumes tokens and does not host the OAuth callback or refresh
them. Configure exactly one of the two credentials.
[Official app setup](https://developers.kit.com/kit-app-store/building-apps).

## Test account track

This implementation does not assume a Kit sandbox endpoint or special test key.
Use a dedicated creator account for ZeoCore testing. If account creation or API
access requires an eligible plan, complete that in Kit before proceeding; creating
a key does not prove endpoint entitlement. Do not clone your real subscriber list.

1. Create/sign into the dedicated test creator account and confirm its account
   identity in the UI before creating `zeocore-test`.
2. Configure its sender identity and physical mailing address using Kit's account
   settings. Complete sender/domain verification required by the account.
3. Add only operator-controlled designated recipients with recorded consent. Do
   not import unknown addresses or use a public test tag in the real account as
   equivalent isolation.
4. Prepare the test environment and place the script below at an absolute path.
5. Run the command with the test key prompt. A successful read confirms access to
   that account endpoint; it does not prove sending is enabled.

Save as `check_kit.py`:

```python
from zeo_core.integrations.kit import KitIntegration

kit = KitIntegration()
try:
    configured = kit.initialize()
    if not configured.success:
        raise SystemExit(configured.error)
    account = kit.client.account()
    if not account.data:
        raise SystemExit("Kit returned no account data")
    print("Kit account read succeeded; verify identity in the account dashboard")
finally:
    kit.close()
```

```bash
python -m zeo_core.integrations.environments --mode test   --root "$ZEO_ENV_ROOT" --integration kit.marketing --secret KIT_API_KEY   -- python /absolute/path/check_kit.py
```

For CI use `ZEO_TEST_KIT_API_KEY`, or `ZEO_TEST_KIT_ACCESS_TOKEN` with OAuth.
Tokens for a separate test account are still real, privileged credentials.

## Production account track

Sign into the actual publishing account, confirm its brand/sender and API plan,
and create a separate production key or authorize the production OAuth app.
Store it as `ZEO_PRODUCTION_KIT_API_KEY` or `ZEO_PRODUCTION_KIT_ACCESS_TOKEN`.
Prepare `production/config/` and record production template, sender, subscriber,
sequence and tag IDs there. Do not reuse the test account's IDs or caches.

Run the same harmless script with `--mode production` and the production prompt:

```bash
python -m zeo_core.integrations.environments --mode production   --root "$ZEO_ENV_ROOT" --integration kit.marketing --secret KIT_API_KEY   -- python /absolute/path/check_kit.py
```

For a public integration, finish the host's OAuth and App Store requirements
before production rollout. The runtime environment does not perform that approval.

## Bounded E2E and cleanup

First run the [offline example](../../examples/kit_usage.py) with `--fixture`.
Then, in the test account, create a private draft named `ZEO TEST <run-id>` with
synthetic content. Read it back, review its digest, sender and exact designated
audience, and invoke the reviewed send capability from the marketing tutorial.
The API creates a **new send object**; record its ID separately from the source
draft. Check that object's provider status and the designated recipient's inbox.
A 2xx response alone is not delivery evidence.

Validate private POST scheduling/immediate-send behavior first, then sequence
partial updates and reviewed activation. No documentation-only claim resolves
those live contract qualifications. Use one designated subscriber for a sequence,
observe each step, then pause it. Archive/delete only objects created by this run.
Do not use global unsubscribe as a substitute for per-sequence removal; the
integration intentionally does not invent that unsupported operation.

## Troubleshooting and rotation

- Missing key: check the v4 Developer tab, account role and plan; v3 credentials
  cannot be used with these endpoints.
- Ambiguous auth: remove one of `KIT_API_KEY`/`KIT_ACCESS_TOKEN` from the selected
  namespace. The integration rejects both together.
- 401: reset/replace the selected key or repair the host's OAuth refresh flow.
- 403 or unavailable operation: inspect endpoint authentication requirements and
  account entitlement. Switching to production is not a repair for a failed test.
- Timeout/unknown send outcome: reconcile the provider's send objects before a
  retry; do not risk a duplicate newsletter.

In **Settings → Developer**, edit the named key to reset or delete it. Reset
invalidates the old value; update only the correct namespace and rerun the read
check. For OAuth, revoke the installed app/authorization and repair custody in the
host. Reconcile queued sends before removing credentials needed to cancel them.
[Key reset/deletion reference](https://developers.kit.com/api-reference/authentication).
