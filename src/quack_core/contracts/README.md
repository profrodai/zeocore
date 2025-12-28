# QuackCore Contracts (Ring A / Kernel)

## Mission

The `quack_core.contracts` module defines the **canonical data contracts** for the QuackCore system. This module represents **Ring A** in the Doctrine v3 architecture — the stable, versionable kernel that all other rings depend upon.

## What Belongs Here

✅ **Pydantic models** for:
- Envelopes (results, errors, log events)
- Artifacts (references, metadata, storage)
- Run manifests (inputs, outputs, intermediates)
- Capability request/response schemas

✅ **Minimal helpers** that do NOT orchestrate:
- ID generation (UUID only)
- Timestamp utilities (UTC now)
- Version constants
- Model validators for invariants

## What Does NOT Belong Here

❌ **Implementation logic**:
- File I/O operations
- Network requests (FTP, S3, Drive uploads)
- Media processing (ffmpeg, transcription)
- Retry/timeout logic
- Workflow orchestration

❌ **External dependencies**:
- No imports from `quack_core.lib.*`
- No imports from `quack_core.toolkit.*`
- No imports from `quack_core.integrations.*`
- No imports from `quack_core.workflow.*`

## Dependency Rule (CRITICAL)

**Contracts may only import:**
- Python standard library
- Pydantic (v2)
- Type hints from `typing`

**Contracts must never import:**
- Other QuackCore modules (except within contracts itself)
- Third-party libraries beyond Pydantic

This ensures contracts remain stable and can be versioned independently.

## Consumer Rings

- **Ring B (Toolkit/Tools)**: Imports contracts to emit `CapabilityResult` and artifacts
- **Ring C (Runners/Orchestrators)**: Imports contracts to parse manifests and route artifacts
- **Ring D (Integrations)**: Imports contracts to understand artifact schemas

## Stability Promise

Contracts follow **semantic versioning**:
- **Patch** (1.0.x): Bug fixes, documentation, internal refactors
- **Minor** (1.x.0): Backward-compatible additions (new optional fields)
- **Major** (x.0.0): Breaking changes (required fields, renamed types)

Breaking changes require:
1. Deprecation warning in previous minor version
2. Migration guide in changelog
3. Version bump in `CONTRACTS_VERSION`

## Usage Examples

```python
# Correct usage
from quack_core.contracts import (
    CapabilityResult,
    ArtifactRef,
    RunManifest,
    StorageRef
)

# Tool emits a result
result = CapabilityResult.ok(
    data=transcription,
    msg="Transcription completed",
    metadata={"model": "whisper-large"}
)

# Tool creates artifact reference
artifact = ArtifactRef(
    role="transcript_txt",
    kind=ArtifactKind.final,
    content_type="text/plain",
    storage=StorageRef(scheme="local", uri="/data/transcript.txt")
)

# Runner reads manifest
manifest = RunManifest.model_validate_json(manifest_json)
for output in manifest.outputs:
    if output.role == "transcript_txt":
        route_to_next_step(output)
```

## Architecture Notes

### Why Contracts Are Separate

1. **Versionability**: Contracts can be versioned independently from implementations
2. **Testability**: Contracts can be validated without running actual workflows
3. **Clarity**: Clear boundary between "what" (contracts) and "how" (implementations)
4. **Reusability**: Same contracts work across CLI, n8n, Temporal, cloud runners

### Artifact-Centric Design

All data flows through `ArtifactRef`:
- Tools produce artifacts (not raw file paths)
- Runners route artifacts (not file contents)
- Integrations store artifacts (not implementation details)

This enables:
- **Pluggable storage**: Local → S3 → GCS without changing contracts
- **Machine branching**: n8n routes by `role` and `kind`, not file inspection
- **Audit trails**: Full provenance from manifest metadata

## Contributing

When adding to contracts:

1. **Check boundaries**: Does this belong in Ring A?
2. **Minimize dependencies**: Can this use stdlib only?
3. **Document consumers**: Who will import this?
4. **Add tests**: Validate invariants and examples
5. **Update version**: Bump `CONTRACTS_VERSION` if breaking

See `CONTRIBUTING.md` in repo root for full guidelines.