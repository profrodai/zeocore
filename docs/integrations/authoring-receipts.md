# Authoring conversion receipts

**Updated:** 2026-09-09. Available in ZeoCore 0.10.0.

Receipt APIs are additive. Existing path-returning methods and legacy partial
batch behavior keep their return shapes. Use the strict API for required releases.

## Convert and compare

Initialize `JupytextIntegration`, then use `script_to_notebook_with_receipt`
and `notebook_to_script_with_receipt`. Both require explicit input, output and
`workspace_root`. The output must not exist. Relative paths resolve from the
workspace root. `NotebookConverter.convert_file_with_receipt` also allows
`absolute_paths=True`; portable relative paths are the default.

```python
from zeo_core.integrations.jupytext import JupytextIntegration

integration = JupytextIntegration()
assert integration.initialize().success
clean = integration.script_to_notebook_with_receipt(
    "source.md", "lesson.ipynb", workspace_root="/path/to/git/workspace"
)
assert clean.success
diagnostic = integration.notebook_to_script_with_receipt(
    "lesson.ipynb", "diagnostic.md", workspace_root="/path/to/git/workspace"
)
assert diagnostic.success
parity = integration.compare_notebook_semantics(
    "/path/to/git/workspace/source.md", "/path/to/git/workspace/diagnostic.md"
)
assert parity.success
```

For strict authoring, declare the kernel and Jupytext text representation in
canonical Markdown. Use `md` with explicit code fences, metadata regions and
`.noeval` listings. Canonical Markdown and round-tripped diagnostic Markdown are
compared; IPYNB-to-IPYNB pairs are also supported. Cross-format comparison may
fail because Jupytext strips its text representation from notebook JSON. It
does not silently ignore that metadata difference.

Comparison checks ordered cell type, declared ID, tags, source hash, every
metadata field and attachments. Receipts carry metadata hashes, not potentially
sensitive metadata contents. Named normalizations are CRLF to LF and the
`jupytext.text_representation.jupytext_version` field. Unknown drift fails.
Text readers create random nbformat IDs; these are not declared source IDs and
do not enter text-pair comparison. Notebook JSON IDs are compared exactly.
Receipt-bearing text-to-notebook conversion assigns deterministic IDs from
ordinal, type and source. The legacy converter retains its existing behavior.

Empty input, zero cells and unsupported cell types produce separate parity
errors. Conversion is not execution: a clean notebook is never execution evidence.

## Required release batches

```python
from zeo_core.integrations.jupytext import RequiredConversionTask

result = integration.convert_batch_strict(
    [
        RequiredConversionTask(
            task_id="lesson", source_path="source.md",
            output_path="lesson.ipynb", target_format="ipynb", required=True
        )
    ],
    "release-001",
    workspace_root="/path/to/git/workspace",
)
assert result.success and result.content.promoted
```

The destination directory must be absent, and its parent must already exist.
Each output is relative to that directory. Preflight rejects empty batches,
duplicate IDs and outputs, path traversal, symlinks, nested output collisions,
source/output aliasing and paths outside the workspace before conversion.
Missing input files remain ordered failed item results. Optional failure remains
visible; any required failure prevents promotion. Failed staging is cleaned.
An exclusive sibling promotion lock coordinates cooperating builds. Success
renames one complete directory; rerunning into the same destination refuses.
This is a caller-owned filesystem transaction, not an adversarial OS sandbox
or protection against a hostile process changing filesystem paths concurrently.

Every success receipt contains full source/output SHA-256, sizes, format facts,
converter version, preserved low-level ConversionDetails, structural validation
and cell facts where applicable. `reproducibility_digest()` excludes only the
named `details.conversion_time` diagnostic; use portable paths for comparison.
Any output/source/version difference still changes that digest.

## Pandoc review artifacts

`PandocIntegration.markdown_to_docx_with_receipt` and
`html_to_markdown_with_receipt` expose the same explicit path/root contract.
Initialize with an explicit Pandoc configuration as documented in the Pandoc
integration guide. `DocumentConverter.convert_file_with_receipt` is available
for an already validated `PandocConfig`.

DOCX receipt conversion independently checks archive structure even if legacy
configuration disables structural checks. It always records
`human_visual_approval=false`. A human render review is a separate receipt.
HTML import creates a new `REVIEW_DRAFT`; existing Markdown is never overwritten.
Pandoc absence is an explicit unavailable failure. Source and parser exception
contents are not copied into receipt errors.

## Ownership and evidence limits

ZeoCore owns generic conversion, comparison and required-item aggregation.
ZeoTutorial owns objective/task/assessment manifests and release orchestration.
Book repositories own the canonical content and independent learner checks.
Learners consume committed artifacts without this authoring dependency.
A converter success proves neither notebook execution nor learning, classroom
effectiveness, publisher acceptance or visual approval. Fresh-kernel execution
is a separate capability and release prerequisite.

Run `make verify` and `.venv/bin/pytest -q tests/authoring`. The real conversion
tests use a child process to avoid the legacy suite's filesystem mocks; expected
cell structure, metadata, output hashes and failure outcomes are asserted
independently.
