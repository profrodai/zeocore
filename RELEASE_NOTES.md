# zeocore 0.10.0

Current-source additions are listed under [Unreleased](CHANGELOG.md#unreleased).
The Runtime capability host and meeting-v1 adapters are not in the published
0.10.0 wheel; use the source installation in [provider registration](docs/how-to/provider-registration.md)
and the [meeting guide](docs/integrations/meetings.md). The release below remains 0.10.0.

ZeoCore 0.10.0 brings marketing automation, explicit integration environments,
governed image commissioning and receipt-bearing notebook authoring into one
release. Python 3.14 or newer remains required. The complete history is in
[CHANGELOG.md](CHANGELOG.md).

## Newsletter and marketing automation

HubSpot adds eleven registered agent capabilities for marketing email drafts,
reviewed publishing/scheduling, campaigns, subscription preferences and marketing
workflows. Its scope is marketing automation; it does not expose a general CRM
integration. Account entitlements, beta access and recipient restrictions still
apply. [HubSpot setup](docs/integrations/hubspot.md) explains test and real accounts,
private-app tokens, scopes, sender requirements and a bounded delivery check.

Kit adds thirteen registered capabilities for broadcasts, sequence authoring,
consent-bound subscribers, tags and reporting. Draft review binds the exact send;
mutation results must identify the correct resource. A lost or malformed response
remains uncertain rather than authorizing a blind retry.
[Kit setup](docs/integrations/kit.md) covers API v4 keys versus OAuth, dedicated
test accounts, designated recipients and production sender setup.

Both ship in the base package. Their runnable examples use explicit simulated
HTTP transports and send no real mail.

## Separate test and production environments

The managed launcher selects one provider namespace and separate configuration,
credential caches, working directories and temporary files. Secure prompts do not
echo or save secrets. Missing credentials cannot fall back to ambient keys or the
opposite track; managed live LLM calls cannot silently select a mock or another
provider. Fixtures are explicitly test-only and require injected test transports.

The [setup index](docs/integrations/README.md) links every supported service to
key acquisition, test-account creation, production setup, E2E checks and cleanup.
Providers without a sandbox use dedicated accounts/resources. Gemini images and
local notebook execution are now named launcher composition surfaces as well.

Identical Supabase project URLs across live tracks are refused even with distinct
keys. HTTP clients cannot replace a selected token with ambient netrc credentials.
Google Drive pagination now uses the real SDK keyword. Preserved HOME can still
expose third-party Google ADC/AWS credential files; the guide states that limit.
This is a boundary for trusted code, not an operating-system sandbox.

## Native ZEOconnect and Gemini images

Native fake and hosted profiles import without optional local Google/Bluesky SDKs.
Native ZEOconnect composition offers fake, local, hosted and governed profiles,
explicit pairing/session custody and consent-bound resolution. Governed authority
cannot fall back to an ordinary paired member session. Existing hosted request
revision fields remain optional for compatibility; the server derives its bound
revision from the authenticated connection.

Gemini reference-image operations use admitted connections, exact authorization,
durable dispatch markers, private hashed artifacts and read-only reconciliation.
Known interactions are recovered without a second generation POST. Lost responses
without a durable provider ID remain ambiguous. Returned images are unreviewed
candidates; provider acceptance does not establish artistic quality or zero cost.
[Gemini setup](docs/integrations/gemini-images.md) explains Google project/key
provisioning and separate test/production host custody.

## Document and notebook authoring

Jupytext and Pandoc expose conversion receipts, source/output identities and strict
staging batches. Notebook semantic digests carry a versioned schema and remain
separate from exact file hashes and individual execution observations.

The optional notebook executor creates a fresh Python kernel, removes stale output,
uses parent-enforced deadlines, bounds output capture and tracks observed process
cleanup. Receipts include interpreter/environment identity, declared lock provenance
and attempted/completed/failed/skipped cells. Worker results are published atomically
so a polling parent cannot see partially written JSON.

The [authoring reference](docs/integrations/authoring-reference.md) combines conversion,
independent fixture checks, parity, fresh execution and optional DOCX, with real runs
in separate test and production roots. Its receipts mean **staged, not published**.
They do not establish chapter acceptance, learner success, complete descendant
containment or OS/network isolation.

## Install and upgrade

```bash
uv pip install --upgrade "zeocore==0.10.0"
uv pip install "zeocore[jupytext,pandoc,notebook]==0.10.0"
```

The second command is for local authoring. Pandoc itself must also be installed.
Install only the optional provider/adaptor extras you use; `httpx` is now a base
dependency. The notebook extra adds nbclient, ipykernel and psutil. The base import
remains usable without those optional packages.

Existing direct integration construction keeps its historical configuration
behavior. Move the application entry point to the
[managed launcher](docs/integrations/environments.md) to adopt the separate tracks.
Do not reuse an initialized client across modes. Semantic digest consumers must
retain the new schema label; old and new digest values are not interchangeable.

The [examples catalog](examples/README.md), [API reference](docs/reference/api.md)
and [resources repository](https://github.com/profrodai/sovereign-agent-resources)
provide runnable paths. Resources migrate to this exact version after publication.
No live provider delivery, account entitlement, classroom result or visual image
qualification is asserted by the package release.
