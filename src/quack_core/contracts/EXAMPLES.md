# QuackCore Contracts - Usage Examples

This document provides practical examples of using the contracts module.

## Table of Contents

1. [Basic Result Envelope](#basic-result-envelope)
2. [Creating Artifacts](#creating-artifacts)
3. [Building Manifests](#building-manifests)
4. [Tool Implementation Pattern](#tool-implementation-pattern)
5. [Orchestrator Pattern](#orchestrator-pattern)

---

## Basic Result Envelope

### Success Result

```python
from quack_core.contracts import CapabilityResult

# Simple success
result = CapabilityResult.ok(
    data={"transcription": "Hello, world!"},
    msg="Transcription completed successfully",
    metadata={
        "model": "whisper-large-v3",
        "duration_sec": 5.2
    }
)

print(result.status)  # CapabilityStatus.success
print(result.data)    # {"transcription": "Hello, world!"}
```

### Skip Result (Policy Decision)

```python
# Video too short for processing
result = CapabilityResult.skip(
    reason="Video duration (3.5s) is below minimum threshold (10s)",
    code="QC_VAL_TOO_SHORT",
    metadata={"duration_sec": 3.5, "threshold_sec": 10}
)

print(result.status)           # CapabilityStatus.skipped
print(result.machine_message)  # QC_VAL_TOO_SHORT
```

### Error Result

```python
# From exception
try:
    process_video("/invalid/path.mp4")
except FileNotFoundError as e:
    result = CapabilityResult.fail_from_exc(
        msg="Video file not found",
        code="QC_IO_NOT_FOUND",
        exc=e,
        metadata={"path": "/invalid/path.mp4"}
    )

print(result.status)       # CapabilityStatus.error
print(result.error.code)   # QC_IO_NOT_FOUND
```

---

## Creating Artifacts

### Local File Artifact

```python
from quack_core.contracts import (
    ArtifactRef,
    StorageRef,
    Checksum,
    ArtifactKind,
    StorageScheme,
    ChecksumAlgorithm
)

artifact = ArtifactRef(
    role="transcript_txt",
    kind=ArtifactKind.final,
    content_type="text/plain",
    storage=StorageRef(
        scheme=StorageScheme.local,
        uri="file:///data/transcripts/output.txt"
    ),
    size_bytes=2048,
    checksum=Checksum(
        algorithm=ChecksumAlgorithm.sha256,
        value="a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789"
    ),
    tags={
        "language": "en",
        "model": "whisper-large-v3"
    },
    metadata={
        "word_count": 150,
        "confidence_avg": 0.94
    }
)

print(artifact.artifact_id)  # Auto-generated UUID
print(artifact.role)         # transcript_txt
```

### S3 Artifact

```python
artifact = ArtifactRef(
    role="video_slice_1",
    kind=ArtifactKind.final,
    content_type="video/mp4",
    storage=StorageRef(
        scheme=StorageScheme.s3,
        uri="s3://my-bucket/outputs/clip1.mp4",
        bucket="my-bucket",
        key="outputs/clip1.mp4",
        metadata={
            "region": "us-east-1",
            "storage_class": "STANDARD"
        }
    ),
    size_bytes=5242880,
    tags={"clip_index": "1", "quality": "1080p"}
)
```

---

## Building Manifests

### Complete Tool Execution Manifest

```python
from quack_core.contracts import (
    RunManifest,
    ToolInfo,
    ManifestInput,
    Provenance,
    CapabilityStatus,
    CapabilityLogEvent,
    LogLevel
)
from datetime import datetime, timezone

# Create input artifact
input_artifact = ArtifactRef(
    role="video_source",
    kind=ArtifactKind.intermediate,
    content_type="video/mp4",
    storage=StorageRef(
        scheme=StorageScheme.local,
        uri="file:///data/input.mp4"
    )
)

# Create output artifacts
output_clips = [
    ArtifactRef(
        role=f"video_slice_{i}",
        kind=ArtifactKind.final,
        content_type="video/mp4",
        storage=StorageRef(
            scheme=StorageScheme.local,
            uri=f"file:///data/output/clip{i}.mp4"
        )
    )
    for i in range(1, 4)
]

# Build manifest
started = datetime.now(timezone.utc)
# ... execute tool ...
finished = datetime.now(timezone.utc)
duration = (finished - started).total_seconds()

manifest = RunManifest(
    tool=ToolInfo(
        name="slice_video",
        version="1.0.0",
        metadata={"preset": "fast"}
    ),
    status=CapabilityStatus.success,
    started_at=started,
    finished_at=finished,
    duration_sec=duration,
    inputs=[
        ManifestInput(
            name="source_video",
            artifact=input_artifact,
            required=True,
            description="Source video to slice"
        )
    ],
    outputs=output_clips,
    logs=[
        CapabilityLogEvent(
            level=LogLevel.INFO,
            message="Started slicing video",
            context={"clip_count": 3}
        ),
        CapabilityLogEvent(
            level=LogLevel.INFO,
            message="Slicing completed",
            context={"success_count": 3}
        )
    ],
    metadata={
        "preset": "fast",
        "re_encode": False
    },
    provenance=Provenance(
        git_commit="abc123",
        environment="prod",
        runner="n8n"
    )
)

# Serialize to JSON
manifest_json = manifest.model_dump_json(indent=2)
print(manifest_json)
```

---

## Tool Implementation Pattern

### Video Slicing Tool

```python
from quack_core.contracts import (
    SliceVideoRequest,
    SliceVideoResponse,
    SlicedClipData,
    CapabilityResult,
    RunManifest,
    ArtifactRef,
    StorageRef,
    ToolInfo,
    ManifestInput,
    ArtifactKind,
    StorageScheme
)
from datetime import datetime, timezone

def slice_video_tool(request: SliceVideoRequest) -> CapabilityResult[SliceVideoResponse]:
    """
    Tool implementation that follows the contract pattern.
    
    Returns both:
    1. CapabilityResult[SliceVideoResponse] (immediate result)
    2. Side effect: Writes RunManifest to disk
    """
    started = datetime.now(timezone.utc)
    run_id = generate_run_id()
    
    try:
        # Validate input
        if not request.clips:
            return CapabilityResult.skip(
                reason="No clips specified",
                code="QC_VAL_NO_CLIPS"
            )
        
        # Process clips (implementation in Ring B, not shown)
        generated_clips = []
        for i, time_range in enumerate(request.clips, 1):
            # ... actual slicing logic ...
            
            clip_artifact = ArtifactRef(
                role=f"video_slice_{i}",
                kind=ArtifactKind.final,
                content_type="video/mp4",
                storage=StorageRef(
                    scheme=StorageScheme.local,
                    uri=f"file:///data/output/clip{i}.mp4"
                )
            )
            
            generated_clips.append(SlicedClipData(
                artifact=clip_artifact,
                duration_sec=(time_range.end_sec - time_range.start_sec),
                original_range=time_range
            ))
        
        # Build response
        response = SliceVideoResponse(
            generated_clips=generated_clips
        )
        
        # Build manifest
        finished = datetime.now(timezone.utc)
        manifest = RunManifest(
            run_id=run_id,
            tool=ToolInfo(name="slice_video", version="1.0.0"),
            status=CapabilityStatus.success,
            started_at=started,
            finished_at=finished,
            duration_sec=(finished - started).total_seconds(),
            inputs=[
                ManifestInput(
                    name="source_video",
                    artifact=request.source,
                    required=True
                )
            ],
            outputs=[clip.artifact for clip in generated_clips]
        )
        
        # Write manifest (Ring B responsibility)
        # write_manifest(manifest)
        
        return CapabilityResult.ok(
            data=response,
            msg=f"Generated {len(generated_clips)} clips",
            metadata={"run_id": run_id}
        )
        
    except Exception as e:
        return CapabilityResult.fail_from_exc(
            msg="Video slicing failed",
            code="QC_SLICE_ERROR",
            exc=e
        )
```

---

## Orchestrator Pattern

### n8n Workflow Node (Pseudocode)

```javascript
// n8n node that routes based on manifest

const manifest = JSON.parse(manifestJson);

// Branch based on status
if (manifest.status === 'error') {
    // Route to error handler
    return handleError(manifest.error);
}

if (manifest.status === 'skipped') {
    // Route to skip handler
    return handleSkip(manifest.machine_message);
}

// Success - route outputs by role
for (const artifact of manifest.outputs) {
    switch (artifact.role) {
        case 'transcript_txt':
            sendToTranscriptProcessor(artifact);
            break;
        case 'video_slice_1':
            sendToThumbnailGenerator(artifact);
            break;
        default:
            storeArtifact(artifact);
    }
}
```

### Temporal Workflow (Python)

```python
from temporalio import workflow
from quack_core.contracts import RunManifest, CapabilityStatus

@workflow.defn
class VideoProcessingWorkflow:
    
    @workflow.run
    async def run(self, manifest_json: str) -> dict:
        """Process video based on manifest."""
        
        # Parse manifest
        manifest = RunManifest.model_validate_json(manifest_json)
        
        # Branch based on status
        if manifest.status == CapabilityStatus.error:
            return await self.handle_error(manifest)
        
        if manifest.status == CapabilityStatus.skipped:
            return await self.handle_skip(manifest)
        
        # Route artifacts
        results = {}
        for artifact in manifest.outputs:
            if artifact.kind == ArtifactKind.final:
                results[artifact.role] = await self.process_final_artifact(artifact)
        
        return results
```

---

## Common Patterns

### Error Codes Convention

```python
# Configuration errors
QC_CFG_ERROR         # Generic config error
QC_CFG_MISSING       # Missing required config
QC_CFG_INVALID       # Invalid config value

# I/O errors
QC_IO_NOT_FOUND      # File not found
QC_IO_READ_ERROR     # Failed to read file
QC_IO_WRITE_ERROR    # Failed to write file
QC_IO_DECODE_ERROR   # Failed to decode media

# Network errors
QC_NET_TIMEOUT       # Network timeout
QC_NET_UNAVAILABLE   # Service unavailable

# Validation errors
QC_VAL_INVALID       # Generic validation error
QC_VAL_TOO_SHORT     # Input too short
QC_VAL_TOO_LONG      # Input too long
QC_VAL_UNSUPPORTED   # Unsupported format
```

### Artifact Roles Convention

```python
# Video artifacts
"video_source"       # Original input video
"video_slice_{n}"    # Nth extracted clip
"thumbnail_jpg"      # Preview thumbnail

# Audio artifacts
"audio_extract"      # Extracted audio track

# Transcript artifacts
"transcript_txt"     # Plain text transcription
"transcript_srt"     # SRT subtitle file
"transcript_vtt"     # WebVTT subtitle file
"transcript_json"    # Full transcription with segments

# Analysis artifacts
"analysis_json"      # Video analysis/metadata
"report_pdf"         # Summary report

# Debug artifacts
"debug_log"          # Debug output
"debug_ffmpeg"       # FFmpeg command log
```

---

## Testing

### Unit Test Example

```python
import pytest
from quack_core.contracts import CapabilityResult, CapabilityStatus

def test_success_result():
    """Test creating a success result."""
    result = CapabilityResult.ok(
        data={"count": 5},
        msg="Processing complete"
    )
    
    assert result.status == CapabilityStatus.success
    assert result.data["count"] == 5
    assert result.error is None

def test_error_invariants():
    """Test that error status enforces invariants."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        # Error status requires error field
        CapabilityResult(
            status=CapabilityStatus.error,
            human_message="Failed"
            # Missing: error field and machine_message
        )
```

### Fixture Validation Example

```python
import json
from pathlib import Path
from quack_core.contracts import RunManifest

def test_load_manifest_fixture():
    """Test loading and validating a manifest fixture."""
    fixture_path = Path("tests/contracts/fixtures/manifest_success.json")
    
    with open(fixture_path) as f:
        data = json.load(f)
    
    # Pydantic validates automatically
    manifest = RunManifest.model_validate(data)
    
    assert manifest.status == CapabilityStatus.success
    assert len(manifest.outputs) > 0
```

---

## See Also

- [README.md](README.md) - Architecture and boundaries
- [Doctrine v3 Documentation](../docs/doctrine-v3.md) - Ring architecture
- [API Reference](../docs/api-reference.md) - Complete API docs