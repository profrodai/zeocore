# Reference image commissioning

Created and reviewed 2026-09-08. Doctrine Rev 17 with the active operator delegation.

`zeo_core.integrations.gemini.ImageGenerationService` executes one reference-image
request through the admitted connection, exact authorization verifier, durable
effect broker, and Keychain custody callback. The provider is Gemini's
`gemini-3.1-flash-image` model, also called Nano Banana 2. No UI or ComfyUI process
is involved. Returned images are candidates with `UNREVIEWED` qualification.

## Install and choose an account track

Available in `zeocore==0.10.0`; the adapter needs no Google SDK extra.
Start with [managed environments](environments.md). Its integration ID is
`gemini.images`. The launcher isolates configuration and process state; this
integration deliberately forwards no raw API-key environment variables.
The Runtime host supplies Keychain custody and broker authorization below.

### Obtain a key

1. Sign in to [Google AI Studio](https://aistudio.google.com/), accept its terms,
   and open **Dashboard → Projects**. Import the Google Cloud project you intend
   to use, or create a dedicated project.
2. Open **API keys** and create a key in that project. Follow Google's current
   [API-key instructions](https://ai.google.dev/gemini-api/docs/api-key): new keys
   use authorization keys bound to service accounts; do not provision a new
   integration with a deprecated standard key.
3. If creation is unavailable, have the project's administrator grant the
   project, API-key, service-enablement and service-account permissions listed
   in that guide. Confirm model access and [billing](https://ai.google.dev/gemini-api/docs/billing)
   for the selected project before a live request. A key does not guarantee
   image-model entitlement or a free generation allowance.
4. Copy the key once into the trusted host's secret provisioning flow. Keep it
   out of notebook cells, command arguments, repository files and issue comments.

### Test account and offline E2E

Google project separation is the test variant; ZeoCore does not turn a live
image generation into a sandbox call. Create a dedicated test Cloud project,
use synthetic reference images, and grant only the required API access.
A separate Google login is optional; the project, key and local stores must
be distinct from production.

For a fully offline first run, use `python examples/gemini_request.py` from
this release's checkout. It verifies local image bytes and constructs a typed
request without obtaining a key or calling Google. For broker E2E, run
`pytest tests/test_integrations/test_gemini_images.py`: its fake HTTP/Keychain
fixtures exercise real broker persistence, custody boundaries and reconciliation.
Those fixtures must never become production trust verifiers.

### Production account and custody

Use a production Cloud project and newly provisioned production key. Configure
separate private broker databases and artifact directories for both tracks.
`KeychainSecretStore(service_prefix=...)` does **not** automatically read the
managed environment: the host must derive distinct prefixes from the selected
mode and canonical state root and pass them explicitly. Provision through
`KeychainSecretStore.put(organization_id=..., material=...)` inside the trusted
host and retain only its opaque handle in the admitted connection. Its default
backend uses macOS Keychain; another platform needs a reviewed host custody
implementation, not a plaintext substitute.

Bind each connection to its organization and allowed Google project IDs, and
configure the host's real issuer, audience and signature verifier. The host
must attest which project owns the key; the key itself is not identity proof.
The account transition is new admission plus new authorization, not copying a
test database or changing an environment label.

### Bounded live verification, cleanup and rotation

First run the revision's read-only model health probe through the host's
connection admission flow. Record the mode, admitted project, revision and
health result without the key. To qualify actual generation, explicitly approve
one request with synthetic inputs, its cost and its output destination. Invoke
through `ImageGenerationService`, verify the receipt and image digests, and
inspect the generated candidate separately. A request-only example or passing
fixture suite is not proof of a live Google generation.

Delete only artifacts created by that test after retaining the required audit
receipts. Local deletion does not delete Google's stored interaction; consult
the provider's retention policy. Rotate by provisioning a new key/handle,
validating and admitting the replacement, then revoking the old key in AI Studio
and retiring its connection. Never retry an ambiguous billed request merely
because the local output is absent; follow the reconciliation rules below.

## Host wiring

The Runtime host supplies an `EffectOrchestrator` configured with its durable
`BrokerExecutionStore`, trusted signature verifier, issuer set and audience.
It enrolls `image_generation_revision()` and an active connection in that store.
Connection enrollment must select the allowed project IDs, expose
`gemini.generate_reference_image`, and bind an organization-scoped Keychain
secret handle. The API key alone does not attest a Google project identity:
`operator-attested-google-project` denotes a host admission obligation. This
adapter does not automatically enroll a connection, invent identity evidence,
mint authorization, or provide a default accepting signature verifier.

Construct `ImageArtifactStore` with the host's private artifact directory. Add
canonical PNG/JPEG/WebP reference bytes using `put_image(organization_id,
project_id, bytes, mime_type)`. Construct `ImageGenerationRequest` with those
returned artifact descriptors and the complete prompt. The Runtime authority
signs the SHA256 digest of exactly `request.model_dump_json().encode()` along
with the connection, revision, operation and execution bindings required by the
broker. Requests contain no credentials, network URLs or filesystem paths.

Construct `ImageGenerationService(orchestrator=broker, secrets=keychain,
artifacts=artifacts)` and invoke `generate(organization_id=..., connection_id=...,
execution_id=..., authorization=..., request=request)`. This invokes the actual
broker and custody path; it does not call a provider directly from authored IR.
The operation ID and revision ID are fixed by the service. Obtain successful
output with `artifacts.receipt(organization_id, str(execution_id))` and
`artifacts.read_image(...)`. Receipts bind request, execution, project, provider
interaction and actual output image digests. They are separate from the broker's
authorization/execution receipts and from artistic qualification.

The low-level dispatcher and transport are adapter implementation surfaces;
production hosts must use the service. Artifact roots are trusted host
configuration with exclusive write custody; paths reject descendant symlinks,
including symlinks into another project inside the same root. This is not a
filesystem sandbox against a privileged process concurrently replacing the root.

## Failure behavior

The broker commits `DISPATCH_STARTED` before the one provider POST. A completed
interaction ID is persisted before generated image materialization. An uncertain
response is reconciled by checking the immutable local receipt or GETting the
already recorded interaction ID. No reconciliation issues another POST. A lost
response without a durable provider ID remains `AMBIGUOUS`; an operator must
investigate the original attempt before authorizing any distinct generation.
The connector makes no claim of provider-native idempotency or exactly-once
billing. A terminal unsuccessful interaction does not prove a zero charge.

Only `steps` entries with `type: model_output` contribute output images. Echoed
input references, empty output, wrong MIME types, invalid base64, unexpected
shapes and non-image transport never become successful generation receipts.
Provider response text and exceptions are sanitized at the transport/custody
boundary. Redirects are not followed; clients disable environment proxy routing
and automatic retries. Explicit rejection statuses terminate the attempt.

The closed contract permits one to six distinct references, at most 24 MiB each
and 32 MiB combined, one to four output images, PNG or JPEG output, selected
aspect ratios and 1K/2K output. The broker request envelope is 32 KiB; inline
provider response transport is capped at 48 MiB. Images must pass a transport
signature check and are hashed, but full image decoding, registration, masks,
identity checks and paint review belong to the downstream cast-art pipeline.
Stored provider interactions follow Google's retention rules, not local store
retention. Raw prompts and source images are sent to the configured Google API.

## Verification and live configuration

`tests/test_integrations/test_gemini_images.py` runs the real SQLite broker,
Keychain custody implementation and immutable artifact store against an offline
HTTP provider. It checks marker-before-POST, recovery without a second POST,
refusal before custody, project isolation, symlinks, tampering, secret sanitizing
and input-echo rejection. Its synthetic signature verifier and fake Keychain are
test fixtures only. These checks do not attest a live Runtime installation or
artistic quality. Full repository gate: `make verify`.

API contract checked against Google's [Interactions reference](https://ai.google.dev/api/interactions-api)
and [image generation documentation](https://ai.google.dev/gemini-api/docs/image-generation)
on 2026-09-08. Generation uses stored, synchronous interactions; no support for
background image generation is assumed. The revision's `models.get` health
probe is a host connection-admission probe, not an automatic billed generation
or a claim that this service performed live health verification.
