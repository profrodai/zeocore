# Authoring reference consumer

**Updated:** 2026-09-09. Development API: use the reviewed source checkout until
these changes are released. Do not assume an older published wheel has them.

The [self-contained consumer](../../examples/authoring_reference/run.py) uses
only public ZeoCore conversion, comparison, execution and environment APIs.
It contains a small generic fixture, not a book chapter or an exercise grader.

From this checkout, with Python 3.14, Git, uv and Pandoc installed:

```sh
uv sync --frozen --extra jupytext --extra pandoc --extra notebook
.venv/bin/python examples/authoring_reference/run.py --state-root /tmp/authoring-example --mode test --run-id one --docx
.venv/bin/python examples/authoring_reference/run.py --state-root /tmp/authoring-example --mode test --run-id two --docx
.venv/bin/python examples/authoring_reference/run.py --state-root /tmp/authoring-example --mode production --run-id one --docx
```

The three runs occupy separate `test/work/one`, `test/work/two` and
`production/work/one` directories beneath the state root. Each mode has its own
configuration, credentials and temporary directory through the existing
`IntegrationEnvironment`. Explicit `JupytextConfig()` and `PandocConfig()`
select local conversion behavior; no provider credentials are needed. An
**author profile** means ZeoTutorial policy composed over these test/production
modes. It is not a third environment mode.

Each run copies the canonical fixture into a disposable Git-rooted workspace,
converts an explicitly required notebook batch, writes diagnostic round-trip
Markdown, checks semantic parity, checks hand-authored fixture expectations,
and executes a separate notebook in a new kernel. It checks the actual output
against the independent expected value. Relative assets accompany both notebook
locations. Optional DOCX conversion remains visibly SUCCEEDED/FAILED, or
UNAVAILABLE with NOT_REQUESTED when `--docx` is omitted. It cannot turn failed
required checks into success.

The outer staging directory is renamed into the absent run directory only
after every required gate passes. A failed required check removes its staging
workspace. Reusing a run ID is refused without changing the old run. A sibling
exclusive lock prevents simultaneous example builds to that destination.
These are caller-owned directories, not a boundary against hostile filesystem
mutation. JSON errors contain a fixed failure code, not raw notebook exceptions.

Inspect `release.json` for complete source/output byte sizes and SHA-256 hashes,
conversion receipts, parity, execution, independent checks and optional export.
The [complete example receipt](../../examples/authoring_reference/receipt.example.json)
is an observed local run, not a golden file or a promise that different tool
versions produce the same bytes. Its tool versions describe that run.

The repeatability test runs all three commands and independently rehashes every
artifact. It compares the entire release object after excluding only each
conversion receipt's named `details.conversion_time` diagnostic. No timestamps,
paths, metadata or output identities are broadly scrubbed. New receipt APIs
supply deterministic cell IDs. The example sets `SOURCE_DATE_EPOCH=315532800`
in its child process for [Pandoc's documented reproducible archive timestamps](https://pandoc.org/demo/example33/18-reproducible-builds.html).
Repeatability applies to matching tools and inputs; version changes remain visible.

The fixture includes prose, Unicode, a relative asset, executable exercise code,
a `.noeval` illustration, a `solution-only` tag and reflection metadata.
`expected.json` is hand-authored. Deliberate assertion failure, wrong input and
a wrong independent expected output each prove a required gate can reject a run.
The broader [conversion](authoring-receipts.md) and
[execution](notebook-execution.md) suites exercise drift, partial batches,
collisions, secrets, timeouts, kernel failures and descendant cleanup.
Run the full `make verify` gate with the development/all extras installed.

## Ownership and migration

ZeoCore supplies mechanical evidence. ZeoTutorial owns objective-task-assessment
maps, independent student/transfer graders, solution separation, immutable
chapter manifests, brands, author policy and release orchestration. The
reference fixture deliberately retains its solution-only cell to prove metadata
preservation; it is an author fixture and must not be published as a student
bundle. Student solution separation belongs to the consuming application.

After classroom use of the Chapter 1, 3 and 9 successor bundles and measured
per-chapter release cost justify adoption, and these capabilities are in a
supported ZeoCore release, QuackTutorial's
consumer migration must pin that release, rename package/import/CLI consistently
to `zeotutorial`, replace swallowed errors and mutable runs, and use these public
receipt APIs without private-import fallback. Preserve existing Git history and
search real consumers before removing compatibility. Keep old path-returning
and exploratory partial-batch ZeoCore APIs compatible; use the new strict APIs
for authoring releases.

Sovereign Agent owns canonical lesson Markdown, learner artifacts and the
student/site release manifest; learners
need neither authoring package. profrod-site remains the sole book renderer.
This reference run is not evidence of learner success, classroom effectiveness,
publisher acceptance or human visual approval. Fresh execution is trusted code,
not process/network isolation; use externally enforced containers when required.
HTML import creates a separate review draft. Importing generated artifacts must
never automatically overwrite canonical Markdown.

## Staging, publication and evidence layers

The reference's `release.json` is explicitly NOT_PUBLISHED. Conversion batches
report CONVERSION_STAGE; their promotion makes a complete converted staging
bundle, not an accepted chapter release. Only a future ZeoTutorial publisher
may update an atomic current-release reference after all required gates. This
example has no public current pointer and performs no publication. Concurrent
publisher and interrupted current-pointer controls remain part of that deferred
application, not a claim made by this substrate.

The example records the checkout's lockfile and checks the actual installed
inventory identity at execution. This recipe approves the current environment
for its local demonstration; production author policy must supply its separately
approved inventory identity and lock, rather than trusting a new environment
merely because it can describe itself. The kernel receipt also identifies the
actual generated spec and interpreter binary. Undeclared skips and unexpected
errors are required-gate failures in this fixture.

Exact artifact hashes, versioned notebook semantics and execution observations
are different evidence. The semantic schema `zeocore.notebook-semantics.v1`
includes ordered cell types, declared IDs, tags, source, unknown metadata and
attachments; it names the limited CRLF/tool-version/text-parser-ID normalization
and explicitly excludes execution counters and outputs. No code whitespace or
unknown metadata is broadly normalized. A test changes execution output and
retains different exact hashes with the same semantic digest, then changes
unknown metadata and proves parity rejects it. The three-run byte equality test
is a property of this deliberately deterministic fixture, not a requirement for
arbitrary executed notebooks or a license to scrub their observations.

The book proceeds independently with its locked CLI tooling. Neither these APIs
nor the deferred ZeoTutorial migration blocks its successor chapters. Adoption
requires the classroom and release-cost evidence in organization issue 639's
elder direction; the reference consumer does not claim to supply that evidence.
