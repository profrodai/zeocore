# Bluesky account setup

**Reviewed:** 2026-09-08. Integration: `social.bluesky`. Install with
`uv pip install -e ".[bluesky]"`. Start with [environment setup](environments.md)
and the [Bluesky API tutorial](../tutorials/bluesky-integration.md).

## Obtain an app password

Create/sign into the intended account at [Bluesky](https://bsky.app). Open
**Settings → Privacy and security → App passwords**, or the direct
[App passwords page](https://bsky.app/settings/app-passwords), and add a named app
password. Save it when shown. Use an app password for this integration rather than
the account's main login password. App passwords are independently revocable.
[Bluesky's explanation](https://bsky.app/profile/safety.bsky.app/post/3k7waehomo52m).

Supply `BLUESKY_IDENTIFIER` as the full account handle or supported login identifier,
and `BLUESKY_APP_PASSWORD` as the generated password. The default PDS service is
`https://bsky.social`; for an account hosted elsewhere, provide its actual PDS in
`BLUESKY_SERVICE_URL`. An arbitrary API hostname is not interchangeable with the
account's home PDS. The managed credential cache lives at
`<state>/credentials/bluesky/bluesky_credentials.json`.

## Test account track

Use a separate Bluesky account clearly labeled as a test account. This integration
does not assume a private Bluesky sandbox: posts on the public network can be seen
by others, even if their title begins with TEST. Use synthetic content, no mentions
of real people and no imported production audience. For a self-hosted test PDS,
follow that deployment's account creation and federation settings explicitly.

Create `zeocore-test` as an app password on that account. Supply
`ZEO_TEST_BLUESKY_IDENTIFIER` and either the password prompt or
`ZEO_TEST_BLUESKY_APP_PASSWORD`. Save `check_bluesky.py`:

```python
from zeo_core.integrations.social.bluesky import BlueskyIntegration

service = BlueskyIntegration()
result = service.initialize()
if not result.success:
    raise SystemExit("Bluesky login failed; check account, PDS and app password")
print("Bluesky session initialized; no post was created")
```

```bash
ZEO_TEST_BLUESKY_IDENTIFIER="your-test-handle.bsky.social" python -m zeo_core.integrations.environments   --mode test --root "$ZEO_ENV_ROOT" --integration social.bluesky   --secret BLUESKY_APP_PASSWORD -- python /absolute/path/check_bluesky.py
```

Initialization authenticates or loads the selected account session; it does not
publish anything. Verify the account identity in the provider UI before posting.
A cached session is configuration evidence, not proof of a newly accepted login.

## Production account track

Sign into the actual brand account and create a different production app password.
Use `ZEO_PRODUCTION_BLUESKY_IDENTIFIER`, `ZEO_PRODUCTION_BLUESKY_APP_PASSWORD` and,
if needed, `ZEO_PRODUCTION_BLUESKY_SERVICE_URL`. Run the harmless check with
`--mode production`. Its cache and Keychain-independent credential file are separate
from test. Never copy the test session file into the production credential tree.

## Bounded E2E and cleanup

On the test account, invoke `service.post("ZEO TEST <run-id>: synthetic integration check")`
once. Check success, record its URI/CID, and view the actual post in the test profile.
API acceptance alone is not the visual verdict. Delete that post through the
Bluesky UI when finished; the current service only exposes posting, so do not claim
an unimplemented delete method exists. The provider tests use controlled clients
and require no real account; they are the fixture track, not public posting proof.

## Troubleshooting and rotation

401: confirm the full handle, PDS and app password; do not use the main password or
blindly retry. If a cached account is wrong, revoke the app password and retire only
the selected environment's credential file before logging in again. 429: observe
provider rate limits rather than creating a retry loop. If profile visibility is
missing, inspect the actual post URI and moderation/account state.

In App passwords, create a replacement, update the selected namespace and rerun
authentication. Delete the old app password and retire its selected cache when no
longer needed. Keep the production account password outside this integration.
