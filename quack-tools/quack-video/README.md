# 🦆 QuackVideo

**An Atomic Limb for Deterministic Video Processing and Asset Production**

> **QuackVideo turns raw video inputs into structured, auditable video artifacts.**
> It does not decide what is interesting. It does not choose what to publish. It does not plan workflows.

---

## 🧠 What QuackVideo Is

QuackVideo is a **Ring B Atomic Limb**.

It is a deterministic worker designed to be manipulated by Sovereign Agents (e.g., OpenClaw). It consumes **video inputs** and produces **video-derived artifacts**, such as:

* processed video files
* atomic clips and segments
* extracted frames and thumbnails
* captions and transcripts
* per-run manifests + LLM-optimized summaries

QuackVideo answers one question only:

> **“Given these video inputs and atomic parameters, produce these video artifacts and provide proof.”**

---

## ❌ What QuackVideo Is Not

QuackVideo is **not**:

* a video editor UI
* a content strategy engine
* a workflow orchestrator
* an AI agent (it is a tool used *by* agents)

It never:

* decides *which* clips are worth keeping (The Agent decides)
* talks to SaaS platforms directly
* sequences multi-step edits (The Manager decides)

Those responsibilities belong to **Ring C** (Sovereign Agents, Temporal, Quackchat).

---

## 🧭 Position in the QuackVerse Doctrine

```
┌──────────────────────────────────────────────────────────┐
│             RING C — AGENTIC CONTROL                     │
│    OpenClaw (Manager) · Temporal · Quackchat (Cockpit)   │
├──────────────────────────────────────────────────────────┤
│             RING B — ATOMIC LIMBS (WORKERS)              │
│        ▶ QuackVideo ◀                                    │
├──────────────────────────────────────────────────────────┤
│             RING A — THE SOVEREIGN BRAIN                 │
│    Ticket System · QuackStore (.quack/) · QuackLedger    │
└──────────────────────────────────────────────────────────┘

```

QuackVideo:

* imports **QuackCore only**
* issues **Async Tickets** for long-running renders
* stores all outputs in the local **Artifact Store** (`.quack/`)
* is orchestrated by always-on agents

---

## 🧰 Canonical CLI Surface

QuackVideo does **not** expose its own standalone CLI. All interaction happens via the **single canonical CLI**:

```bash
quack video <limb> [options]

```

### Mandatory Agentic Verbs

* `status <RunID>` — Check progress of a video render ticket.
* `explain <RunID>` — Output the `summary.md` for LLM context.
* `--discovery` — Output JSON-formatted capability and schema map for the agent.
* `validate` — Pre-flight check of video headers and parameters.
* `doctor` — Auto-fix local FFmpeg/codec dependencies.

---

## 🚀 Common Atomic Limbs

### Process a video (Async)

```bash
quack video process input.mp4 --normalize-audio

```

Produces a `RunID` ticket. Agent polls `quack status` until completion.

### Extract Clip (Atomic)

```bash
quack video clip input.mp4 --start 00:10 --end 00:20 --out ./dist/clips

```

### Extract Frames

```bash
quack video frames input.mp4 --interval 60

```

---

## 📦 Output Artifacts

Each run produces an **artifact bundle** within the project's local store.

```text
.quack/
└── runs/
    └── run_vid_abc_123/
        ├── processed.mp4
        ├── summary.md      <-- LLM-optimized context snippet
        ├── manifest.json   <-- Machine-readable proof
        └── artifacts/
            └── thumbnail.png

```

### The Manifest & Summary

* **`manifest.json`**: Contains checksums, codec metadata, and timestamps. It is the machine's system of record.
* **`summary.md`**: A high-level textual summary (e.g., "Extracted 10s clip. Verified 1080p. Audio normalized.") to prevent Agent context-shredding.

---

## 🔗 The Agentic Handshake

QuackVideo never orchestrates. It follows the **Sovereign Handshake**:

1. **Trigger:** Agent calls `quack video clip` and receives a `RunID`.
2. **Poll:** Agent monitors `quack status <RunID>`.
3. **Verify:** Once finished, the tool writes a verified manifest.
4. **Context:** Agent reads `explain <RunID>` to update its internal monologue.

---

## 🧭 Governance Rules

1. **Atomic Over Monolithic:** Use granular commands for better agent feedback loops.
2. **Async by Default:** Any render or processing task issues a `RunID` ticket.
3. **No Silent Failures:** Exit with `QC_ERROR_CODES` if codecs or files are missing.
4. **Local Sovereignty:** All artifacts and manifests live in the project’s `.quack/` folder.
5. **Everything Emits Proof:** If it didn't emit a manifest, it didn't happen.

---

## 🧠 Closing Statement

QuackVideo is a **limb** of the organization.

It does not decide the narrative. It performs the mutation of video data exactly as instructed, providing the Sovereign Agent with the proof it needs to move the organization forward.