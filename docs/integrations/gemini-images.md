# Reference image commissioning

Created and reviewed 2026-09-08. Doctrine Rev 17 with the active operator delegation.

`zeo_core.integrations.gemini.ImageGenerationService` executes one reference-image
request through the admitted connection, exact authorization verifier, durable
effect broker, and Keychain custody callback. The provider is Gemini's
`gemini-3.1-flash-image` model, also called Nano Banana 2. No UI or ComfyUI process
is involved. Returned images are candidates with `UNREVIEWED` qualification.

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
