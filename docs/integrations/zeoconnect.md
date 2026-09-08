# ZEOconnect hosted account setup

<!-- Teaches CLAUDE.md Rev 17; user documentation reviewed 2026-09-08. -->

This optional composition surface uses a paired device session rather than a
provider API key in ZeoCore. Provider OAuth and token custody belong to
ZEOconnect. Start with [test and production environments](environments.md),
then follow the [complete pairing and service-resolution tutorial](../tutorials/zeoconnect-hosted-profile.md).
The current native slice supplies Drive, Docs and Bluesky bindings; it is not
a claim that every local integration is available through the hosted service.
Live operation also requires a compatible deployed ZEOconnect Member API.

## Offline test track

No account or key is needed. Inject `FakeGoogleDriveService` and use
`ExecutionProfile.FAKE` as shown in the tutorial. Use
`InMemorySecureSessionStore` for pairing protocol fixtures. Run those scripts
with `--mode test --fixture --integration zeoconnect` so fixture state and
outputs cannot be confused with a paired live test run. Assert the known fake
bytes and resolution/operation outcomes. These tests prove client composition,
not deployed membership, browser pairing or provider delivery.

## Live test account and pairing

1. Provision a separate test identity/member in the deployed ZEOconnect
   application at [connect.zeroemployee.org](https://connect.zeroemployee.org).
   If membership or the required connector is not available, that is a live
   prerequisite; no ZeoCore API key can bypass it.
2. In that identity's connection setup, authorize a dedicated provider test
   account, using the [Google](google.md) or [Bluesky](bluesky.md) account
   separation guidance. Select only disposable test resources. The OAuth
   browser must show the test account before consent is granted.
3. In your client application construct `KeychainSecureSessionStore` on macOS,
   `ZEOconnectHTTPTransport(session_store=store)`, and
   `build_hosted_runtime(transport=transport, session_store=store)`. The
   [tutorial's pairing code](../tutorials/zeoconnect-hosted-profile.md#hosted-pairing-is-an-explicit-second-action)
   shows the exact requirement, challenge, browser approval and polling calls.
4. Launch that application explicitly in test mode:

```bash
python -m zeo_core.integrations.environments --mode test   --root "$ZEO_ENV_ROOT" --integration zeoconnect --   python /absolute/path/your_pairing_application.py
```

Approve the displayed device code in the test member's browser session. Wait at
least the challenge's polling interval before each completion attempt. Pairing
stores a rotating device session, not provider credentials. Keychain entries
are separated by mode and a hash of the environment root; a production device
session is not loaded automatically into test mode. Keep that root stable for
a deployment. No global paired session is migrated into managed mode.

For a non-macOS host, inject a secure session-store adapter supplied by your
deployment, with separate namespaces for each mode/root. The native Keychain
adapter cannot work there. The in-memory adapter loses sessions on process exit
and is intended for fixtures; no plaintext fallback is provided.

## Production account and pairing

Provision the real production member and provider connection separately. Start
the same application with `--mode production` and the same environment root:

```bash
python -m zeo_core.integrations.environments --mode production   --root "$ZEO_ENV_ROOT" --integration zeoconnect --   python /absolute/path/your_pairing_application.py
```

Pair again in the production member's browser session and select production
resources explicitly. Do not copy the test device session. If several eligible
connections exist, present the returned selection state to the user; do not
choose the first account silently. Test mode uses the same deployed API unless
an explicitly configured localhost development transport is used. It does not
turn the hosted product into a vendor sandbox.

## E2E verification and cleanup

Start with a seeded selected Drive file. Resolve its requirement, complete
pairing, select the intended connection/resource, then download and compare the
known bytes. Verify the provider account and selected-resource display in the
application. Repeat in production with its own harmless resource. For mutations
use the application's explicit approval flow; pairing alone does not approve a
post or document change. An ambiguous effect must stop automatic dispatch.

Exercise device revocation and confirm the old session can no longer perform
operations. Re-pair only in the same intended mode. For cleanup, revoke the test
device and test provider connection in their respective account controls and
remove disposable provider artifacts. On a revoked/repair-required connection,
show that state; do not substitute another account. On protocol/version errors,
check the deployed server compatibility described in the tutorial. A successful
fake-server test does not establish that the production service is compatible.
