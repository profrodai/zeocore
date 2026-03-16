# QuackCore Error Code Reference

This document defines the blessed error code taxonomy for QuackCore capabilities. In the Sovereign Agent Architecture, these codes are the primary mechanism for preventing agent hallucination by providing unambiguous, machine-readable feedback.

All machine-readable error codes and skip codes must follow the format: `QC_<AREA>_<DETAIL>`

## Blessed Error Areas

### QC_SYS_* - System & Runtime Errors

Failures related to the local execution environment or process management.

* `QC_SYS_PID_LOST` - Background process ID no longer exists or crashed
* `QC_SYS_DISK_FULL` - Insufficient space in the local Artifact Store
* `QC_SYS_TIMEOUT` - Process exceeded the hard execution limit
* `QC_SYS_DEP_MISSING` - Required system dependency (e.g., FFmpeg) not found

### QC_IO_* - I/O & Artifact Store Operations

Failures related to the `.quack/` store or local file operations.

* `QC_IO_NOT_FOUND` - File or resource not found in project path
* `QC_IO_MANIFEST_CORRUPT` - Existing manifest failed checksum or parsing
* `QC_IO_WRITE_ERROR` - Failed to commit artifact or manifest to the store
* `QC_IO_LEDGER_LOCKED` - Local `ledger.db` is busy or read-only

### QC_VAL_* - Validation & Agent Input Failures

Errors in the parameters provided by the Agent (often used for skips).

* `QC_VAL_INVALID_ID` - Provided `RunID` or `AssetID` does not exist in ledger
* `QC_VAL_TOO_SHORT` - Input below minimum threshold
* `QC_VAL_UNSUPPORTED` - Format or codec unsupported by this limb
* `QC_VAL_CHKSUM_MISMATCH` - Final artifact does not match expected manifest hash

### QC_CFG_* - Configuration & Discovery

Errors in tool configuration or capability mapping.

* `QC_CFG_MISSING` - Required configuration parameter missing
* `QC_CFG_DISCOVERY_FAILED` - Tool failed to output machine-readable schema
* `QC_CFG_PRESET_NOT_FOUND` - Requested execution preset does not exist

### QC_NET_* - Network & Cloud Operations

Failures when a limb must cross the sovereign boundary to external APIs.

* `QC_NET_TIMEOUT` - Remote request timed out
* `QC_NET_UNAVAILABLE` - External service (e.g., OpenAI, Anthropic) is down
* `QC_NET_AUTH_EXPIRED` - Cloud credentials or tokens require rotation

### QC_AUTH_* - Authentication & Permissions

Security and local permission failures.

* `QC_AUTH_FORBIDDEN` - Limb does not have local permission to access path
* `QC_AUTH_SCOPE_MISSING` - Scoped token does not permit this specific action

### QC_RATE_* - Rate Limiting

* `QC_RATE_EXCEEDED` - External API rate limit reached
* `QC_RATE_QUOTA_EXCEEDED` - Monthly commercial usage quota reached

### QC_TOOL_* - Limb-Internal Errors

Deterministic logic failures specific to a tool's domain.

* `QC_TOOL_INVALID_STATE` - Mutation requested is impossible for current asset
* `QC_TOOL_PROCESSING_FAILED` - Transformation logic failed despite valid inputs

## Usage Guidelines

1. **Always use QC_ prefix** - All machine codes must start with `QC_`
2. **Machine-First** - Codes must be specific enough for an Agent (OpenClaw) to decide whether to retry, pivot, or escalate to the Human.
3. **Immutability** - Do not change the meaning of a code once it is in production; version the detail if necessary.
4. **Summary Pairing** - Every error returned to a CLI should be accompanied by a `human_message` for the `summary.md`.

## Examples in Code

```python
# Agent provided a bad timestamp for a clip
result = CapabilityResult.fail(
    msg="Start time 00:50 exceeds video duration 00:45",
    code="QC_VAL_INVALID_RANGE"
)

# Tool crashed during async execution
result = CapabilityResult.fail(
    msg="FFmpeg exited with code 137 (OOM)",
    code="QC_SYS_PID_LOST",
    metadata={"pid": 45210}
)

# Skip because the work is already done (Idempotency)
result = CapabilityResult.skip(
    reason="Fingerprint already matches ledger entry",
    code="QC_VAL_ALREADY_EXISTS"
)

```