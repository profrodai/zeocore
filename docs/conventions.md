# QuackCore v3 Conventions & Standards

**Status:** Approved v3 (Agentic OS Edition)

**Scope:** All Capability, Limb, and Kernel Development

## 1. Job & Status Semantics

In the Sovereign Agent architecture, we shift from simple synchronous returns to an **Authoritative Ticket System**.

| Status | Meaning | Agent (OpenClaw) Action | Example |
| --- | --- | --- | --- |
| **`pending`** | Ticket issued; background worker queued. | Poll `quack status <ID>` | Job added to `.quack/runs/` |
| **`running`** | Mutation in progress. | Wait & Polling continues | Fingerprinting 45% complete. |
| **`success`** | Task complete; **Manifest Verified**. | Read `explain <ID>` (Summary) | `manifest.json` written + signed. |
| **`skipped`** | Logic determined action unnecessary. | Log and proceed to next limb | Video already normalized. |
| **`error`** | Execution failed or tool crashed. | ADMIT failure; do not hallucinate | `QC_IO_NOT_FOUND` on source. |

## 2. Agent-First Error Codes (`machine_message`)

The `machine_message` **MUST** be a `QC_*` code. This is the only way for Sovereign Agents to handle failures programmatically without "guessing."

* **`QC_SYS_*`**: System/Infra level (e.g., `QC_SYS_PID_LOST`, `QC_SYS_DISK_FULL`)
* **`QC_VAL_*`**: Agent input errors (e.g., `QC_VAL_INVALID_TIMESTAMP`)
* **`QC_IO_*`**: Local I/O & Artifact Store (e.g., `QC_IO_MANIFEST_CORRUPT`)
* **`QC_EXT_*`**: External API/Cloud issues (e.g., `QC_EXT_AUTH_EXPIRED`)
* **`QC_TOOL_*`**: Specific tool/limb logic failures (e.g., `QC_TOOL_CODEC_UNSUPPORTED`)

## 3. Sovereignty & Portability Rules

1. **Local System of Record:** Every run MUST record its `RunID` and artifacts in the project-local `.quack/` directory.
2. **The "Proof" Mandate:** Success cannot be returned unless a `manifest.json` with a valid checksum exists in the run directory.
3. **No Hidden State:** Tools must not rely on global system state. If a tool moves to another Mac Mini, it must be able to resume by reading the local `.quack/ledger.db`.
4. **Agent Context:** Every `success` MUST produce a `summary.md`—a 2-3 sentence LLM-optimized snippet describing the output.

## 4. CLI Grammar & Discovery

1. **Atomic Limbs:** Prefer granular verbs (`add-slide`) over monolithic flags (`--create-with-slides`).
2. **Machine-Readable Discovery:** All tools must support `--discovery` returning a JSON map of subcommands and input schemas.
3. **Async-by-Default:** Any operation expected to take >2 seconds must issue a Ticket (`RunID`) and return immediately.

## 5. Architectural Boundaries (Agentic)

| Question | If YES → Put logic in... | If NO → Put logic in... |
| --- | --- | --- |
| Does this involve judgment or strategy? | **Sovereign Agent** | QuackCore/Tool |
| Is this a long-running mutation of data? | **QuackTool (Limb)** | QuackCore |
| Is this an authoritative proof/contract? | **QuackCore (Kernel)** | QuackTool |
| Does this coordinate multiple tools? | **Temporal / Agent** | QuackTool |

---